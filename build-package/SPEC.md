# `build-package` — Spec

## Overview

A GitHub Action that runs conda-build. Zero required inputs if your repo has a
recipe in the obvious place. Sensible defaults for everything: finds the recipe,
uses Anaconda's CBC, builds against `defaults` channel.

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

---

## Interface

```yaml
inputs:
  recipe:
    description: "Path to the conda recipe directory. Auto-discovered if omitted."
    required: false
  cbc-preset:
    description: 'Built-in CBC preset: "anaconda" (default), "conda-forge", or "none"'
    required: false
    default: "anaconda"
  cbc:
    description: "URL or local path to a conda_build_config.yaml. Merged on top of cbc-preset."
    required: false
  channels:
    description: "Comma-separated list of conda channels. Inferred from preset if omitted."
    required: false
  python-version:
    description: "Python version(s): single ('3.12') or comma-separated ('3.11,3.12,3.13')."
    required: false
  conda-build-version:
    description: "Version of conda-build to use. Uses action's pinned default if omitted."
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

## Recipe auto-discovery (D)

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

## CBC resolution (R)

```
R1: cbc-preset=anaconda (default) + no cbc
    → fetch CBC from https://raw.githubusercontent.com/AnacondaRecipes/aggregate/master/conda_build_config.yaml

R2: cbc-preset=conda-forge + no cbc
    → fetch CBC from https://raw.githubusercontent.com/conda-forge/conda-forge-pinning-feedstock/main/recipe/conda_build_config.yaml

R3: cbc-preset=none + no cbc
    → no CBC provided to conda-build. It uses whatever it discovers natively.

R4: cbc-preset=none + cbc=<path-or-URL>
    → use only the custom CBC, no preset base.

R5: cbc-preset=anaconda + cbc=<URL-or-path>
    → --variant-config-files <preset-cbc> <custom-cbc>
    conda-build's native merge: later files override earlier ones at the key level.

R6: cbc-preset=conda-forge + cbc=<URL-or-path>
    → same as R5 but with conda-forge preset as base.

R7: Fetched CBCs are written to temp files, not to the workspace.

R8: If CBC fetch fails (404, network error) → error with the URL that failed.

R9: cbc-preset unknown value → error: "Unknown cbc-preset: <value>. Must be 'anaconda', 'conda-forge', or 'none'."
```

## Channel defaults (C)

```
C1: channels explicitly set → use exactly those channels, regardless of preset.

C2: channels not set + cbc-preset=anaconda → channels="defaults"

C3: channels not set + cbc-preset=conda-forge → channels="conda-forge"

C4: channels not set + cbc-preset=none → channels="defaults"
```

## Build execution (B)

```
B1: conda-build is invoked with:
    --override-channels
    -c <each channel from channels input>
    --variant-config-files <resolved-cbc-path(s)>  (omitted when cbc-preset=none and no cbc)
    --output-folder <output-dir>
    --no-anaconda-upload
    <recipe-path>

B2: python-version="3.12" → adds --python 3.12 to conda-build invocation

B3: python-version="3.11,3.12,3.13" → runs conda-build once with
    --python 3.11 --python 3.12 --python 3.13

B4: verbose=true → adds --verbose to conda-build invocation

B5: conda-build-version provided → after pixi setup, run
    `pixi add conda-build=<user-version>` to override the default pin.

B6: conda-build-version not provided → uses the action's pinned default.
```

## Outputs (O)

```
O1: On success, packages output = output-dir value
O2: At least one .conda or .tar.bz2 file exists in output-dir after successful build
```

## Input validation (V)

```
V1: cbc-preset is not "anaconda", "conda-forge", or "none"
    → error: "Unknown cbc-preset: <value>. Must be 'anaconda', 'conda-forge', or 'none'."

V2: cbc is a URL that returns non-YAML content → error with details

V3: cbc is a local path that doesn't exist → error: "CBC file not found: <path>"
```

---

## Integration tests (INT)

```
INT-1: Zero-config build
       - Repo has recipe at conda.recipe/ (or recipe/)
       - Action invoked with no inputs
       → .conda file exists in ./build/

INT-2: Build with conda-forge preset
       - uses: build-package with cbc-preset=conda-forge, channels=conda-forge
       → .conda file exists in ./build/

INT-3: Build with custom CBC override (URL)
       - uses: build-package with cbc=<URL to aggregate CBC>
       → .conda file exists in ./build/

INT-4: Build with local CBC override
       - Repo has build-package/tests/test-cbc-override/cbc-overrides.yaml
       - uses: build-package with cbc=build-package/tests/test-cbc-override/cbc-overrides.yaml
       → .conda file exists in ./build/

INT-5: Build + upload workflow
       - build-package → upload-package
       → package uploaded to anaconda.org test channel

INT-6: Build compiled package — verify CBC pins flow through (anaconda preset)
       - Test recipe: C extension with {{ compiler('c') }} and numpy host dep
       - uses: build-package (default anaconda preset)
       → .conda file exists; info/recipe/conda_build_config.yaml inside package
         reflects anaconda CBC pins

INT-6b: Same compiled recipe — conda-forge preset
       - uses: build-package with cbc-preset=conda-forge, channels=conda-forge
       → .conda file exists; CBC pins reflect conda-forge values

INT-6c: Same compiled recipe — anaconda preset + local override
       - Local CBC overrides numpy pin to a specific version
       - uses: build-package with cbc=./cbc-overrides.yaml
       → .conda file exists; compiler from anaconda preset, numpy pin from override

INT-6d: Same compiled recipe — conda-forge preset + local override
       - uses: build-package with cbc-preset=conda-forge, cbc=./cbc-overrides.yaml, channels=conda-forge
       → .conda file exists; compiler from conda-forge, numpy pin from override

INT-6e: Same compiled recipe — cbc-preset=none + local CBC only
       - uses: build-package with cbc-preset=none, cbc=./full-cbc.yaml
       → .conda file exists; no preset values leak through

INT-7: Multi-python build
       - uses: build-package with python-version="3.11,3.12"
       → .conda files exist for both python versions in ./build/

INT-8: Custom conda-build version
       - uses: build-package with conda-build-version="24.9.0"
       → build succeeds; conda-build --version confirms correct version

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

## How CBC variables flow into a build

The CBC provides variables. The recipe must consume them. The action supplies
the CBC — it does **not** modify the recipe.

Three mechanisms:

1. **Jinja variables in meta.yaml** — `{{ compiler('c') }}`, `{{ pin_compatible('numpy') }}`.
   The recipe explicitly references CBC-defined values.

2. **run_exports from host dependencies** — listing `openssl` in `host:` means
   openssl's run_exports constrain the runtime pin; the CBC controls which version
   of openssl gets resolved into host.

3. **pin_run_as_build** — CBC section that auto-generates run pins from host deps.

If a recipe says `- openssl >=3` without using CBC variables or relying on
run_exports, the CBC has no effect — the solver picks whatever matches.

This works out of the box for recipes that follow conda-build conventions
(Anaconda feedstocks, conda-forge recipes). For recipes that don't use CBC
variables at all, the preset has no effect and that's fine.

---

## Not in v1

- rattler-build support
- Cross-compilation
- Per-release Anaconda presets (`anaconda:2025.12`)
- Variant matrix control beyond `python-version`
- Build caching
- Windows runners (add `win-64` to `pixi.toml` platforms)
