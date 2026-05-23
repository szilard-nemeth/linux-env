from pathlib import Path

from scripts.disk_cleanup.cleanup_disk import (
    AggregateCleanupDetails,
    CleanupDetails,
    CleanupDetailsTracker,
    CleanupResult,
)


def test_cleanup_details_reclaimed_bytes():
    detail = CleanupDetails(Path("/tmp/x"), before_size=1000, after_size=400)
    assert detail.reclaimed_bytes == 600

    assert CleanupDetails(Path("/tmp/y"), before_size=500, after_size=None).reclaimed_bytes == 0


def test_aggregate_cleanup_details_reclaimed_bytes():
    components = [
        CleanupDetails(Path("/a"), before_size=100, after_size=10),
        CleanupDetails(Path("/b"), before_size=200, after_size=50),
    ]
    aggregate = AggregateCleanupDetails(keys=["a", "b"], components=components)
    assert aggregate.reclaimed_bytes == 240


def test_tracker_build_cleanup_result_unnamed_uses_after_sizes():
    tracker = CleanupDetailsTracker()
    tracker.register_unnamed_dir(Path("/tmp/removed"))
    tracker.unnamed_cleanup[0].before_size = 1000
    tracker.unnamed_cleanup[0].after_size = 0

    result = tracker.build_cleanup_result_unnamed()
    assert result.bytes_reclaimed == 1000
    assert result.success is True
    assert isinstance(result, CleanupResult)
