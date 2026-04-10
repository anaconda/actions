"""
Integration tests for build.py — these actually invoke conda-build.

Run with:
    cd build-package && pixi run -e integration pytest tests/test_integration.py -v

Requires the integration pixi environment (conda-build + pytest).  All tests
that avoid the network use cbc-preset=none with a local CBC file so they are
repeatable offline.
"""

from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

import pytest
import yaml

# The integration tests live at build-package/tests/test_integration.py.
# Recipes live at <repo-root>/tests/{test-package,test-compiled}.
REPO_ROOT = Path(__file__).parent.parent.parent


# ── Helpers ────────────────────────────────────────────────────────────────────


def extract_embedded_cbc(pkg: Path) -> dict | None:
    """
    Pull info/recipe/conda_build_config.yaml out of a .conda file.
    Returns None when the file isn't present (normal for noarch packages).
    """
    with zipfile.ZipFile(pkg) as z:
        info_members = [n for n in z.namelist() if n.startswith("info-")]
        if not info_members:
            return None
        with z.open(info_members[0]) as f:
            data = f.read()

    with tarfile.open(fileobj=io.BytesIO(data), mode="r:zst") as t:
        try:
            member = t.getmember("info/recipe/conda_build_config.yaml")
            return yaml.safe_load(t.extractfile(member).read().decode())
        except KeyError:
            return None


def run_build(
    monkeypatch,
    tmp_path: Path,
    recipe_rel: str,
    *,
    preset: str = "none",
    cbc: str = "",
    channels: str = "",
    python_version: str = "",
) -> Path:
    """
    Call build.main() with the given inputs.  Returns the output directory.
    Asserts that main() returns 0 (success).
    """
    from build import main

    output_dir = tmp_path / "build"

    monkeypatch.setenv("GITHUB_WORKSPACE", str(REPO_ROOT))
    monkeypatch.setenv("INPUT_RECIPE", recipe_rel)
    monkeypatch.setenv("INPUT_CBC_PRESET", preset)
    monkeypatch.setenv("INPUT_CBC", cbc)
    monkeypatch.setenv("INPUT_CHANNELS", channels)
    monkeypatch.setenv("INPUT_PYTHON_VERSION", python_version)
    monkeypatch.setenv("INPUT_OUTPUT_DIR", str(output_dir))
    monkeypatch.setenv("INPUT_VERBOSE", "false")
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "github_output.txt"))

    rc = main()
    assert rc == 0, f"build.main() returned {rc}"
    return output_dir


# ── Basic build tests ──────────────────────────────────────────────────────────


class TestBuilds:
    def test_noarch_package_builds(self, monkeypatch, tmp_path):
        """The noarch test recipe produces at least one .conda file."""
        out = run_build(monkeypatch, tmp_path, "build-package/tests/test-package", preset="none")
        packages = list(out.rglob("*.conda")) + list(out.rglob("*.tar.bz2"))
        assert len(packages) >= 1, f"No packages found under {out}"

    def test_compiled_package_builds(self, monkeypatch, tmp_path):
        """The compiled C extension recipe builds with a minimal local CBC."""
        # A CBC is required here: without one, pin_compatible('numpy') in the
        # recipe cannot resolve because conda-build doesn't know which numpy
        # (or which python) to install in the host environment.
        out = run_build(
            monkeypatch,
            tmp_path,
            "build-package/tests/test-compiled",
            preset="none",
            cbc="build-package/tests/test-cbc-override/cbc-overrides.yaml",
            python_version="3.12",
        )
        packages = list(out.rglob("*.conda")) + list(out.rglob("*.tar.bz2"))
        assert len(packages) >= 1, f"No packages found under {out}"

    def test_github_output_written(self, monkeypatch, tmp_path):
        """main() writes packages=<output-dir> to $GITHUB_OUTPUT."""
        out = run_build(monkeypatch, tmp_path, "build-package/tests/test-package", preset="none")
        github_output = tmp_path / "github_output.txt"
        assert github_output.exists()
        content = github_output.read_text()
        assert f"packages={out}" in content


# ── CBC propagation tests ──────────────────────────────────────────────────────
#
# These are the tests that answer "did --variant-config-files actually do
# anything?"  We use a local CBC override (numpy: 1.26.*) so no network is
# needed, and the expected value is deterministic.


class TestCbcPropagation:
    CBC_OVERRIDE = "build-package/tests/test-cbc-override/cbc-overrides.yaml"

    def test_local_cbc_override_reaches_compiled_package(self, monkeypatch, tmp_path):
        """
        Core end-to-end assertion: a CBC override passed via the `cbc` input
        must appear in the embedded conda_build_config.yaml of the built package.

        If this test fails it means --variant-config-files was not passed to
        conda-build, or was passed incorrectly, despite all unit tests passing.
        """
        out = run_build(
            monkeypatch,
            tmp_path,
            "build-package/tests/test-compiled",
            preset="none",
            cbc=self.CBC_OVERRIDE,
            python_version="3.12",
        )

        packages = list(out.rglob("*.conda"))
        assert len(packages) >= 1, f"No .conda files under {out}"

        cbc = extract_embedded_cbc(packages[0])
        assert cbc is not None, (
            "No embedded conda_build_config.yaml found in compiled package. "
            "conda-build should embed the resolved variant config for compiled packages."
        )

        numpy_pin = cbc.get("numpy")
        assert numpy_pin is not None, (
            f"'numpy' key missing from embedded CBC. "
            f"Available keys: {sorted(cbc.keys())}"
        )
        assert "1.26" in str(numpy_pin), (
            f"Expected numpy pin to contain '1.26' (from cbc-overrides.yaml), "
            f"got: {numpy_pin!r}"
        )

    def test_different_cbc_gives_different_pin(self, monkeypatch, tmp_path):
        """
        Sanity check: using a different CBC override (numpy 2.0.*) produces a
        different pin than our 1.26.* override.  This verifies that
        test_local_cbc_override_reaches_compiled_package is testing something
        meaningful and not passing by coincidence.
        """
        CBC_OVERRIDE_2 = "build-package/tests/test-cbc-override-2/cbc-overrides-2.yaml"
        out = run_build(
            monkeypatch,
            tmp_path,
            "build-package/tests/test-compiled",
            preset="none",
            cbc=CBC_OVERRIDE_2,
            python_version="3.12",
        )

        packages = list(out.rglob("*.conda"))
        assert len(packages) >= 1, f"No packages found under {out}"

        cbc = extract_embedded_cbc(packages[0])
        assert cbc is not None, "No embedded CBC found in compiled package"

        numpy_pin = cbc.get("numpy")
        assert numpy_pin is not None, (
            f"'numpy' key missing from embedded CBC. "
            f"Available keys: {sorted(cbc.keys())}"
        )
        assert "2.0" in str(numpy_pin), (
            f"Expected numpy pin to contain '2.0' (from cbc-overrides-2.yaml), "
            f"got: {numpy_pin!r}"
        )
        assert "1.26" not in str(numpy_pin), (
            f"Got 1.26 numpy pin from alternate CBC — something is wrong: {numpy_pin!r}"
        )
