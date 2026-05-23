import argparse
import datetime
import enum
import os
import re
import shutil
from dataclasses import dataclass
from typing import List, Optional

# --- Default configuration ---
GOOGLE_DRIVE_ROOT = os.path.expanduser("~/googledrive/development/KB-private-offloaded")
PATH_PREFIX_TO_STRIP = "cloudera/tasks/cde/"
KB_PRIVATE_ROOT = os.path.expanduser("~/development/my-repos/knowledge-base-private")
ALLOWED_EXTENSIONS = [".tar.gz", ".gz", ".zip", ".gzip"]
# -----------------------------


class FileStats:
    def __init__(self):
        self.files_moved = 0
        self.files_skipped_by_extension = 0
        self.total_space_saved_bytes = 0
        self.total_space_reclaimed_non_matching_extension = 0

    def skip_file(self, file_path, size_in_bytes):
        self.files_skipped_by_extension += 1
        self.total_space_reclaimed_non_matching_extension += size_in_bytes

    def add_saved_space(self, size_in_bytes):
        self.total_space_saved_bytes += size_in_bytes

    def record_file_moved(self, file_path):
        self.files_moved += 1

    def print(self, dry_run: bool):
        print("-" * 60)
        print("Summary:")
        print(f"Files meeting size and extension criteria: {self.files_moved}")
        if self.files_skipped_by_extension > 0:
            print(f"Files skipped due to extension filter: {self.files_skipped_by_extension}")

        total_space_saved_human = GitLargeFileMover.convert_bytes_to_human_readable(self.total_space_saved_bytes)
        non_matching_human = GitLargeFileMover.convert_bytes_to_human_readable(
            self.total_space_reclaimed_non_matching_extension
        )
        if dry_run:
            print(f"Would save estimated space: {total_space_saved_human}")
            print(f"Would save estimated space for non-matching extensions: {non_matching_human}")
            print("\nNote: Re-run with --execute to perform the actual move.")
        else:
            print(f"Estimated Space Saved: {total_space_saved_human}")
            print(f"Space for non-matching extensions (not moved): {non_matching_human}")


class CandidateValidationCode(enum.Enum):
    FILE_PATTERN_DOES_NOT_MATCH = 0
    FILE_SIZE_BELOW_THRESHOLD = 1
    FILE_EXTENSION_NOT_ALLOWED = 2
    FILE_DOES_NOT_EXIST = 3
    VALID = 4


class FileMoveCandidate:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.size_in_bytes = -1
        self.human_size = -1
        self.paths = FileMoveCandidatePaths()


class FileMoveCandidatePaths:
    def __init__(self):
        self.source_path_abs: str = None
        self.repository_relative_filepath: str = None
        self.new_relative_path: str = None
        self.target_path_abs: str = None
        self.target_dir_abs: str = None
        self.placeholder_path: str = None


@dataclass
class FilePathValidationResult:
    code: CandidateValidationCode
    candidate: FileMoveCandidate


class FilePathValidator:
    def __init__(self, repo_root: str, allowed_extensions: List[str], threshold_bytes: int):
        self.repo_root = repo_root
        self.allowed_extensions = allowed_extensions
        self.threshold_bytes = threshold_bytes

    def is_ext_allowed(self, candidate, stats):
        is_allowed = False
        for ext in self.allowed_extensions:
            if candidate.paths.repository_relative_filepath.lower().endswith(ext):
                is_allowed = True
                break

        if not is_allowed:
            stats.skip_file(candidate.paths.file_path, candidate.size_in_bytes)
            return False
        return True

    def validate_candidate(self, file_path: str, stats: FileStats) -> FilePathValidationResult:
        # Use regex to robustly extract SIZE and FILENAME
        # Example format: #1: 1013MB -> cloudera/tasks/...
        c = FileMoveCandidate(file_path)
        match = re.search(r":\s*(\d+(\.\d+)?\s*[KMGTPE]?B?)\s*->\s*(.*)", c.file_path)

        if not match:
            return FilePathValidationResult(CandidateValidationCode.FILE_PATTERN_DOES_NOT_MATCH, c)

        # Set human size, repository_relative_filepath and size_in_bytes as early as possible
        c.human_size = match.group(1).strip()
        c.paths.repository_relative_filepath = match.group(3).strip()
        c.size_in_bytes = GitLargeFileMover.parse_human_size(c.human_size)

        if c.size_in_bytes is None or c.size_in_bytes < self.threshold_bytes:
            # Since the input is sorted, we can usually stop early, but checking all lines is safer.
            return FilePathValidationResult(CandidateValidationCode.FILE_SIZE_BELOW_THRESHOLD, c)

        if not self.is_ext_allowed(c, stats):
            return FilePathValidationResult(CandidateValidationCode.FILE_EXTENSION_NOT_ALLOWED, c)

        c.paths.source_path_abs = os.path.join(self.repo_root, c.paths.repository_relative_filepath)
        if not os.path.isfile(c.paths.source_path_abs):
            return FilePathValidationResult(CandidateValidationCode.FILE_DOES_NOT_EXIST, c)

        return FilePathValidationResult(CandidateValidationCode.VALID, c)


class GitLargeFileMover:
    def __init__(
        self,
        input_filepath: str,
        threshold_bytes: int,
        dry_run: bool = True,
        google_drive_root: str = GOOGLE_DRIVE_ROOT,
        path_prefix_to_strip: str = PATH_PREFIX_TO_STRIP,
        repo_root: str = KB_PRIVATE_ROOT,
        allowed_extensions: Optional[List[str]] = None,
    ):
        self.input_filepath = input_filepath
        self.threshold_bytes = threshold_bytes
        self.dry_run = dry_run
        self.google_drive_root = google_drive_root
        self.path_prefix_to_strip = path_prefix_to_strip
        self.repo_root = repo_root
        self.allowed_extensions = allowed_extensions

    @staticmethod
    def convert_bytes_to_human_readable(bytes: int):
        return f"{bytes / 1024 ** 3:.2f} GB" if bytes > 1024**3 else f"{bytes / 1024 ** 2:.2f} MB"

    @staticmethod
    def parse_human_size(size_str: str) -> Optional[int]:
        """
        Converts a human-readable size string (e.g., '1.7G', '5.1K', '128B') to bytes.
        This function is copied from the analyzer for self-sufficiency.
        """
        size_str = size_str.strip().upper()
        if not size_str:
            return None

        match = re.match(r"(\d+(\.\d+)?)\s*([KMGTPE])?B?", size_str)
        if not match:
            if size_str.isdigit():
                return int(size_str)
            return None

        value = float(match.group(1))
        unit = match.group(3)

        units_map = {
            None: 1,  # Bytes
            "K": 1024,  # Kibibytes
            "M": 1024**2,  # Mebibytes
            "G": 1024**3,  # Gibibytes
            "T": 1024**4,  # Tebibytes
            "P": 1024**5,  # Pebibytes
        }

        multiplier = units_map.get(unit, 1)
        return int(value * multiplier)

    def set_file_paths_for_candidate(self, c: FileMoveCandidate):
        rel_path = c.paths.repository_relative_filepath

        # Strip the configured prefix from the relative path
        if rel_path.startswith(self.google_drive_root, self.path_prefix_to_strip):
            c.paths.new_relative_path = rel_path[len(self.google_drive_root, self.path_prefix_to_strip) :]
        else:
            c.paths.new_relative_path = rel_path

        # Combine the clean relative path with the Google Drive root
        c.paths.target_path_abs = os.path.join(self.google_drive_root, c.paths.new_relative_path)
        c.paths.target_dir_abs = os.path.dirname(c.paths.target_path_abs)
        c.paths.placeholder_path = c.paths.source_path_abs + ".MOVED.txt"

    def process_and_move(  # noqa: C901
        self,
    ):
        """
        Reads the file list, identifies files larger than the threshold, and moves them
        to the Google Drive root, preserving the relative path after stripping the prefix.
        It also creates a placeholder file in the original location upon a successful move.

        Args:
            input_filepath: Path to the file containing the size analysis output.
            threshold_bytes: The minimum file size in bytes required for a move.
        """
        if self.allowed_extensions is None:
            self.allowed_extensions = ALLOWED_EXTENSIONS

        if self.dry_run:
            print("!!! DRY RUN MODE ACTIVE !!!")
            print("No files will be moved. Commands are printed below.")
        else:
            print("!!! REAL MOVE MODE ACTIVE !!!")
            print(f"Files > {self.threshold_bytes // 1024 // 1024}MB will be MOVED to {self.google_drive_root}")

        print("-" * 60)
        print(f"NOTE: Stripping prefix '{self.path_prefix_to_strip}' from source paths.")
        print(f"NOTE: Only processing files with extensions: {', '.join(self.allowed_extensions)}")

        try:
            with open(self.input_filepath, "r") as f:
                raw_data = f.read()
        except Exception as e:
            print(f"Error reading input file: {e}")
            return

        lines = raw_data.strip().split("\n")
        stats = FileStats()

        current_candidate_no = 1
        for line in lines:
            # Skip header/footer lines and lines that don't look like file entries
            if not line.startswith("#"):
                continue

            # from now on, line is file_path
            file_path = line

            validator = FilePathValidator(self.repo_root, self.allowed_extensions, self.threshold_bytes)
            result = validator.validate_candidate(file_path, stats)
            if result.code in (
                CandidateValidationCode.FILE_SIZE_BELOW_THRESHOLD,
                CandidateValidationCode.FILE_PATTERN_DOES_NOT_MATCH,
                CandidateValidationCode.FILE_EXTENSION_NOT_ALLOWED,
                CandidateValidationCode.FILE_DOES_NOT_EXIST,
            ):
                if result.code == CandidateValidationCode.FILE_DOES_NOT_EXIST:
                    print(f"ERROR: File does not exist at source: {result.candidate.paths.source_path_abs}")
                continue

            c: FileMoveCandidate = result.candidate

            # Determine destination paths and print candidate
            self.set_file_paths_for_candidate(c)
            print(f"\n[MOVE Candidate #{current_candidate_no}: {c.human_size}]")
            print(f"  SOURCE: {c.paths.source_path_abs}")
            print(f"  TARGET: {c.paths.target_path_abs}")

            # Execute/Simulate directory creation
            if not self._make_dir_for_candidate(c):
                continue

            stats.add_saved_space(c.size_in_bytes)

            # Execute/Simulate file move
            self._perform_file_move(c, stats)
            current_candidate_no += 1
        stats.print(self.dry_run)

    def _make_dir_for_candidate(self, c: FileMoveCandidate):
        if not self.dry_run:
            try:
                os.makedirs(c.paths.target_dir_abs, exist_ok=True)
                print(f"  Created directory: {c.paths.target_dir_abs}")
            except Exception as e:
                print(f"  ERROR creating directory: {e}")
                return False
            return True
        else:
            print(f"  Dry Run: mkdir -p {c.paths.target_dir_abs}")
            return True

    def _perform_file_move(self, c: FileMoveCandidate, stats: FileStats):
        if not self.dry_run:
            try:
                shutil.move(c.paths.source_path_abs, c.paths.target_path_abs)
                print("  SUCCESS: Moved file.")

                placeholder_content = (
                    "--- FILE MOVED ---\n"
                    f"Original file was moved by large_file_mover.py script on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n"
                    f"New location: {c.paths.target_path_abs}\n"
                    "--------------------\n"
                )

                with open(c.paths.placeholder_path, "w") as ph_file:
                    ph_file.write(placeholder_content)

                print(f"  SUCCESS: Created placeholder at {os.path.basename(c.paths.placeholder_path)}")
                stats.record_file_moved(c.file_path)
            except FileNotFoundError:
                print(f"  ERROR: Source file not found at {c.paths.source_path_abs}. Skipping.")
            except Exception as e:
                print(f"  ERROR moving file: {e}")
        else:
            print(f"  Dry Run: mv {c.paths.source_path_abs} {c.paths.target_path_abs}")
            print(f"  Dry Run: Creating placeholder file: {c.paths.placeholder_path}")
            stats.record_file_moved(c.file_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Move large repository files to offloaded storage and leave placeholders.",
    )
    parser.add_argument(
        "input_filepath",
        help="Path to sorted analyzer output (full list, not top-N stdout only)",
    )
    parser.add_argument("threshold_mb", type=int, help="Minimum file size in MB to move")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually move files (default: dry run)",
    )
    parser.add_argument(
        "--repo",
        default=KB_PRIVATE_ROOT,
        help=f"Local repository root (default: {KB_PRIVATE_ROOT})",
    )
    parser.add_argument(
        "--drive-root",
        default=GOOGLE_DRIVE_ROOT,
        help=f"Offload destination root (default: {GOOGLE_DRIVE_ROOT})",
    )
    parser.add_argument(
        "--path-prefix-to-strip",
        default=PATH_PREFIX_TO_STRIP,
        help=f"Repository path prefix stripped before offload (default: {PATH_PREFIX_TO_STRIP})",
    )
    args = parser.parse_args()

    large_file_mover = GitLargeFileMover(
        args.input_filepath,
        args.threshold_mb * 1024 * 1024,
        dry_run=not args.execute,
        google_drive_root=os.path.expanduser(args.drive_root),
        path_prefix_to_strip=args.path_prefix_to_strip,
        repo_root=os.path.expanduser(args.repo),
    )
    large_file_mover.process_and_move()
