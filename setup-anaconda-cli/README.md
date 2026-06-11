# setup-anaconda-cli

Install the [Anaconda CLI](https://github.com/anaconda/anaconda-cli) and optional tools in GitHub Actions.

## Usage

### Basic usage

Install the latest version of ana:

```yaml
- uses: anaconda/actions/setup-anaconda-cli@0.2.0
```

### Install a specific version

```yaml
- uses: anaconda/actions/setup-anaconda-cli@0.2.0
  with:
    ana-version: "v0.1.6"
```

### Install ana with additional tools

Install ana along with anaconda-cli, pixi:

```yaml
- uses: anaconda/actions/setup-anaconda-cli@0.2.0
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

      - uses: anaconda/actions/setup-anaconda-cli@0.2.0
        id: setup-anaconda-cli
        with:
          ana-version: latest
          tools: pixi

      - name: Show installed version
        run: |
          echo "Installed ana version: ${{ steps.setup-anaconda-cli.outputs.ana-version }}"
          ana --version
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `ana-version` | Version of ana to install (e.g., `v0.1.6` or `latest`) | No | `latest` |
| `tools` | Space or comma-separated list of tools to install (e.g., `pixi` or `anaconda-cli, pixi`) | No | `''` |

## Outputs

| Output | Description |
|--------|-------------|
| `ana-version` | The version of ana that was installed |

## Platform support

This action supports:

- Linux (ubuntu-latest, ubuntu-22.04, etc.)
- macOS (macos-latest, macos-14, etc.)
- Windows (windows-latest, windows-2022, etc.)
