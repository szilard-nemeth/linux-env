import click
import pytest

from scripts.disk_cleanup.cleanup_disk import KbPrivateGitOffloadCleanup
from scripts.git.git_move_large_files import FileStats


def test_kb_private_git_offload_has_pending_work_when_estimate_positive():
    tool = KbPrivateGitOffloadCleanup(interactive=False)
    tool._estimated_reclaim_bytes = 1024
    assert tool._has_pending_work()
    assert tool.estimated_reclaim_bytes() == 1024


def test_kb_private_git_offload_skips_when_repo_missing(monkeypatch, caplog):
    import logging

    caplog.set_level(logging.INFO)
    tool = KbPrivateGitOffloadCleanup(interactive=False)
    monkeypatch.setattr(
        "scripts.disk_cleanup.cleanup_disk.Path.is_dir",
        lambda self: False,
    )

    tool.prepare()
    tool.execute_flow()

    assert tool._workflow_failed
    assert not tool._has_pending_work()
    assert "Repository not found" in caplog.text


def test_kb_private_git_offload_execute_flow_uses_workflow_estimate(monkeypatch):
    tool = KbPrivateGitOffloadCleanup(interactive=False)
    monkeypatch.setattr(
        "scripts.disk_cleanup.cleanup_disk.Path.is_dir",
        lambda self: True,
    )
    monkeypatch.setattr(
        "scripts.disk_cleanup.cleanup_disk.FileUtils.get_dir_size",
        lambda _path: 1000,
    )

    dry_stats = FileStats()
    dry_stats.total_space_saved_bytes = 500
    execute_stats = FileStats()
    execute_stats.total_space_saved_bytes = 500

    calls = {"execute": []}

    def fake_run_workflow(execute: bool):
        calls["execute"].append(execute)
        return execute_stats if execute else dry_stats

    monkeypatch.setattr(tool, "_run_workflow", fake_run_workflow)
    tool.execute_flow()

    assert calls["execute"] == [False, True]
    assert tool.reclaimed_bytes() == 500


def test_main_rejects_conflicting_exclusive_flags():
    from scripts.disk_cleanup.cleanup_disk import main

    with pytest.raises(click.UsageError):
        main(["--docker-only", "--kb-private-git-offload"], standalone_mode=False)
