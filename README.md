# Anaconda GitHub Actions

Reusable GitHub Actions for the Anaconda platform.

## Available Actions

### [setup-anaconda-cli](./setup-anaconda-cli)

Install the Anaconda CLI and optional tools in GitHub Actions.

```yaml
- uses: anaconda/github-actions/setup-anaconda-cli@0.2.0
```

See the [setup-anaconda-cli README](./setup-anaconda-cli/README.md) for full documentation.

### [upload-package](./upload-package)

Upload conda or Python packages to Anaconda.org, Anaconda Repository (PSM/Anaconda Business), or self-hosted Anaconda Platform.

**Upload to anaconda.org:**
```yaml
- uses: anaconda/github-actions/upload-package@0.2.0
  with:
    token: ${{ secrets.ANACONDA_ORG_TOKEN }}
    channel: my-org
    packages: ./build/**/*.conda
```

**Upload to Anaconda Repository (PSM):**
```yaml
- uses: anaconda/github-actions/upload-package@0.2.0
  with:
    token: ${{ secrets.PSM_TOKEN }}
    channel: my-channel
    packages: ./build/**/*.conda
    target-type: repository
    repository-url: https://pkgs.example.com/api/repo
```

**Upload to self-hosted Anaconda Platform:**
```yaml
- uses: anaconda/github-actions/upload-package@0.2.0
  with:
    token: ${{ secrets.AP_API_KEY }}
    channel: my-channel
    packages: ./build/**/*.conda
    target-type: self-hosted
    repository-url: https://anaconda.mycompany.com
```

See the [upload-package README](./upload-package/README.md) for full documentation.

## License

See [LICENSE](./LICENSE).
