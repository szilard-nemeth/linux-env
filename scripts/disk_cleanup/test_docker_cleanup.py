import humanfriendly

from scripts.disk_cleanup.cleanup_disk import DockerCleanup, DockerSystemPruneCleanup


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
