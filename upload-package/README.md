# Upload Package Action

Upload conda or Python packages to Anaconda.org, Anaconda Repository (PSM/Anaconda Business), or self-hosted Anaconda Platform.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `token` | API token for authentication | Yes | - |
| `packages` | Path or glob pattern to package files | Yes | - |
| `channel` | Channel to upload to (org name or channel) | Yes* | - |
| `owner` | **Deprecated**: Use `channel` instead | Yes* | - |

\* Either `channel` or `owner` must be provided. If both are provided, `channel` takes precedence.
| `target-type` | `anaconda.org`, `repository`, or `self-hosted` | No | `anaconda.org` |
| `repository-url` | Repository API URL for `repository` target, or domain for `self-hosted` target | No | - |
| `package-type` | `conda` or `pypi` (auto-detected if not specified) | No | - |
| `summary` | Package summary (anaconda.org only) | No | - |
| `private` | Make package private (anaconda.org only) | No | `false` |
| `labels` | Comma-separated labels (anaconda.org only, e.g., `main,dev`) | No | - |
| `force` | Overwrite existing packages | No | `false` |
| `verbose` | Enable verbose output | No | `false` |
| `disable-new-cli` | Disable new anaconda-client CLI parser (anaconda.org only) | No | `false` |

## Usage

### Upload conda package to anaconda.org

```yaml
- name: Upload to anaconda.org
  uses: anaconda/actions/upload-package@0.2.0
  with:
    token: ${{ secrets.ANACONDA_ORG_TOKEN }}
    channel: my-org
    packages: ./build/noarch/*.conda
```

### Upload wheel to anaconda.org

```yaml
- name: Upload wheel to anaconda.org
  uses: anaconda/actions/upload-package@0.2.0
  with:
    token: ${{ secrets.ANACONDA_ORG_TOKEN }}
    channel: my-org
    packages: ./dist/*.whl
    summary: "My package description"
    private: true
    labels: "main,dev"
```

### Upload to Anaconda Repository (PSM)

```yaml
- name: Upload to PSM
  uses: anaconda/actions/upload-package@0.2.0
  with:
    token: ${{ secrets.PSM_TOKEN }}
    channel: my-channel
    packages: ./build/noarch/*.conda
    target-type: repository
    repository-url: https://pkgs.example.com/api/repo
    package-type: conda
```

### Upload to self-hosted Anaconda Platform

```yaml
- name: Upload to self-hosted Anaconda Platform
  uses: anaconda/actions/upload-package@0.2.0
  with:
    token: ${{ secrets.AP_API_KEY }}
    channel: my-channel
    packages: ./build/noarch/*.conda
    target-type: self-hosted
    repository-url: https://anaconda.mycompany.com
    package-type: conda
```

## Full workflow example

```yaml
name: Build and Deploy

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup miniconda
        uses: conda-incubator/setup-miniconda@v3
        with:
          channels: defaults

      - name: Build conda package
        shell: bash -el {0}
        run: |
          conda install -y conda-build
          conda build recipe --output-folder ./build

      - name: Upload build artifact
        uses: actions/upload-artifact@v4
        with:
          name: conda-package
          path: ./build/noarch/*.conda

  publish-anaconda-org:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Download artifact
        uses: actions/download-artifact@v4
        with:
          name: conda-package
          path: ./dist

      - name: Upload to anaconda.org
        uses: anaconda/actions/upload-package@0.2.0
        with:
          token: ${{ secrets.ANACONDA_ORG_TOKEN }}
          channel: my-org
          packages: ./dist/*.conda
          private: true

  publish-psm:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Download artifact
        uses: actions/download-artifact@v4
        with:
          name: conda-package
          path: ./dist

      - name: Upload to PSM
        uses: anaconda/actions/upload-package@0.2.0
        with:
          token: ${{ secrets.PSM_TOKEN }}
          channel: my-channel
          packages: ./dist/*.conda
          target-type: repository
          repository-url: https://pkgs.example.com/api/repo
```

## Migrating from existing workflows

### Before (anaconda.org)

```yaml
- name: Install anaconda-client
  run: conda install -y anaconda-client
- name: Upload
  run: |
    anaconda --token ${{ secrets.TOKEN }} upload \
      --user my-org \
      --private \
      ./build/*.conda
```

### After

```yaml
- uses: anaconda/actions/upload-package@0.2.0
  with:
    token: ${{ secrets.TOKEN }}
    channel: my-org
    packages: ./build/*.conda
    private: true
```

### Before (PSM)

```yaml
- name: Install conda-repo-cli
  run: conda install -y conda-repo-cli
- name: Upload
  run: |
    conda repo config --set sites.psm.url https://pkgs.example.com/api/repo
    conda repo --token ${{ secrets.TOKEN }} --site psm upload \
      --channel my-channel \
      --package-type conda \
      ./build/*.conda
```

### After

```yaml
- uses: anaconda/actions/upload-package@0.2.0
  with:
    token: ${{ secrets.TOKEN }}
    channel: my-channel
    packages: ./build/*.conda
    target-type: repository
    repository-url: https://pkgs.example.com/api/repo
    package-type: conda
```
