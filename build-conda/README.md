# build-conda

Build a conda package with conda-build. Zero required inputs — auto-discovers your recipe and uses Anaconda's conda_build_config.yaml (CBC) by default.

## Usage

```yaml
# Zero-config: finds recipe, uses Anaconda CBC, builds against defaults
- uses: anaconda/github-actions/build-conda@v1
```

```yaml
# Build with conda-forge pins
- uses: anaconda/github-actions/build-conda@v1
  with:
    cbc-preset: conda-forge
    channels: conda-forge
```

```yaml
# Layer your own overrides on top of Anaconda's CBC
- uses: anaconda/github-actions/build-conda@v1
  with:
    cbc: ./my-overrides.yaml
```

```yaml
# Full build + upload workflow
- uses: anaconda/github-actions/build-conda@v1
- uses: anaconda/github-actions/upload-package@v1
  with:
    token: ${{ secrets.ANACONDA_TOKEN }}
    owner: my-channel
    packages: ${{ steps.build.outputs.packages }}/**/*.conda
```

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `recipe` | No | auto-discovered | Path to conda recipe directory. Searches `conda.recipe/`, `conda-recipe/`, `recipe/`, `./meta.yaml` if omitted. |
| `cbc-preset` | No | `anaconda` | Built-in CBC preset: `anaconda`, `conda-forge`, or `none`. |
| `cbc` | No | | URL or local path to a `conda_build_config.yaml` to merge on top of the preset. |
| `channels` | No | inferred from preset | Comma-separated conda channels. Defaults: `anaconda` → `defaults`, `conda-forge` → `conda-forge`. |
| `python-version` | No | | Python version(s) to build for. Single (`3.12`) or comma-separated (`3.11,3.12,3.13`). |
| `conda-build-version` | No | pinned default | Override the conda-build version used by the action. |
| `output-dir` | No | `./build` | Output directory for built packages. |
| `verbose` | No | `false` | Enable verbose conda-build output. |

## Outputs

| Output | Description |
|---|---|
| `packages` | Path to the directory containing built package files. |

## How recipe discovery works

If `recipe` is not set, the action searches the workspace in this order and uses the first match:

1. `conda.recipe/`
2. `conda-recipe/`
3. `recipe/`
4. `./meta.yaml` (repo root)

If no recipe is found, or multiple are found, the action fails with a message listing the paths it searched or found.

## How CBCs work

The CBC preset provides the base set of version pins (numpy, python, compilers, etc.). The optional `cbc` input lets you layer overrides on top — later files override earlier ones at the key level, using conda-build's native `--variant-config-files` merge semantics.

```
cbc-preset=anaconda  →  Anaconda's aggregate CBC (master branch)
cbc-preset=conda-forge  →  conda-forge pinning feedstock
cbc-preset=none  →  no preset; use only what's in `cbc` (if provided)
```

For the CBC to affect a build, the recipe must consume CBC variables — via Jinja expressions like `{{ compiler('c') }}` or `{{ pin_compatible('numpy') }}`, or via `pin_run_as_build`. Recipes that don't reference CBC variables are unaffected by the preset.

## Examples

### Build for multiple Python versions

```yaml
- uses: anaconda/github-actions/build-conda@v1
  with:
    python-version: "3.11,3.12,3.13"
```

### Use a specific conda-build version

```yaml
- uses: anaconda/github-actions/build-conda@v1
  with:
    conda-build-version: "24.9.0"
```

### Build with no preset (fully custom CBC)

```yaml
- uses: anaconda/github-actions/build-conda@v1
  with:
    cbc-preset: none
    cbc: ./my-full-cbc.yaml
```

---

## Future actions in this family

- **build-rattler** — build conda packages with rattler-build (recipe v2 / `recipe.yaml`)
- **build-wheel** — build Python wheel packages with build/pip
