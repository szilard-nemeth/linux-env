from scripts.disk_cleanup.cleanup_disk import CleanupResult, CleanupTool


class _StubCleanup(CleanupTool):
    def __init__(self, interactive: bool = False, pending: bool = True):
        super().__init__(interactive=interactive)
        self.pending = pending
        self.prepare_called = False
        self.execute_called = False

    def _has_pending_work(self) -> bool:
        return self.pending

    def prepare(self):
        self.prepare_called = True

    def execute(self):
        self.execute_called = True

    def verify(self) -> CleanupResult:
        return CleanupResult(0, True, [])

    def print_summary(self):
        pass


def test_confirm_execution_accepts_yes_variants():
    import builtins

    for answer in ("y", "Y", "yes", "YES", " Yes "):
        tool = _StubCleanup()

        def fake_input(_prompt):
            return answer

        original = builtins.input
        builtins.input = fake_input
        try:
            assert tool._confirm_execution("Proceed? (y/n): ")
        finally:
            builtins.input = original


def test_confirm_execution_rejects_no_and_eof():
    import builtins

    for answer in ("n", "no", ""):
        tool = _StubCleanup()

        def fake_input(_prompt):
            return answer

        original = builtins.input
        builtins.input = fake_input
        try:
            assert not tool._confirm_execution("Proceed? (y/n): ")
        finally:
            builtins.input = original

    tool = _StubCleanup()

    def eof_input(_prompt):
        raise EOFError

    original = builtins.input
    builtins.input = eof_input
    try:
        assert not tool._confirm_execution("Proceed? (y/n): ")
    finally:
        builtins.input = original


def test_execute_flow_skips_execute_when_interactive_declined(monkeypatch):
    tool = _StubCleanup(interactive=True, pending=True)
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    tool.execute_flow()
    assert tool.prepare_called
    assert not tool.execute_called
    assert tool._execute_skipped


def test_execute_flow_runs_execute_when_interactive_confirmed(monkeypatch):
    tool = _StubCleanup(interactive=True, pending=True)
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")
    tool.execute_flow()
    assert tool.execute_called
    assert not tool._execute_skipped


def test_execute_flow_no_prompt_when_not_interactive():
    tool = _StubCleanup(interactive=False, pending=True)
    tool.execute_flow()
    assert tool.execute_called
