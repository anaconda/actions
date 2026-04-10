"""
build.py — conda-build runner for the build-package GitHub Action.

All public functions take plain Python types (str, Path, list) so they can be
exercised in unit tests without touching conda-build or the network.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
import yaml


# ── CBC preset URLs ────────────────────────────────────────────────────────────

PRESET_URLS: dict[str, str] = {
    "anaconda": (
        "https://raw.githubusercontent.com/AnacondaRecipes/aggregate/master/"
        "conda_build_config.yaml"
    ),
    "conda-forge": (
        "https://raw.githubusercontent.com/conda-forge/conda-forge-pinning-feedstock/"
        "main/recipe/conda_build_config.yaml"
    ),
}

# Ordered search candidates for recipe auto-discovery (D1).
SEARCH_CANDIDATES = ["conda.recipe", "conda-recipe", "recipe"]


# ── Recipe discovery ───────────────────────────────────────────────────────────


def discover_recipe(recipe_input: str, workspace: Path) -> Path:
    """
    D1-D5: Return the recipe path to hand to conda-build.

    If *recipe_input* is provided, validate and return it (D4/D5).
    Otherwise, search standard locations and raise on zero or multiple matches (D2/D3).
    """
    if recipe_input:
        path = Path(recipe_input)
        if not path.is_absolute():
            path = workspace / recipe_input
        if not path.exists():
            raise ValueError(f"Recipe path not found: {recipe_input}")
        return path

    found: list[Path] = []
    for candidate in SEARCH_CANDIDATES:
        p = workspace / candidate
        if p.is_dir():
            found.append(p)
    if (workspace / "meta.yaml").is_file():
        found.append(workspace)

    if not found:
        raise ValueError(
            "No recipe found. "
            "Searched: conda.recipe/, conda-recipe/, recipe/, ./meta.yaml. "
            "Set the 'recipe' input to specify the path."
        )

    if len(found) > 1:
        listing = _format_paths(found, workspace)
        raise ValueError(
            f"Multiple recipe directories found: {listing}. "
            "Set the 'recipe' input to specify which one to use."
        )

    return found[0]


def _format_paths(paths: list[Path], workspace: Path) -> str:
    """Format a list of paths relative to workspace for error messages."""
    labels = []
    for p in paths:
        rel = str(p.relative_to(workspace))
        # Append trailing slash for named subdirs; leave "." bare for root.
        if p.is_dir() and rel != ".":
            rel += "/"
        labels.append(rel)
    return ", ".join(labels)


# ── CBC resolution ─────────────────────────────────────────────────────────────


def fetch_url(url: str, dest: Path) -> None:
    """Download *url* to *dest*, raising RuntimeError on network failure."""
    try:
        urllib.request.urlretrieve(url, dest)
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to fetch CBC from {url}: {exc}") from exc


def preset_cbc_url(preset: str) -> str | None:
    """
    R1-R3/R9: Return the fetch URL for a preset, or None for 'none'.

    This is a pure function — no I/O — so it can be unit-tested directly.
    Raises ValueError for unknown preset values (R9).
    """
    if preset not in ("anaconda", "conda-forge", "none"):
        raise ValueError(
            f"Unknown cbc-preset: {preset}. "
            "Must be 'anaconda', 'conda-forge', or 'none'."
        )
    return PRESET_URLS.get(preset)


def resolve_cbc(
    preset: str, custom_cbc: str, tmp_dir: Path, workspace: Path | None = None
) -> list[Path]:
    """
    R1-R9: Return an ordered list of CBC paths to pass to conda-build.

    Fetches preset and/or custom URLs into *tmp_dir*.  Local paths are
    resolved relative to *workspace* (defaults to CWD).  Raises ValueError
    for unknown preset (R9), missing local path (V3), or non-YAML URL
    content (V2).  Raises RuntimeError on fetch failure (R8).
    """
    url = preset_cbc_url(preset)  # raises on unknown preset (R9)

    cbc_files: list[Path] = []

    if url is not None:
        dest = tmp_dir / f"cbc-{preset}.yaml"
        fetch_url(url, dest)
        cbc_files.append(dest)

    if custom_cbc:
        if custom_cbc.startswith(("http://", "https://")):
            dest = tmp_dir / "cbc-custom.yaml"
            fetch_url(custom_cbc, dest)
            _assert_valid_yaml(dest, custom_cbc)
            cbc_files.append(dest)
        else:
            base = workspace if workspace is not None else Path(".")
            path = (base / custom_cbc).resolve()
            if not path.is_file():
                raise ValueError(f"CBC file not found: {custom_cbc}")
            cbc_files.append(path)

    return cbc_files


def _assert_valid_yaml(path: Path, source: str) -> None:
    try:
        yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise ValueError(
            f"CBC URL did not return valid YAML: {source}: {exc}"
        ) from exc


# ── Channel resolution ─────────────────────────────────────────────────────────


def resolve_channels(channels_input: str, preset: str) -> list[str]:
    """C1-C4: Return the list of channels for --override-channels."""
    if channels_input:
        return [c.strip() for c in channels_input.split(",") if c.strip()]
    if preset == "conda-forge":
        return ["conda-forge"]
    return ["defaults"]


# ── Build command construction ─────────────────────────────────────────────────


def build_command(
    recipe: Path,
    channels: list[str],
    cbc_files: list[Path],
    output_dir: str,
    python_versions: list[str],
    verbose: bool,
) -> list[str]:
    """
    B1-B4: Return the conda-build argv list (without any 'pixi run' prefix).

    The caller prepends whatever is needed to run conda-build in the right env.
    """
    cmd = ["conda-build", "--override-channels"]

    for ch in channels:
        cmd += ["-c", ch]

    if cbc_files:
        cmd += ["--variant-config-files", *[str(f) for f in cbc_files]]

    cmd += ["--output-folder", output_dir, "--no-anaconda-upload"]

    for py in python_versions:
        cmd += ["--python", py]

    if verbose:
        cmd.append("--verbose")

    cmd.append(str(recipe))
    return cmd


# ── Entry point ────────────────────────────────────────────────────────────────


def get_input(name: str, default: str = "") -> str:
    """Read a GitHub Actions input from the INPUT_* environment variable."""
    key = "INPUT_" + name.upper().replace("-", "_")
    return os.environ.get(key, default)


def set_output(name: str, value: str) -> None:
    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a") as fh:
            fh.write(f"{name}={value}\n")


def main() -> int:
    workspace = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()

    recipe_input = get_input("recipe")
    preset = get_input("cbc-preset", "anaconda")
    custom_cbc = get_input("cbc")
    channels_input = get_input("channels")
    python_version_input = get_input("python-version")
    output_dir = get_input("output-dir", "./build")
    verbose = get_input("verbose", "false").lower() == "true"

    python_versions = (
        [v.strip() for v in python_version_input.split(",") if v.strip()]
        if python_version_input
        else []
    )

    with tempfile.TemporaryDirectory(prefix="cbc-") as tmp_str:
        tmp_dir = Path(tmp_str)
        try:
            recipe = discover_recipe(recipe_input, workspace)
            cbc_files = resolve_cbc(preset, custom_cbc, tmp_dir, workspace)
            channels = resolve_channels(channels_input, preset)
        except (ValueError, RuntimeError) as exc:
            print(f"::error::{exc}", file=sys.stderr)
            return 1

        cmd = ["pixi", "run"] + build_command(
            recipe, channels, cbc_files, output_dir, python_versions, verbose
        )
        print(f"Running: {' '.join(cmd)}", flush=True)
        result = subprocess.run(cmd)
        if result.returncode != 0:
            return result.returncode

    set_output("packages", output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
