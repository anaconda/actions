# Anaconda GitHub Actions

Reusable GitHub Actions for the Anaconda platform.

## Available Actions

### [setup-anaconda-cli](./setup-anaconda-cli)

Install the Anaconda CLI and optional tools in GitHub Actions.

```yaml
- uses: anaconda/actions/setup-anaconda-cli@0.2.0
```

See the [setup-anaconda-cli README](./setup-anaconda-cli/README.md) for full documentation.

### [upload-package](./upload-package)

Upload conda or Python packages to Anaconda.org or Package Security Manager (PSM).

**Upload to anaconda.org:**
```yaml
- uses: anaconda/actions/upload-package@0.2.0
  with:
    token: ${{ secrets.ANACONDA_ORG_TOKEN }}
    channel: my-org
    packages: ./build/**/*.conda
```

**Upload to Package Security Manager (PSM):**
```yaml
- uses: anaconda/actions/upload-package@0.2.0
  with:
    token: ${{ secrets.PSM_TOKEN }}
    channel: my-channel
    packages: ./build/**/*.conda
    target-type: psm
    repository-url: https://pkgs.example.com/api/repo
```

See the [upload-package README](./upload-package/README.md) for full documentation.

## License

See [LICENSE](./LICENSE).
