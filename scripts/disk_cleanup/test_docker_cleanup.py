import subprocess

import humanfriendly

from scripts.disk_cleanup.cleanup_disk import (
    CleanupTool,
    DockerCleanup,
    DockerSystemPruneCleanup,
    _DockerPruneMixin,
)


def test_parse_total_reclaimed_sums_multiple_lines():
    output = """
Deleted Images:
untagged: alpine:latest
Total reclaimed space: 16.43 MB
Total reclaimed space: 1.093 MB
"""
    expected = humanfriendly.parse_size("16.43 MB") + humanfriendly.parse_size("1.093 MB")
    assert DockerCleanup._parse_total_reclaimed(output) == expected


def test_parse_total_reclaimed_empty():
    assert DockerCleanup._parse_total_reclaimed("Nothing to prune") == 0


def test_system_prune_command():
    assert DockerSystemPruneCleanup.SYSTEM_PRUNE_CMD == [
        "docker",
        "system",
        "prune",
        "-a",
        "--volumes",
        "-f",
    ]


def test_run_prune_records_success(monkeypatch):
    tool = DockerCleanup()
    tool._reset_command_outcomes()

    def fake_check_output(cmd, **kwargs):
        return "Total reclaimed space: 10MB\n"

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)
    reclaimed = tool._run_prune(["docker", "image", "prune", "--force"])
    assert reclaimed == humanfriendly.parse_size("10MB")
    assert tool._commands_succeeded == 1
    assert tool._commands_failed == 0


def test_docker_cleanup_uses_mixin_estimated_reclaim_bytes():
    tool = DockerCleanup()
    tool._docker_available = True
    tool._estimated_reclaim_bytes = 1024

    assert DockerCleanup.__mro__.index(_DockerPruneMixin) < DockerCleanup.__mro__.index(CleanupTool)
    assert tool.estimated_reclaim_bytes() == 1024


def test_docker_cleanup_estimated_reclaim_unknown_when_daemon_unavailable():
    tool = DockerCleanup()
    tool._docker_available = False
    tool._estimated_reclaim_bytes = 1024

    assert tool.estimated_reclaim_bytes() is None


def test_run_prune_records_failure(monkeypatch):
    tool = DockerCleanup()
    tool._reset_command_outcomes()

    def fake_check_output(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd, output="error")

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)
    assert tool._run_prune(["docker", "image", "prune", "--force"]) == 0
    assert tool._commands_succeeded == 0
    assert tool._commands_failed == 1
    assert tool._prune_failed
