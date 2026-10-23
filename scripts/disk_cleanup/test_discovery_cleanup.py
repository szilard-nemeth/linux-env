import os
import subprocess
import time
from pathlib import Path

from scripts.disk_cleanup.cleanup_disk import (
    CHROME_APP_SUPPORT_CACHE_PATTERNS,
    ELECTRON_APP_SUPPORT_CACHE_PATTERNS,
    DiscoveryCleanup,
    MavenLocalRepoCleanup,
)


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


def test_chrome_app_support_patterns_skip_profile_data(tmp_path):
    for rel in [
        "Default/Cache/Cache_Data/blob",
        "Profile 1/GPUCache/data_0",
        "GrShaderCache/data_1",
        "Crashpad/completed/report.dmp",
        "Default/IndexedDB/https_docs.google.com_0.indexeddb.leveldb/000001.log",
        "Default/Bookmarks",
        "Profile 1/Web Applications/manifest.json",
        "Crashpad/settings.dat",
        "Local State",
    ]:
        _write(tmp_path / rel, 16)
    for p in sorted(tmp_path.rglob("*"), key=lambda path: -len(path.parts)):
        _make_stale(p)

    tool = DiscoveryCleanup(
        "Test", tmp_path, CHROME_APP_SUPPORT_CACHE_PATTERNS, age_days=30, target_type="any", recursive=False
    )
    tool.prepare()

    registered = sorted(d.dir.relative_to(tmp_path).as_posix() for d in tool.tracker.unnamed_cleanup)
    assert registered == [
        "Crashpad/completed/report.dmp",
        "Default/Cache",
        "GrShaderCache",
        "Profile 1/GPUCache",
    ]


def test_electron_app_support_patterns_skip_app_data(tmp_path):
    for rel in ["Cache/Cache_Data/blob", "logs/app.log", "IndexedDB/x.leveldb/000001.log", "orionV3.db", "Cookies"]:
        _write(tmp_path / rel, 16)
    for p in sorted(tmp_path.rglob("*"), key=lambda path: -len(path.parts)):
        _make_stale(p)

    tool = DiscoveryCleanup(
        "Test", tmp_path, ELECTRON_APP_SUPPORT_CACHE_PATTERNS, age_days=30, target_type="any", recursive=False
    )
    tool.prepare()

    registered = sorted(d.dir.relative_to(tmp_path).as_posix() for d in tool.tracker.unnamed_cleanup)
    assert registered == ["Cache", "logs/app.log"]


def _git(repo: Path, *args: str):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _init_repo(repo: Path):
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")


def test_skip_git_unignored_keeps_tracked_and_unignored_dirs(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / ".gitignore").write_text("ignored_build/\n")
    _write(repo / "tracked_dist" / "index.js", 16)  # committed bundle
    _write(repo / "untracked_build" / "notes.txt", 16)  # not ignored, not committed
    _write(repo / "ignored_build" / "out.o", 16)  # real build output
    _git(repo, "add", ".gitignore", "tracked_dist")
    _git(repo, "commit", "-q", "-m", "init")
    _write(tmp_path / "no_repo" / "build" / "out.o", 16)  # outside any git work tree

    tool = DiscoveryCleanup(
        "Test",
        tmp_path,
        ["tracked_dist", "untracked_build", "ignored_build", "build"],
        age_days=-1,
        skip_git_unignored=True,
    )
    tool.prepare()

    registered = sorted(d.dir.relative_to(tmp_path).as_posix() for d in tool.tracker.unnamed_cleanup)
    assert registered == ["no_repo/build", "repo/ignored_build"]


def test_exclude_roots_are_never_registered(tmp_path):
    _write(tmp_path / "kb" / "LOGS" / "build" / "f.log", 16)
    _write(tmp_path / "other" / "build" / "f.log", 16)

    tool = DiscoveryCleanup("Test", tmp_path, ["build"], age_days=-1, exclude_roots=[tmp_path / "kb"])
    tool.prepare()

    assert [d.dir for d in tool.tracker.unnamed_cleanup] == [tmp_path / "other" / "build"]


def test_skip_inside_ignores_matches_in_installed_packages(tmp_path):
    _write(tmp_path / "proj" / "venv" / "lib" / "site-packages" / "pip" / "build" / "f.py", 16)
    _write(tmp_path / "proj" / "node_modules" / "ajv" / "dist" / "f.js", 16)
    _write(tmp_path / "proj" / "build" / "out.o", 16)

    tool = DiscoveryCleanup(
        "Test", tmp_path, ["build", "dist"], age_days=-1, skip_inside=["node_modules", "site-packages"]
    )
    tool.prepare()

    assert [d.dir for d in tool.tracker.unnamed_cleanup] == [tmp_path / "proj" / "build"]


def _maven_version(repo: Path, rel: str, remote_repo_id: str = "central", days_old: int = 90) -> Path:
    version_dir = repo / rel
    artifact, version = version_dir.parent.name, version_dir.name
    _write(version_dir / f"{artifact}-{version}.jar", 1024)
    _write(version_dir / f"{artifact}-{version}.pom", 16)
    (version_dir / "_remote.repositories").write_text(
        f"#NOTE: Maven Resolver internal file\n{artifact}-{version}.jar>{remote_repo_id}=\n"
        f"{artifact}-{version}.pom>{remote_repo_id}=\n"
    )
    _make_stale(version_dir, days_old)
    return version_dir


def test_maven_local_repo_cleanup_keeps_newest_recent_and_local_versions(tmp_path):
    repo = tmp_path / "repository"
    old = _maven_version(repo, "org/apache/foo/foo-core/1.0", days_old=300)
    _maven_version(repo, "org/apache/foo/foo-core/2.0", days_old=200)  # newest: kept even though stale
    _maven_version(repo, "org/apache/foo/foo-core/0.9-local", remote_repo_id="", days_old=400)  # mvn install
    _maven_version(repo, "com/example/bar/1.0", days_old=10)
    _maven_version(repo, "com/example/bar/0.5", days_old=20)  # not stale yet
    _maven_version(repo, "com/example/baz/3.0", days_old=500)  # only version

    tool = MavenLocalRepoCleanup("Test", repo, age_days=60)
    tool.prepare()

    assert [d.dir for d in tool.tracker.unnamed_cleanup] == [old]
