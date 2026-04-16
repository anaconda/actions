# setup-ana

Install the [ana CLI](https://github.com/anaconda/ana-cli) and optional tools (anaconda-cli, pixi, etc.) in GitHub Actions.

## Usage

### Basic usage

Install the latest version of ana:

```yaml
- uses: anaconda/github-actions/setup-ana@v1
```

### Install a specific version

```yaml
- uses: anaconda/github-actions/setup-ana@v1
  with:
    ana-version: "1.0.0"
```

### Install ana with additional tools

Install ana along with anaconda-cli, pixi:

```yaml
- uses: anaconda/github-actions/setup-ana@v1
  with:
    tools: anaconda-cli, pixi
```

### Full example

```yaml
name: CI
on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: anaconda/github-actions/setup-ana@v1
        id: setup-ana
        with:
          ana-version: latest
          tools: pixi

      - name: Show installed version
        run: |
          echo "Installed ana version: ${{ steps.setup-ana.outputs.ana-version }}"
          ana --version
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `ana-version` | Version of ana to install (e.g., `1.0.0` or `latest`) | No | `latest` |
| `tools` | Space or comma-separated list of tools to install (e.g., `pixi` or `anaconda-cli, pixi`) | No | `''` |
| `github-token` | GitHub token for accessing private repositories | No | `${{ github.token }}` |

## Outputs

| Output | Description |
|--------|-------------|
| `ana-version` | The version of ana that was installed |

## Platform support

This action supports:

- Linux (ubuntu-latest, ubuntu-22.04, etc.)
- macOS (macos-latest, macos-14, etc.)
- Windows (windows-latest, windows-2022, etc.)
