# SDD: `build-package` GitHub Action

**Date:** April 10, 2026
**Author:** Eric Dill, with Jarvy

## What are we building?

A GitHub Action that runs conda-build. It should just work — zero required inputs if your repo has a recipe in the obvious place. Sensible defaults for everything: finds the recipe, uses Anaconda's CBC, builds against `defaults` channel.

```yaml
# Zero-config: finds recipe, uses Anaconda CBC, builds against defaults
- uses: anaconda/github-actions/build-package@v1
```

```yaml
# Override what you need, leave the rest
- uses: anaconda/github-actions/build-package@v1
  with:
    cbc-preset: conda-forge

# Or layer your own tweaks on top of Anaconda's CBC
- uses: anaconda/github-actions/build-package@v1
  with:
    cbc: ./my-overrides.yaml
```

```yaml
# Full build + upload workflow
- uses: anaconda/github-actions/build-package@v1
- uses: anaconda/github-actions/upload-package@v1
  with:
    token: ${{ secrets.ANACONDA_TOKEN }}
    owner: my-channel
    packages: ./build/**/*.conda
```

## What is SDD for a GitHub Action?

Three layers of spec, written before implementation:

1. **Interface** — inputs, outputs, defaults. The action.yml itself.
2. **Behavior** — testable assertions: "given this input, expect this outcome."
3. **Integration** — end-to-end tests in real CI workflows.

The spec is the first PR. Implementation satisfies it.

---

## Interface spec

```yaml
name: "Build Package"
description: "Build a conda package with conda-build against a conda_build_config.yaml (CBC)"
author: "Anaconda"

inputs:
  recipe:
    description: "Path to the conda recipe directory. Auto-discovered if omitted."
    required: false
  cbc-preset:
    description: 'Built-in CBC preset: "anaconda" (default) or "conda-forge"' or "none"
    required: false
    default: "anaconda"
  cbc:
    description: "URL or local path to a conda_build_config.yaml. Merged on top of cbc-preset (overrides matching keys)."
    required: false
  channels:
    description: "Comma-separated list of conda channels. If omitted, inferred from preset (anaconda→defaults, conda-forge→conda-forge)."
    required: false
  python-version:
    description: "Python version(s) to build for. Single (e.g., '3.12') or comma-separated (e.g., '3.11,3.12,3.13'). If omitted, uses whatever the CBC specifies."
    required: false
  conda-build-version:
    description: "Version of conda-build to use (e.g., '24.11.2'). If omitted, uses the action's pinned default."
    required: false
  output-dir:
    description: "Output directory for built packages"
    required: false
    default: "./build"
  verbose:
    description: "Enable verbose conda-build output"
    required: false
    default: "false"

outputs:
  packages:
    description: "Path to directory containing built package files"
```

---

## Behavior spec

### Recipe auto-discovery (D = discovery)

conda-build natively handles recipe directories — give it a dir, it finds the `meta.yaml`. So discovery just finds the directory and hands it off.

```
D1: recipe not provided → search workspace for a recipe directory in this order:
    1. conda.recipe/
    2. conda-recipe/
    3. recipe/
    4. . (repo root, if meta.yaml exists there)
    First match wins. Hand the directory to conda-build.

D2: recipe not provided + no recipe found at any standard path
    → error: "No recipe found. Searched: conda.recipe/, conda-recipe/, recipe/, ./meta.yaml.
              Set the 'recipe' input to specify the path."

D3: recipe not provided + multiple matches (e.g., both conda.recipe/ and recipe/ exist)
    → error: "Multiple recipe directories found: conda.recipe/, recipe/.
              Set the 'recipe' input to specify which one to use."

D4: recipe provided + path doesn't exist
    → error: "Recipe path not found: <path>"

D5: recipe provided + path exists → use it, skip auto-discovery.
    conda-build handles whatever it finds at that path.
```

### CBC resolution (R = resolution)

```
R1: cbc-preset=anaconda (default) + no cbc
    → fetch CBC from https://raw.githubusercontent.com/AnacondaRecipes/aggregate/main/conda_build_config.yaml

R2: cbc-preset=conda-forge + no cbc
    → fetch CBC from https://raw.githubusercontent.com/conda-forge/conda-forge-pinning-feedstock/main/recipe/conda_build_config.yaml

R3: cbc-preset=none + no cbc
    → no CBC provided to conda-build. It uses whatever it discovers
    natively (recipe-level CBC, conda-build defaults, etc.)

R4: cbc-preset=none + cbc=<path-or-URL>
    → use only the custom CBC, no preset base.

R5: cbc-preset=anaconda + cbc=<URL-or-path>
    → pass both to conda-build: --variant-config-files <preset-cbc> <custom-cbc>
    conda-build's native merge semantics apply: later files override
    earlier ones at the key level.

R6: cbc-preset=conda-forge + cbc=<URL-or-path>
    → same as R5 but with conda-forge preset as base.

R7: Fetched CBCs are written to temp files, not to the workspace.

R8: If CBC fetch fails (404, network error) → error with the URL that failed.

R9: cbc-preset unknown value → error: "Unknown cbc-preset: <value>. Must be 'anaconda', 'conda-forge', or 'none'."
```

### Channel defaults (C = channels)

```
C1: channels explicitly set → use exactly those channels, regardless of preset.
    No warnings, no "did you mean?" — user intent wins.

C2: channels not set + cbc-preset=anaconda → channels="defaults"

C3: channels not set + cbc-preset=conda-forge → channels="conda-forge"

C4: channels not set + cbc-preset=none → channels="defaults"
    (need some default; "defaults" is conda's own default)
```

### Build execution (B = build)

```
B1: conda-build is invoked with:
    --override-channels
    -c <each channel from channels input>
    --variant-config-files <resolved-cbc-path>
    --output-folder <output-dir>
    --no-anaconda-upload
    <recipe-path>

B2: python-version="3.12" → adds --python 3.12 to conda-build invocation

B3: python-version="3.11,3.12,3.13" → runs conda-build once with
    --python 3.11 --python 3.12 --python 3.13
    (conda-build handles the variant matrix internally)

B4: verbose=true → adds --verbose to conda-build invocation

B5: conda-build-version provided → after pixi setup, run
    `pixi add conda-build=<user-version>` to override the default pin,
    then proceed with build.

B6: conda-build-version not provided → uses the action's pinned default
    (version pinned in pixi.toml, updated by action maintainers)
```

### How the CBC actually works (important for recipe authors)

The CBC provides variables. The recipe must consume them. The action provides the CBC — it does NOT modify the recipe.

Three mechanisms by which CBC variables flow into a build:

1. **Jinja variables in meta.yaml** — `{{ compiler('c') }}`, `{{ pin_compatible('numpy') }}`.
   The recipe explicitly references CBC-defined values.

2. **run_exports from host dependencies** — if you list `openssl` in `host:`,
   openssl's run_exports constrain the runtime pin. The CBC controls *which version*
   of openssl gets resolved into host.

3. **pin_run_as_build** — CBC section that auto-generates run pins from host deps.

If a recipe says `- openssl >=3` without using CBC variables or relying on
run_exports, the CBC has no effect — the solver picks whatever matches.

**Implication:** the action "just works" for recipes that follow conda-build
conventions (Anaconda feedstocks, conda-forge recipes). For a user writing their
first meta.yaml, we should document how to write a CBC-aware recipe. This is a
docs problem, not an action problem.

### Outputs (O = outputs)

```
O1: On success, packages output = output-dir value
O2: At least one .conda or .tar.bz2 file exists in output-dir after successful build
```

### Input validation (V = validation)

```
V1: cbc-preset is not "anaconda", "conda-forge", or "none"
    → error: "Unknown cbc-preset: <value>. Must be 'anaconda', 'conda-forge', or 'none'."

V2: cbc is a URL that returns non-YAML content → error with details

V3: cbc is a local path that doesn't exist → error: "CBC file not found: <path>"
```

---

## Integration spec

End-to-end tests that run in CI against real builds:

```
INT-1: Zero-config build
       - Repo has recipe at conda.recipe/ (or recipe/)
       - Action invoked with no inputs
       → .conda file exists in ./build/

INT-2: Build with conda-forge preset
       - uses: build-package with cbc-preset=conda-forge, channels=conda-forge
       → .conda file exists in ./build/

INT-3: Build with custom CBC override
       - uses: build-package with cbc=<URL to aggregate CBC>
       → .conda file exists in ./build/
       (validates that cbc merges on top of preset)

INT-4: Build with local CBC override
       - Repo has a local cbc-overrides.yaml with one pin changed
       - uses: build-package with cbc=./cbc-overrides.yaml
       → .conda file exists in ./build/

INT-5: Build + upload workflow
       - build-package → upload-package
       → package uploaded to anaconda.org test channel

INT-6: Build compiled package — verify CBC pins flow through (anaconda preset)
       - Test recipe: numpy C extension using {{ compiler('c') }} and
         host dep on numpy (CBC-pinned via pin_compatible)
       - uses: build-package (default anaconda preset)
       → .conda file exists
       → Extract built package, inspect info/recipe/conda_build_config.yaml
         and verify compiler version + numpy pin match Anaconda's CBC

INT-6b: Same compiled recipe — conda-forge preset
       - uses: build-package with cbc-preset=conda-forge, channels=conda-forge
       → Extract and verify resolved CBC matches conda-forge's pinnings
         (compiler version and numpy pin will differ from INT-6)

INT-6c: Same compiled recipe — anaconda preset + local override
       - Local CBC overrides numpy pin to a specific version
       - uses: build-package with cbc=./cbc-overrides.yaml
       → Extract and verify: compiler from anaconda preset,
         numpy pin from local override

INT-6d: Same compiled recipe — conda-forge preset + local override
       - uses: build-package with cbc-preset=conda-forge, cbc=./cbc-overrides.yaml, channels=conda-forge
       → Extract and verify: compiler from conda-forge preset,
         numpy pin from local override

INT-6e: Same compiled recipe — cbc-preset=none + local CBC only
       - uses: build-package with cbc-preset=none, cbc=./full-cbc.yaml
       → Extract and verify: everything comes from the local CBC,
         no preset values leak through

INT-7: Multi-python build
       - uses: build-package with python-version="3.11,3.12"
       → .conda files exist for both python versions in ./build/

INT-8: Custom conda-build version
       - uses: build-package with conda-build-version="24.9.0"
       → build succeeds using that specific conda-build version
       → (verify with conda-build --version in a post-build step)

INT-9: Recipe auto-discovery
       - Repo has recipe at conda.recipe/
       - Action invoked with no recipe input
       → recipe is found and build succeeds

INT-10: Recipe auto-discovery failure
        - Repo has no recipe at any standard path
        - Action invoked with no recipe input
        → error message listing searched paths

INT-11: Recipe auto-discovery ambiguity
        - Repo has recipes at both conda.recipe/ and recipe/
        - Action invoked with no recipe input
        → error listing both found paths
```

---

## File structure

```
build-package/
├── SPEC.md             # This behavioral spec
├── action.yml          # Interface (inputs/outputs/steps)
├── pixi.toml           # Dependencies (conda, conda-build)
├── pixi.lock           # Generated
└── README.md           # User-facing docs

tests/
├── test-package/
│   ├── meta.yaml       # conda-build noarch python recipe (new)
│   └── recipe.yaml     # rattler-build recipe (existing, used by upload tests)
├── test-compiled/
│   ├── meta.yaml       # conda-build C extension recipe
│   └── src/
│       └── hello.c     # Minimal C extension
├── test-cbc-override/
│   └── cbc-overrides.yaml  # A CBC with one pin changed, for INT-4
├── pixi.toml
└── pixi.lock

.github/workflows/
├── test-build-package.yml   # INT-1 through INT-8
└── test-upload-package.yml  # Existing
```

## pixi.toml

```toml
[workspace]
name = "build-package-action"
channels = ["https://repo.anaconda.com/pkgs/main"]
platforms = ["linux-64", "osx-arm64"]

[dependencies]
conda = "=26.3.1"
conda-build = ">=24.11"
```

## Development flow

Use roborev at each step to review. 

1. **Step 1: SPEC.md + action.yml (interface only)** — the spec and the input/output contract. Stub steps that echo resolved values. Reviewable without implementation.
2. **Step 2: Test recipes** — `meta.yaml` for noarch python, `meta.yaml` + `hello.c` for compiled C extension, CBC override file.
3. **Step 3: CI workflow** — `test-build-package.yml` with INT-1 through INT-8. Tests will fail — that's the point. Reviewable as "do these tests cover the spec?"
4. **Step 4: Implementation** — fill in the composite steps until tests pass.

Steps 1-3 are the spec-driven part. They establish the contract before any implementation exists.

## Open questions

1. ~~**Channel defaults when using conda-forge preset.**~~ **Resolved:** preset infers channels when not explicitly set (`anaconda` → `defaults`, `conda-forge` → `conda-forge`). If the user sets `channels` explicitly, use exactly those — no second-guessing, even if it seems wrong.

2. **CBC merge semantics.** When `cbc` overrides `cbc-preset`, what does "merge" mean exactly? YAML key-level override (custom keys replace preset keys, everything else preserved)? Or full file replacement? conda-build's own variant merging has specific semantics for lists vs scalars. We should match conda-build's native behavior: when you pass multiple files to `--variant-config-files`, later files override earlier ones at the key level. So: `--variant-config-files <preset-cbc> <custom-cbc>`.

3. **Should the spec be markdown or executable?** The behavior specs (D1-V3) could be a bash test script that validates each assertion locally (mock the CBC fetch, check the constructed command). The integration specs (INT-1-8) can only run in CI. Recommendation: markdown spec + CI workflow. If someone wants to add a local test harness later, the spec gives them the assertions to implement.

4. **How does this land with Matt?** He built upload-package without specs. This is more process. Frame it as: "build-package is more complex (recipe discovery, CBC merging, channel defaults) — the spec helps us agree on the dozens of behavior decisions before we implement." Not "we're changing how the repo works."

## Not in v1

- rattler-build support (add after v1 works with conda-build)
- Cross-compilation
- Per-release Anaconda presets (`anaconda:2025.12`) — waiting on Charles's Q2 work
- Variant matrix control
- Caching
- Windows support (add platforms to pixi.toml, test on windows runners)
