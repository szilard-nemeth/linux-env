from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.disk_cleanup.cleanup_disk import (
    AsdfGolangCleanup,
    parse_asdf_current_golang_version,
    resolve_asdf_golang_keep_versions,
)


@pytest.mark.parametrize(
    "output,expected",
    [
        (
            "golang          1.25.8          /Users/snemeth/development/cloudera/cde/dex/.tool-versions",
            "1.25.8",
        ),
        (
            "golang          1.24.11         /Users/snemeth/.tool-versions",
            "1.24.11",
        ),
        ("", None),
        ("unexpected format", None),
    ],
)
def test_parse_asdf_current_golang_version(output, expected):
    assert parse_asdf_current_golang_version(output) == expected


def test_resolve_asdf_golang_keep_versions_home_and_dex(tmp_path):
    home = Path("/fake/home")
    dex_dir = tmp_path / "dex"
    dex_dir.mkdir()

    def fake_asdf_current(*, cwd=None):
        if cwd == home:
            return "1.24.11"
        if cwd == dex_dir:
            return "1.25.8"
        return None

    with (
        patch("scripts.disk_cleanup.cleanup_disk.Path.home", return_value=home),
        patch("scripts.disk_cleanup.cleanup_disk.DEX_PROJECT_DIR", dex_dir),
        patch("scripts.disk_cleanup.cleanup_disk.asdf_current_golang_version", side_effect=fake_asdf_current),
    ):
        assert resolve_asdf_golang_keep_versions() == ["1.24.11", "1.25.8"]


def test_resolve_asdf_golang_keep_versions_dedupes_same_version(tmp_path):
    home = Path("/fake/home")
    dex_dir = tmp_path / "dex"
    dex_dir.mkdir()
    version = "1.24.11"

    with (
        patch("scripts.disk_cleanup.cleanup_disk.Path.home", return_value=home),
        patch("scripts.disk_cleanup.cleanup_disk.DEX_PROJECT_DIR", dex_dir),
        patch(
            "scripts.disk_cleanup.cleanup_disk.asdf_current_golang_version",
            return_value=version,
        ),
    ):
        assert resolve_asdf_golang_keep_versions() == [version]


def test_resolve_asdf_golang_keep_versions_skips_missing_dex_dir(tmp_path):
    home = Path("/fake/home")
    missing_dex = tmp_path / "no-dex-here"

    with (
        patch("scripts.disk_cleanup.cleanup_disk.Path.home", return_value=home),
        patch("scripts.disk_cleanup.cleanup_disk.DEX_PROJECT_DIR", missing_dex),
        patch(
            "scripts.disk_cleanup.cleanup_disk.asdf_current_golang_version",
            return_value="1.24.11",
        ) as asdf_current,
    ):
        assert resolve_asdf_golang_keep_versions() == ["1.24.11"]
        asdf_current.assert_called_once_with(cwd=home)


def test_asdf_golang_cleanup_prepare_skips_uninstall_when_no_keep_versions(tmp_path, monkeypatch):
    asdf_root = tmp_path / "golang"
    asdf_root.mkdir()
    (asdf_root / "1.23.0").mkdir()

    monkeypatch.setattr("scripts.disk_cleanup.cleanup_disk.ASDF_GOLANG_ROOT", asdf_root)
    monkeypatch.setattr(
        "scripts.disk_cleanup.cleanup_disk.AsdfGolangCleanup.run_command_check_output",
        lambda self, cmd, cwd=None: ("", ""),
    )

    tool = AsdfGolangCleanup(keep_versions=[])
    tool.prepare()

    assert tool.tracker.unnamed_cleanup == []
