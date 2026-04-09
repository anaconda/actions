# Upload Package Action

Upload conda or Python packages to Anaconda.org or Anaconda Repository (PSM/Anaconda Business).

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `token` | API token for authentication | Yes | - |
| `packages` | Path or glob pattern to package files | Yes | - |
| `owner` | Package owner/channel (org name or channel) | Yes | - |
| `target-type` | `anaconda.org` or `repository` | No | `anaconda.org` |
| `repository-url` | URL of repository API (required for `repository` target) | No | - |
| `package-type` | `conda` or `pypi` (auto-detected if not specified) | No | - |
| `summary` | Package summary (anaconda.org only) | No | - |
| `private` | Make package private (anaconda.org only) | No | `false` |
| `force` | Overwrite existing packages | No | `false` |
| `verbose` | Enable verbose output | No | `false` |

## Usage

### Upload conda package to anaconda.org

```yaml
- name: Upload to anaconda.org
  uses: anaconda/github-actions/upload-package@v1
  with:
    token: ${{ secrets.ANACONDA_ORG_TOKEN }}
    owner: my-org
    packages: ./build/noarch/*.conda
```

### Upload wheel to anaconda.org

```yaml
- name: Upload wheel to anaconda.org
  uses: anaconda/github-actions/upload-package@v1
  with:
    token: ${{ secrets.ANACONDA_ORG_TOKEN }}
    owner: my-org
    packages: ./dist/*.whl
    summary: "My package description"
    private: true
```

### Upload to Anaconda Repository (PSM)

```yaml
- name: Upload to PSM
  uses: anaconda/github-actions/upload-package@v1
  with:
    token: ${{ secrets.PSM_TOKEN }}
    owner: my-channel
    packages: ./build/noarch/*.conda
    target-type: repository
    repository-url: https://pkgs.example.com/api/repo
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
        uses: anaconda/github-actions/upload-package@v1
        with:
          token: ${{ secrets.ANACONDA_ORG_TOKEN }}
          owner: my-org
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
        uses: anaconda/github-actions/upload-package@v1
        with:
          token: ${{ secrets.PSM_TOKEN }}
          owner: my-channel
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
- uses: anaconda/github-actions/upload-package@v1
  with:
    token: ${{ secrets.TOKEN }}
    owner: my-org
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
- uses: anaconda/github-actions/upload-package@v1
  with:
    token: ${{ secrets.TOKEN }}
    owner: my-channel
    packages: ./build/*.conda
    target-type: repository
    repository-url: https://pkgs.example.com/api/repo
    package-type: conda
```
