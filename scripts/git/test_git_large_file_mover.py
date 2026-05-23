#!/usr/bin/env python3

import os
import tempfile
import unittest
from pathlib import Path

# Import from script path (scripts/git is not a package)
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from git_large_file_mover import (  # noqa: E402
    CandidateValidationCode,
    FileMoveCandidate,
    FilePathValidator,
    FileStats,
    GitLargeFileMover,
    PATH_PREFIX_TO_STRIP,
)


class TestGitLargeFileMover(unittest.TestCase):
    def test_set_file_paths_strips_repo_prefix(self):
        mover = GitLargeFileMover(
            input_filepath="/tmp/unused",
            threshold_bytes=1024,
            path_prefix_to_strip=PATH_PREFIX_TO_STRIP,
            google_drive_root="/offload",
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
                    google_drive_root=os.path.join(repo, "offload"),
                )
                mover.process_and_move()
            finally:
                os.unlink(listing_path)


if __name__ == "__main__":
    unittest.main()
