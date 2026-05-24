import click
import pytest

from scripts.disk_cleanup.cleanup_disk import KbPrivateGitOffloadCleanup, ToolRunner
from scripts.git.git_move_large_files import FileStats


def test_kb_private_git_offload_has_pending_work_when_estimate_positive():
    tool = KbPrivateGitOffloadCleanup()
    tool._estimated_reclaim_bytes = 1024
    assert tool._has_pending_work()
    assert tool.estimated_reclaim_bytes() == 1024


def test_kb_private_git_offload_skips_when_repo_missing(monkeypatch, caplog):
    import logging

    caplog.set_level(logging.INFO)
    tool = KbPrivateGitOffloadCleanup()
    monkeypatch.setattr(
        "scripts.disk_cleanup.cleanup_disk.Path.is_dir",
        lambda self: False,
    )

    tool.prepare()

    assert tool._workflow_failed
    assert not tool._has_pending_work()
    assert "Repository not found" in caplog.text


def test_kb_private_git_offload_run_tools_uses_workflow_estimate(monkeypatch):
    tool = KbPrivateGitOffloadCleanup()
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
    monkeypatch.setattr("scripts.disk_cleanup.cleanup_disk.setup_logging", lambda: None)
    monkeypatch.setattr(
        "scripts.disk_cleanup.cleanup_disk.TOOL_OUTPUT_BASEDIR", type("P", (), {"mkdir": lambda *a, **k: None})()
    )
    ToolRunner.run_tools([tool], dry_run=False, confirm=False)

    assert calls["execute"] == [False, True]
    assert tool.reclaimed_bytes() == 500


def test_main_rejects_conflicting_exclusive_flags():
    from scripts.disk_cleanup.cleanup_disk import main

    with pytest.raises(click.UsageError):
        main(["--docker-only", "--kb-private-git-offload"], standalone_mode=False)


def test_resolve_tools_full_default_run():
    from scripts.disk_cleanup.cleanup_disk import (
        AsdfGolangCleanup,
        DEFAULT_OPTIONAL_TOOLS,
        DockerCleanup,
        DockerSystemPruneCleanup,
        MavenCleanup,
        OPTIONAL_TOOL_KB_PRIVATE_OFFLOAD,
        resolve_tools,
    )

    tools = resolve_tools(docker_time_limit="24h")
    types = [type(t) for t in tools]

    assert MavenCleanup in types
    assert AsdfGolangCleanup in types
    assert DockerCleanup in types
    assert DockerSystemPruneCleanup in types
    assert len([t for t in tools if type(t) is DockerCleanup]) == 1
    assert DEFAULT_OPTIONAL_TOOLS == ("docker-cleanup", "docker-system-prune")
    assert OPTIONAL_TOOL_KB_PRIVATE_OFFLOAD not in [t.summary_name for t in tools]


def test_resolve_tools_skip_defaults_requires_include():
    from scripts.disk_cleanup.cleanup_disk import resolve_tools

    with pytest.raises(click.UsageError):
        resolve_tools(docker_time_limit="24h", skip_defaults=True)


def test_resolve_tools_skip_defaults_with_include():
    from scripts.disk_cleanup.cleanup_disk import (
        DockerCleanup,
        KbPrivateGitOffloadCleanup,
        OPTIONAL_TOOL_DOCKER_CLEANUP,
        OPTIONAL_TOOL_KB_PRIVATE_OFFLOAD,
        resolve_tools,
    )

    tools = resolve_tools(
        docker_time_limit="48h",
        skip_defaults=True,
        include_optional=[OPTIONAL_TOOL_DOCKER_CLEANUP, OPTIONAL_TOOL_KB_PRIVATE_OFFLOAD],
    )

    assert len(tools) == 2
    assert isinstance(tools[0], DockerCleanup)
    assert tools[0].time_limit == "48h"
    assert isinstance(tools[1], KbPrivateGitOffloadCleanup)


def test_build_catalog_table_includes_defaults_and_kb_offload():
    from scripts.disk_cleanup.cleanup_disk import OPTIONAL_TOOL_KB_PRIVATE_OFFLOAD, ToolRunner

    entries = ToolRunner.catalog_entries(docker_time_limit="24h")
    labels = [label for label, _slug in entries]
    slugs = [slug for _label, slug in entries]

    assert "Python Venvs" in labels
    assert "Maven cleanup" in labels
    assert "python-venvs" in slugs
    assert "terraform" in slugs
    assert "maven-cleanup" in slugs
    assert "docker-cleanup" in slugs
    assert OPTIONAL_TOOL_KB_PRIVATE_OFFLOAD in slugs
    assert any(label.startswith("KB private") for label in labels)


def test_main_list_tools_prints_catalog(monkeypatch):
    from scripts.disk_cleanup.cleanup_disk import main

    called: list[str] = []

    def fake_print_catalog(*, docker_time_limit: str) -> None:
        called.append(docker_time_limit)

    monkeypatch.setattr(
        "scripts.disk_cleanup.cleanup_disk.ToolRunner.print_tool_catalog",
        fake_print_catalog,
    )

    main(["--list-tools"], standalone_mode=False)

    assert called == ["1440h"]


def test_main_list_tools_rejects_other_flags():
    from scripts.disk_cleanup.cleanup_disk import main

    with pytest.raises(click.UsageError, match="cannot be combined"):
        main(["--list-tools", "--dry-run"], standalone_mode=False)


def test_log_run_tool_selection_logs_excluded_and_resolved(caplog):
    import logging

    from scripts.disk_cleanup.cleanup_disk import MavenCleanup, ToolRunner

    caplog.set_level(logging.INFO)

    tools = [MavenCleanup("100M")]
    ToolRunner.log_run_tool_selection(tools, ["Python Venvs"])

    messages = [r.message for r in caplog.records]
    assert "Excluded tools: Python Venvs" in messages
    assert "Resolved tool: Maven cleanup (slug: maven-cleanup)" in messages


def test_resolve_tools_exclude_python_venvs():
    from scripts.disk_cleanup.cleanup_disk import DiscoveryCleanup, MavenCleanup, resolve_tools

    tools = resolve_tools(docker_time_limit="24h", exclude_tools=["Python Venvs"])
    summary_names = [t.summary_name for t in tools]

    assert "Python Venvs" not in summary_names
    assert any(isinstance(t, MavenCleanup) for t in tools)
    assert any(isinstance(t, DiscoveryCleanup) and t.summary_name == "Terraform" for t in tools)


def test_resolve_tools_exclude_by_slug():
    from scripts.disk_cleanup.cleanup_disk import DockerCleanup, DockerSystemPruneCleanup, resolve_tools

    tools = resolve_tools(docker_time_limit="24h", exclude_tools=["docker-cleanup"])
    types = [type(t) for t in tools]

    assert DockerCleanup not in types
    assert DockerSystemPruneCleanup in types


def test_resolve_tools_exclude_unknown_raises():
    from scripts.disk_cleanup.cleanup_disk import resolve_tools

    with pytest.raises(click.UsageError, match="Unknown --exclude-tool"):
        resolve_tools(docker_time_limit="24h", exclude_tools=["not-a-real-tool"])


def test_resolve_tools_exclude_all_raises():
    from scripts.disk_cleanup.cleanup_disk import OPTIONAL_TOOL_DOCKER_CLEANUP, resolve_tools

    with pytest.raises(click.UsageError, match="All cleanup tools were excluded"):
        resolve_tools(
            docker_time_limit="24h",
            skip_defaults=True,
            include_optional=[OPTIONAL_TOOL_DOCKER_CLEANUP],
            exclude_tools=["docker-cleanup"],
        )


def test_resolve_tools_include_kb_without_docker():
    from scripts.disk_cleanup.cleanup_disk import (
        DockerCleanup,
        DockerSystemPruneCleanup,
        KbPrivateGitOffloadCleanup,
        MavenCleanup,
        OPTIONAL_TOOL_KB_PRIVATE_OFFLOAD,
        resolve_tools,
    )

    tools = resolve_tools(
        docker_time_limit="24h",
        include_optional=[OPTIONAL_TOOL_KB_PRIVATE_OFFLOAD],
    )
    types = [type(t) for t in tools]

    assert MavenCleanup in types
    assert KbPrivateGitOffloadCleanup in types
    assert DockerCleanup not in types
    assert DockerSystemPruneCleanup not in types
