import logging

from scripts.disk_cleanup.cleanup_disk import (
    CleanupResult,
    CleanupTool,
    ToolRunner,
    _DockerPruneMixin,
    confirm_cleanup,
)


class _StubCleanup(CleanupTool):
    def __init__(self, pending: bool = True):
        super().__init__()
        self.pending = pending
        self.prepare_called = False
        self.execute_called = False
        self.verify_called = False

    def _has_pending_work(self) -> bool:
        return self.pending

    def prepare(self):
        self.prepare_called = True

    def execute(self):
        self.execute_called = True

    def verify(self) -> CleanupResult:
        self.verify_called = True
        return CleanupResult.from_bytes(0)

    def print_summary(self):
        pass


def _run_tools(tools, monkeypatch, *, dry_run=False, confirm=True):
    monkeypatch.setattr("scripts.disk_cleanup.cleanup_disk.setup_logging", lambda: None)
    monkeypatch.setattr(
        "scripts.disk_cleanup.cleanup_disk.TOOL_OUTPUT_BASEDIR",
        type("P", (), {"mkdir": lambda *a, **k: None})(),
    )
    ToolRunner.run_tools(tools, dry_run=dry_run, confirm=confirm)


def test_confirm_cleanup_accepts_yes_variants():
    import builtins

    for answer in ("y", "Y", "yes", "YES", " Yes "):
        original = builtins.input
        builtins.input = lambda _prompt: answer
        try:
            assert confirm_cleanup("Proceed? (y/n): ")
        finally:
            builtins.input = original


def test_confirm_cleanup_rejects_no_and_eof():
    import builtins

    for answer in ("n", "no", ""):
        original = builtins.input
        builtins.input = lambda _prompt: answer
        try:
            assert not confirm_cleanup("Proceed? (y/n): ")
        finally:
            builtins.input = original

    def eof_input(_prompt):
        raise EOFError

    original = builtins.input
    builtins.input = eof_input
    try:
        assert not confirm_cleanup("Proceed? (y/n): ")
    finally:
        builtins.input = original


def test_run_tools_skips_execute_when_declined(monkeypatch):
    tool = _StubCleanup(pending=True)
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    _run_tools([tool], monkeypatch, confirm=True)
    assert tool.prepare_called
    assert not tool.execute_called
    assert not tool.verify_called


def test_run_tools_runs_execute_when_confirmed(monkeypatch):
    tool = _StubCleanup(pending=True)
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")
    _run_tools([tool], monkeypatch, confirm=True)
    assert tool.execute_called
    assert tool.verify_called


def test_run_tools_no_prompt_when_force_mode(monkeypatch):
    tool = _StubCleanup(pending=True)

    def fail_if_called(_prompt):
        raise AssertionError("input should not be called when confirm=False")

    monkeypatch.setattr("builtins.input", fail_if_called)
    _run_tools([tool], monkeypatch, confirm=False)
    assert tool.execute_called


def test_run_tools_dry_run_prepares_only(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    tool = _StubCleanup(pending=True)

    def fail_if_called(_prompt):
        raise AssertionError("input should not be called in dry-run mode")

    monkeypatch.setattr("builtins.input", fail_if_called)
    _run_tools([tool], monkeypatch, dry_run=True)
    assert tool.prepare_called
    assert not tool.execute_called
    assert not tool.verify_called
    assert "DRY RUN MODE" in caplog.text
    assert "Dry run complete" in caplog.text


class _StubWithEstimate(_StubCleanup):
    def estimated_reclaim_bytes(self):
        return 1024 * 1024


def test_run_tools_prints_plan_table(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    tool = _StubWithEstimate(pending=True)
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    _run_tools([tool], monkeypatch, confirm=True)
    assert "Cleanup plan" in caplog.text
    assert "TOTAL" in caplog.text


def test_run_tools_logs_command_outcomes(monkeypatch, caplog):
    class _StubCommands(_StubCleanup):
        def execute(self):
            self._record_command_outcome(0)
            self._record_command_outcome(1)

    caplog.set_level(logging.INFO)
    tool = _StubCommands(pending=True)
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")
    _run_tools([tool], monkeypatch, confirm=True)
    assert any("commands finished: 1 succeeded, 1 failed" in r.message for r in caplog.records)


def test_parse_system_df_reclaimable():
    output = """
TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Images          10        5         1.2GB     800MB
Containers      2         1         100MB     50MB
"""
    assert _DockerPruneMixin._parse_system_df_reclaimable(output) > 0
