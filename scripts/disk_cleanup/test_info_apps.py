from click.testing import CliRunner
from rich.console import Console

import scripts.disk_cleanup.cleanup_disk as cleanup_disk

from scripts.disk_cleanup.cleanup_disk import main, print_app_dirs_info, scan_dir_usage


def _write(path, size: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


def test_scan_dir_usage_missing_dir_returns_none(tmp_path):
    assert scan_dir_usage(tmp_path / "nope", top_n=5) is None


def test_scan_dir_usage_total_and_top_children(tmp_path):
    _write(tmp_path / "big" / "nested" / "f.bin", 400 * 1024)
    _write(tmp_path / "medium" / "f.bin", 200 * 1024)
    _write(tmp_path / "small" / "f.bin", 50 * 1024)
    _write(tmp_path / ".hidden" / "f.bin", 100 * 1024)

    usage = scan_dir_usage(tmp_path, top_n=3)

    assert [c.path.name for c in usage.top_children] == ["big", "medium", ".hidden"]
    assert usage.top_children[0].size_bytes >= 400 * 1024
    # Total includes every child, also the ones cut off by top_n
    assert usage.size_bytes >= sum(c.size_bytes for c in usage.top_children) + 50 * 1024
    # Nested dirs are not listed as separate children
    assert all(c.path.parent == tmp_path for c in usage.top_children)


def test_print_app_dirs_info_skips_missing_and_sorts(tmp_path, capsys, monkeypatch):
    # Wide console so long tmp paths are not wrapped
    monkeypatch.setattr(cleanup_disk, "console", Console(width=500))
    _write(tmp_path / "small_app" / "data" / "f.bin", 10 * 1024)
    _write(tmp_path / "big_app" / "Profile 1" / "f.bin", 500 * 1024)

    print_app_dirs_info(dirs=[tmp_path / "small_app", tmp_path / "missing_app", tmp_path / "big_app"], top_n=5)

    out = capsys.readouterr().out
    assert "missing_app" not in out
    assert out.index("big_app") < out.index("small_app")
    assert "Profile 1" in out
    assert "TOTAL" in out


def test_info_apps_rejects_other_options():
    result = CliRunner().invoke(main, ["--info-apps", "--dry-run"])
    assert result.exit_code != 0
    assert "--info-apps cannot be combined" in result.output
