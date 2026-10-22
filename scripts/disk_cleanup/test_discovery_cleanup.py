import os
import time
from pathlib import Path

from scripts.disk_cleanup.cleanup_disk import DiscoveryCleanup


def _make_stale(path: Path, days: int = 90):
    stale = time.time() - days * 24 * 60 * 60
    os.utime(path, (stale, stale))


def _write(path: Path, size: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


def test_drop_nested_keeps_only_outermost_paths():
    paths = [Path("/r/a/b/c"), Path("/r/a"), Path("/r/a/b"), Path("/r/d"), Path("/r/ab")]
    assert DiscoveryCleanup._drop_nested(paths) == [Path("/r/a"), Path("/r/d"), Path("/r/ab")]


def test_prepare_does_not_register_descendants_of_stale_match(tmp_path):
    _write(tmp_path / "outer" / "inner" / "deep" / "f.bin", 4096)
    for d in ["outer/inner/deep", "outer/inner", "outer"]:
        _make_stale(tmp_path / d)

    tool = DiscoveryCleanup("Test", tmp_path, ["*"], age_days=30)
    tool.prepare()

    registered = [d.dir for d in tool.tracker.unnamed_cleanup]
    assert registered == [tmp_path / "outer"]


def test_prepare_registers_stale_child_of_active_parent(tmp_path):
    _write(tmp_path / "active" / "stale" / "f.bin", 4096)
    _make_stale(tmp_path / "active" / "stale")

    tool = DiscoveryCleanup("Test", tmp_path, ["*"], age_days=30)
    tool.prepare()

    registered = [d.dir for d in tool.tracker.unnamed_cleanup]
    assert registered == [tmp_path / "active" / "stale"]


def test_prepare_dedupes_across_patterns(tmp_path):
    _write(tmp_path / "dist" / "build" / "f.bin", 4096)

    tool = DiscoveryCleanup("Test", tmp_path, ["build", "dist"], age_days=-1)
    tool.prepare()

    registered = [d.dir for d in tool.tracker.unnamed_cleanup]
    assert registered == [tmp_path / "dist"]
