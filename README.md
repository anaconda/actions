# Anaconda GitHub Actions

Reusable GitHub Actions for the Anaconda platform.

## Available Actions

### [setup-anaconda-cli](./setup-anaconda-cli)

Install the Anaconda CLI and optional tools in GitHub Actions.

```yaml
- uses: anaconda/actions/setup-anaconda-cli@v0
```

See the [setup-anaconda-cli README](./setup-anaconda-cli/README.md) for full documentation.

### [upload-package](./upload-package)

Upload conda or Python packages to Anaconda.org or Package Security Manager (PSM).

**Upload to anaconda.org:**
```yaml
- uses: anaconda/actions/upload-package@v0
  with:
    token: ${{ secrets.ANACONDA_ORG_TOKEN }}
    channel: my-org
    packages: ./build/**/*.conda
```

**Upload to Package Security Manager (PSM):**
```yaml
- uses: anaconda/actions/upload-package@v0
  with:
    token: ${{ secrets.PSM_TOKEN }}
    channel: my-channel
    packages: ./build/**/*.conda
    target-type: psm
    repository-url: https://pkgs.example.com/api/repo
```

See the [upload-package README](./upload-package/README.md) for full documentation.

### [build-conda](./build-conda)

Build conda packages with conda-build. Zero required inputs — auto-discovers your recipe and uses Anaconda's CBC by default.

**Zero-config build:**
```yaml
- uses: anaconda/github-actions/build-conda@v1
```

**Build with conda-forge pins:**
```yaml
- uses: anaconda/github-actions/build-conda@v1
  with:
    cbc-preset: conda-forge
```

**Full build + upload workflow:**
```yaml
- uses: anaconda/github-actions/build-conda@v1
- uses: anaconda/github-actions/upload-package@v1
  with:
    token: ${{ secrets.ANACONDA_TOKEN }}
    owner: my-channel
    packages: ./build/**/*.conda
```

See the [build-conda README](./build-conda/README.md) for full documentation.

## License

See [LICENSE](./LICENSE).
