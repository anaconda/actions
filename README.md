# Anaconda GitHub Actions

Reusable GitHub Actions for Anaconda customers.

## Available Actions

### [upload-package](./upload-package)

Upload conda or Python packages to Anaconda.org or Anaconda Repository (PSM/Anaconda Business).

**Upload to anaconda.org:**
```yaml
- uses: anaconda/github-actions/upload-package@v1
  with:
    token: ${{ secrets.ANACONDA_ORG_TOKEN }}
    owner: my-org
    packages: ./build/**/*.conda
```

**Upload to Anaconda Repository (PSM):**
```yaml
- uses: anaconda/github-actions/upload-package@v1
  with:
    token: ${{ secrets.PSM_TOKEN }}
    owner: my-channel
    packages: ./build/**/*.conda
    target-type: repository
    repository-url: https://pkgs.example.com/api/repo
```

See the [upload-package README](./upload-package/README.md) for full documentation.

## License

See [LICENSE](./LICENSE).
