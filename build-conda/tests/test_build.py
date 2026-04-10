"""Tests for build.py.

Pure-logic tests use tmp_path and need no network.
CBC resolution tests fetch the real remote files — they verify the full path
from URL → disk → valid YAML with expected keys, no mocks.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from build import (
    PRESET_URLS,
    SEARCH_CANDIDATES,
    build_command,
    discover_recipe,
    fetch_url,
    preset_cbc_url,
    resolve_cbc,
    resolve_channels,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def make_dir(base: Path, name: str) -> Path:
    d = base / name
    d.mkdir()
    return d


# ── discover_recipe ────────────────────────────────────────────────────────────


class TestDiscoverRecipe:
    def test_explicit_relative_path(self, tmp_path):
        recipe = make_dir(tmp_path, "my-recipe")
        assert discover_recipe("my-recipe", tmp_path) == recipe

    def test_explicit_absolute_path(self, tmp_path):
        recipe = make_dir(tmp_path, "my-recipe")
        assert discover_recipe(str(recipe), tmp_path) == recipe

    def test_explicit_path_missing_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Recipe path not found: no-such"):
            discover_recipe("no-such", tmp_path)

    def test_auto_discovers_conda_recipe(self, tmp_path):
        d = make_dir(tmp_path, "conda.recipe")
        assert discover_recipe("", tmp_path) == d

    def test_auto_discovers_conda_hyphen_recipe(self, tmp_path):
        d = make_dir(tmp_path, "conda-recipe")
        assert discover_recipe("", tmp_path) == d

    def test_auto_discovers_recipe_dir(self, tmp_path):
        d = make_dir(tmp_path, "recipe")
        assert discover_recipe("", tmp_path) == d

    def test_auto_discovers_root_meta_yaml(self, tmp_path):
        (tmp_path / "meta.yaml").write_text("package:\n  name: t\n  version: 1\n")
        assert discover_recipe("", tmp_path) == tmp_path

    def test_no_recipe_raises(self, tmp_path):
        with pytest.raises(ValueError, match="No recipe found"):
            discover_recipe("", tmp_path)

    def test_no_recipe_lists_all_searched_paths(self, tmp_path):
        with pytest.raises(ValueError, match="conda.recipe.*conda-recipe.*recipe.*meta.yaml"):
            discover_recipe("", tmp_path)

    def test_ambiguous_raises(self, tmp_path):
        make_dir(tmp_path, "conda.recipe")
        make_dir(tmp_path, "recipe")
        with pytest.raises(ValueError, match="Multiple recipe directories found"):
            discover_recipe("", tmp_path)

    def test_ambiguous_message_names_both_dirs(self, tmp_path):
        make_dir(tmp_path, "conda.recipe")
        make_dir(tmp_path, "recipe")
        with pytest.raises(ValueError, match=r"conda\.recipe/.*recipe/"):
            discover_recipe("", tmp_path)

    def test_each_candidate_wins_alone(self, tmp_path):
        for candidate in SEARCH_CANDIDATES:
            ws = tmp_path / candidate
            ws.mkdir()
            assert discover_recipe("", tmp_path) == ws
            ws.rmdir()

    def test_root_meta_yaml_plus_subdir_is_ambiguous(self, tmp_path):
        (tmp_path / "meta.yaml").write_text("package:\n  name: t\n  version: 1\n")
        make_dir(tmp_path, "recipe")
        with pytest.raises(ValueError, match="Multiple recipe directories found"):
            discover_recipe("", tmp_path)


# ── preset_cbc_url ─────────────────────────────────────────────────────────────


class TestPresetCbcUrl:
    def test_anaconda_points_at_aggregate(self):
        url = preset_cbc_url("anaconda")
        assert url is not None
        assert "AnacondaRecipes/aggregate" in url
        assert url.endswith("conda_build_config.yaml")

    def test_conda_forge_points_at_pinning_feedstock(self):
        url = preset_cbc_url("conda-forge")
        assert url is not None
        assert "conda-forge/conda-forge-pinning-feedstock" in url
        assert url.endswith("conda_build_config.yaml")

    def test_none_returns_none(self):
        assert preset_cbc_url("none") is None

    def test_unknown_preset_raises(self):
        with pytest.raises(ValueError, match="Unknown cbc-preset: bad"):
            preset_cbc_url("bad")

    def test_unknown_preset_message_names_valid_options(self):
        with pytest.raises(ValueError, match="'anaconda'.*'conda-forge'.*'none'"):
            preset_cbc_url("invalid")

    def test_all_known_presets_in_preset_urls(self):
        for preset, expected_url in PRESET_URLS.items():
            assert preset_cbc_url(preset) == expected_url


# ── fetch_url ──────────────────────────────────────────────────────────────────


class TestFetchUrl:
    def test_fetches_anaconda_cbc(self, tmp_path):
        dest = tmp_path / "anaconda.yaml"
        fetch_url(PRESET_URLS["anaconda"], dest)
        assert dest.exists()
        assert dest.stat().st_size > 0

    def test_fetches_conda_forge_cbc(self, tmp_path):
        dest = tmp_path / "conda-forge.yaml"
        fetch_url(PRESET_URLS["conda-forge"], dest)
        assert dest.exists()
        assert dest.stat().st_size > 0

    def test_fetched_anaconda_cbc_is_valid_yaml(self, tmp_path):
        dest = tmp_path / "anaconda.yaml"
        fetch_url(PRESET_URLS["anaconda"], dest)
        content = yaml.safe_load(dest.read_text())
        assert isinstance(content, dict)

    def test_fetched_conda_forge_cbc_is_valid_yaml(self, tmp_path):
        dest = tmp_path / "conda-forge.yaml"
        fetch_url(PRESET_URLS["conda-forge"], dest)
        content = yaml.safe_load(dest.read_text())
        assert isinstance(content, dict)

    def test_fetched_anaconda_cbc_has_expected_keys(self, tmp_path):
        dest = tmp_path / "anaconda.yaml"
        fetch_url(PRESET_URLS["anaconda"], dest)
        cbc = yaml.safe_load(dest.read_text())
        # These keys are stable pillars of Anaconda's CBC.
        assert "numpy" in cbc
        assert "python" in cbc

    def test_fetched_conda_forge_cbc_has_expected_keys(self, tmp_path):
        dest = tmp_path / "conda-forge.yaml"
        fetch_url(PRESET_URLS["conda-forge"], dest)
        cbc = yaml.safe_load(dest.read_text())
        assert "numpy" in cbc
        assert "python" in cbc

    def test_bad_url_raises_runtime_error(self, tmp_path):
        with pytest.raises(RuntimeError, match="Failed to fetch CBC"):
            fetch_url("https://raw.githubusercontent.com/no/such/repo/does-not-exist.yaml",
                      tmp_path / "out.yaml")


# ── resolve_cbc ────────────────────────────────────────────────────────────────


class TestResolveCbc:
    def test_anaconda_preset_fetches_and_returns_one_file(self, tmp_path):
        files = resolve_cbc("anaconda", "", tmp_path)
        assert len(files) == 1
        assert files[0].exists()

    def test_conda_forge_preset_fetches_and_returns_one_file(self, tmp_path):
        files = resolve_cbc("conda-forge", "", tmp_path)
        assert len(files) == 1
        assert files[0].exists()

    def test_anaconda_preset_file_is_valid_yaml(self, tmp_path):
        files = resolve_cbc("anaconda", "", tmp_path)
        cbc = yaml.safe_load(files[0].read_text())
        assert isinstance(cbc, dict)
        assert "numpy" in cbc

    def test_conda_forge_preset_file_is_valid_yaml(self, tmp_path):
        files = resolve_cbc("conda-forge", "", tmp_path)
        cbc = yaml.safe_load(files[0].read_text())
        assert isinstance(cbc, dict)
        assert "numpy" in cbc

    def test_none_preset_no_custom_returns_empty(self, tmp_path):
        assert resolve_cbc("none", "", tmp_path) == []

    def test_none_preset_with_local_cbc(self, tmp_path):
        cbc = tmp_path / "my.yaml"
        cbc.write_text("numpy:\n  - 1.26\n")
        result = resolve_cbc("none", str(cbc), tmp_path)
        assert result == [cbc]

    def test_anaconda_plus_local_cbc_returns_two_files(self, tmp_path):
        override = tmp_path / "override.yaml"
        override.write_text("numpy:\n  - 1.26\n")
        files = resolve_cbc("anaconda", str(override), tmp_path)
        assert len(files) == 2
        # Preset comes first so custom can override it (R5)
        assert files[1] == override

    def test_preset_file_written_inside_tmp_dir(self, tmp_path):
        files = resolve_cbc("anaconda", "", tmp_path)
        assert str(files[0]).startswith(str(tmp_path))

    def test_local_cbc_path_missing_raises(self, tmp_path):
        with pytest.raises(ValueError, match="CBC file not found"):
            resolve_cbc("none", str(tmp_path / "no-such.yaml"), tmp_path)

    def test_unknown_preset_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Unknown cbc-preset: bad"):
            resolve_cbc("bad", "", tmp_path)

    def test_anaconda_and_conda_forge_pin_numpy_differently(self, tmp_path):
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()

        anaconda_files = resolve_cbc("anaconda", "", tmp_path / "a")
        cf_files = resolve_cbc("conda-forge", "", tmp_path / "b")

        anaconda_numpy = yaml.safe_load(anaconda_files[0].read_text()).get("numpy")
        cf_numpy = yaml.safe_load(cf_files[0].read_text()).get("numpy")

        # Both CBCs pin numpy, but the exact pins differ between the two.
        assert anaconda_numpy is not None
        assert cf_numpy is not None
        # If this fails it means the two presets have converged — worth knowing.
        assert anaconda_numpy != cf_numpy, (
            f"Anaconda and conda-forge numpy pins are identical ({anaconda_numpy}); "
            "this might indicate the CBCs have converged or one failed to load correctly."
        )


# ── resolve_channels ───────────────────────────────────────────────────────────


class TestResolveChannels:
    def test_explicit_single_channel(self):
        assert resolve_channels("my-channel", "anaconda") == ["my-channel"]

    def test_explicit_multiple_channels(self):
        assert resolve_channels("defaults,conda-forge", "anaconda") == [
            "defaults",
            "conda-forge",
        ]

    def test_explicit_overrides_preset(self):
        # C1: user intent wins regardless of preset
        assert resolve_channels("defaults", "conda-forge") == ["defaults"]

    def test_anaconda_preset_implies_defaults(self):
        assert resolve_channels("", "anaconda") == ["defaults"]

    def test_conda_forge_preset_implies_conda_forge(self):
        assert resolve_channels("", "conda-forge") == ["conda-forge"]

    def test_none_preset_implies_defaults(self):
        assert resolve_channels("", "none") == ["defaults"]

    def test_whitespace_stripped(self):
        assert resolve_channels("  main , conda-forge ", "none") == [
            "main",
            "conda-forge",
        ]

    def test_empty_entries_ignored(self):
        assert resolve_channels("defaults,,conda-forge", "none") == [
            "defaults",
            "conda-forge",
        ]


# ── build_command ──────────────────────────────────────────────────────────────


class TestBuildCommand:
    @pytest.fixture()
    def recipe(self, tmp_path) -> Path:
        d = tmp_path / "recipe"
        d.mkdir()
        return d

    def test_starts_with_conda_build(self, recipe):
        cmd = build_command(recipe, ["defaults"], [], "./build", [], False)
        assert cmd[0] == "conda-build"

    def test_override_channels_present(self, recipe):
        cmd = build_command(recipe, ["defaults"], [], "./build", [], False)
        assert "--override-channels" in cmd

    def test_channel_flags(self, recipe):
        cmd = build_command(recipe, ["defaults", "conda-forge"], [], "./build", [], False)
        c_args = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-c"]
        assert c_args == ["defaults", "conda-forge"]

    def test_output_folder_flag(self, recipe):
        cmd = build_command(recipe, ["defaults"], [], "./my-output", [], False)
        idx = cmd.index("--output-folder")
        assert cmd[idx + 1] == "./my-output"

    def test_no_anaconda_upload_present(self, recipe):
        cmd = build_command(recipe, ["defaults"], [], "./build", [], False)
        assert "--no-anaconda-upload" in cmd

    def test_variant_config_files_when_cbc_provided(self, recipe, tmp_path):
        cbc = tmp_path / "cbc.yaml"
        cbc.write_text("numpy:\n  - 1.26\n")
        cmd = build_command(recipe, ["defaults"], [cbc], "./build", [], False)
        assert "--variant-config-files" in cmd
        assert str(cbc) in cmd

    def test_no_variant_config_files_when_no_cbc(self, recipe):
        cmd = build_command(recipe, ["defaults"], [], "./build", [], False)
        assert "--variant-config-files" not in cmd

    def test_multiple_cbc_files_in_order(self, recipe, tmp_path):
        cbc1 = tmp_path / "preset.yaml"
        cbc2 = tmp_path / "custom.yaml"
        cbc1.write_text("a: 1\n")
        cbc2.write_text("b: 2\n")
        cmd = build_command(recipe, ["defaults"], [cbc1, cbc2], "./build", [], False)
        idx = cmd.index("--variant-config-files")
        assert cmd[idx + 1] == str(cbc1)
        assert cmd[idx + 2] == str(cbc2)

    def test_single_python_version(self, recipe):
        cmd = build_command(recipe, ["defaults"], [], "./build", ["3.12"], False)
        py_idx = [i for i, x in enumerate(cmd) if x == "--python"]
        assert len(py_idx) == 1
        assert cmd[py_idx[0] + 1] == "3.12"

    def test_multiple_python_versions(self, recipe):
        cmd = build_command(recipe, ["defaults"], [], "./build", ["3.11", "3.12"], False)
        py_idx = [i for i, x in enumerate(cmd) if x == "--python"]
        assert len(py_idx) == 2
        assert cmd[py_idx[0] + 1] == "3.11"
        assert cmd[py_idx[1] + 1] == "3.12"

    def test_verbose_flag_added(self, recipe):
        cmd = build_command(recipe, ["defaults"], [], "./build", [], True)
        assert "--verbose" in cmd

    def test_verbose_flag_absent_when_false(self, recipe):
        cmd = build_command(recipe, ["defaults"], [], "./build", [], False)
        assert "--verbose" not in cmd

    def test_recipe_is_last_argument(self, recipe):
        cmd = build_command(recipe, ["defaults"], [], "./build", [], False)
        assert cmd[-1] == str(recipe)

    def test_recipe_last_even_with_all_options(self, recipe, tmp_path):
        cbc = tmp_path / "cbc.yaml"
        cbc.write_text("a: 1\n")
        cmd = build_command(recipe, ["defaults"], [cbc], "./build", ["3.12"], True)
        assert cmd[-1] == str(recipe)
