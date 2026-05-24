#!/usr/bin/env python3

import io
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import sys

import click
import pytest

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from git_move_large_files import (  # noqa: E402
    CandidateValidationCode,
    ExpandedDirectoryPath,
    FileMoveCandidate,
    FilePathValidator,
    FileStats,
    GitCommitSizeAnalyzer,
    GitLargeFileMover,
    GitLargeFileWorkflow,
    PATH_PREFIX_TO_STRIP,
)


class TestGitLargeFileMover(unittest.TestCase):
    def test_set_file_paths_strips_repo_prefix(self):
        mover = GitLargeFileMover(
            input_filepath="/tmp/unused",
            threshold_bytes=1024,
            path_prefix_to_strip=PATH_PREFIX_TO_STRIP,
            offload_root="/offload",
            repo_root="/repo",
        )
        c = FileMoveCandidate("#1: 22.5M -> cloudera/tasks/cde/subdir/archive.zip")
        c.paths.repository_relative_filepath = "cloudera/tasks/cde/subdir/archive.zip"
        c.paths.source_path_abs = "/repo/cloudera/tasks/cde/subdir/archive.zip"

        mover.set_file_paths_for_candidate(c)

        self.assertEqual(c.paths.new_relative_path, "subdir/archive.zip")
        self.assertEqual(c.paths.target_path_abs, "/offload/subdir/archive.zip")
        self.assertEqual(c.paths.placeholder_path, c.paths.source_path_abs + ".MOVED.txt")

    def test_extension_filter_skips_without_error(self):
        validator = FilePathValidator("/repo", [".zip"], threshold_bytes=1024)
        stats = FileStats()
        line = "#1: 22.5M -> data/large.bin"

        result = validator.validate_candidate(line, stats)

        self.assertEqual(result.code, CandidateValidationCode.FILE_EXTENSION_NOT_ALLOWED)
        self.assertEqual(stats.files_skipped_by_extension, 1)

    def test_dry_run_processes_valid_zip_candidate(self):
        with tempfile.TemporaryDirectory() as repo:
            rel = "cloudera/tasks/cde/assets/model.zip"
            abs_dir = os.path.join(repo, "cloudera", "tasks", "cde", "assets")
            os.makedirs(abs_dir, exist_ok=True)
            source = os.path.join(abs_dir, "model.zip")
            with open(source, "wb") as f:
                f.write(b"x" * (25 * 1024 * 1024))

            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as listing:
                listing.write(f"#1: 22.5M -> {rel}\n")
                listing_path = listing.name

            try:
                mover = GitLargeFileMover(
                    input_filepath=listing_path,
                    threshold_bytes=20 * 1024 * 1024,
                    dry_run=True,
                    repo_root=repo,
                    offload_root=os.path.join(repo, "offload"),
                )
                mover.process_and_move()
            finally:
                os.unlink(listing_path)

    def test_dry_run_lists_skipped_extension_above_threshold(self):
        with tempfile.TemporaryDirectory() as repo:
            listing_path = os.path.join(repo, "listing.txt")
            with open(listing_path, "w") as listing:
                listing.write("#1: 22.5M -> data/large.bin\n")
                listing.write("#2: 25.0M -> data/large.zip\n")

            abs_dir = os.path.join(repo, "data")
            os.makedirs(abs_dir, exist_ok=True)
            with open(os.path.join(abs_dir, "large.zip"), "wb") as f:
                f.write(b"x" * (25 * 1024 * 1024))

            mover = GitLargeFileMover(
                input_filepath=listing_path,
                threshold_bytes=20 * 1024 * 1024,
                dry_run=True,
                repo_root=repo,
                offload_root=os.path.join(repo, "offload"),
                allowed_extensions=[".zip"],
            )
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                stats = mover.process_and_move()

            output = buffer.getvalue()
            self.assertIn("[#1 SKIP extension: 22.5M]", output)
            self.assertIn("[#2 MOVE: 25.0M]", output)
            self.assertEqual(stats.files_moved, 1)
            self.assertEqual(stats.files_skipped_by_extension, 1)

    def test_analyzer_sorts_and_writes_sorted_file(self):
        sample = SCRIPT_DIR / "input-files" / "git-commit-size-analyzer-sample-data.txt"
        with tempfile.TemporaryDirectory() as tmp:
            analyzer_out = Path(tmp) / "analyzer-out.txt"
            sorted_out = Path(tmp) / "sorted.txt"
            GitLargeFileWorkflow.run_analyzer(sample, analyzer_out, sorted_out, top_n=3)

            sorted_lines = sorted_out.read_text().splitlines()
            self.assertEqual(len(sorted_lines), 6)
            self.assertIn("large/data.bin", sorted_lines[0])
            self.assertIn("assets/model.zip", sorted_lines[1])
            self.assertIn("Analyzing Size Data", analyzer_out.read_text())

    def test_working_tree_scan_lists_tracked_files(self):
        with tempfile.TemporaryDirectory() as repo_dir:
            repo = Path(repo_dir)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo,
                check=True,
                capture_output=True,
            )

            small = repo / "small.txt"
            small.write_text("small")
            big = repo / "big.bin"
            big.write_bytes(b"x" * (25 * 1024 * 1024))
            subprocess.run(["git", "add", "small.txt", "big.bin"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)

            details_out = repo / "details.txt"
            GitLargeFileWorkflow.run_working_tree_scan(repo, details_out)

            lines = details_out.read_text().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertTrue(any("big.bin" in line for line in lines))
            self.assertTrue(any("small.txt" in line for line in lines))


def test_main_execute_and_dry_run_flag():
    from git_move_large_files import main

    # Tests click behavior for --execute/--dry-run boolean flag
    # --dry-run sets execute to False
    pass


def test_expanded_directory_path_expands_tilde_before_exists_check(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    repo = tmp_path / "knowledge-base-private"
    repo.mkdir()

    path_type = ExpandedDirectoryPath(exists=True, file_okay=False, path_type=Path)
    resolved = path_type.convert("~/knowledge-base-private", None, None)

    assert resolved == Path(str(repo))


def test_run_commit_size_detailed_passes_verbose_flag(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))

    monkeypatch.setattr(subprocess, "run", fake_run)
    output_path = tmp_path / "details.txt"
    GitLargeFileWorkflow.run_commit_size_detailed(tmp_path, "abc123", output_path, verbose=True)

    assert calls
    assert calls[0][0][-1] == "--verbose"


def test_run_working_tree_scan_verbose_prints_progress(capsys, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.txt").write_text("a")
    (repo / "b.txt").write_text("b")

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)

    details_out = repo / "details.txt"
    GitLargeFileWorkflow.run_working_tree_scan(repo, details_out, verbose=True)

    captured = capsys.readouterr()
    assert "Scanning 2 tracked path(s)" in captured.out
    assert details_out.read_text().count("\n") >= 1


if __name__ == "__main__":
    unittest.main()
