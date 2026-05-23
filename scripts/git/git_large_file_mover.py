import argparse
import datetime
import os
import re
import shutil
import sys
from typing import List, Optional

# --- Default configuration ---
GOOGLE_DRIVE_ROOT = os.path.expanduser("~/googledrive/development/KB-private-offloaded")
PATH_PREFIX_TO_STRIP = "cloudera/tasks/cde/"
KB_PRIVATE_ROOT = os.path.expanduser("~/development/my-repos/knowledge-base-private")
ALLOWED_EXTENSIONS = [".tar.gz", ".gz", ".zip", ".gzip"]
# -----------------------------


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
            allowed_extensions = ALLOWED_EXTENSIONS

        if self.dry_run:
            print("!!! DRY RUN MODE ACTIVE !!!")
            print("No files will be moved. Commands are printed below.")
        else:
            print("!!! REAL MOVE MODE ACTIVE !!!")
            print(f"Files > {self.threshold_bytes // 1024 // 1024}MB will be MOVED to {self.google_drive_root}")

        print("-" * 60)
        print(f"NOTE: Stripping prefix '{self.path_prefix_to_strip}' from source paths.")
        print(f"NOTE: Only processing files with extensions: {', '.join(allowed_extensions)}")

        try:
            with open(self.input_filepath, "r") as f:
                raw_data = f.read()
        except Exception as e:
            print(f"Error reading input file: {e}")
            return

        lines = raw_data.strip().split("\n")
        files_moved = 0
        files_skipped_by_extension = 0
        total_space_saved_bytes = 0
        total_space_reclaimed_non_matching_extension = 0

        current_candidate_no = 1
        for line in lines:
            # Skip header/footer lines and lines that don't look like file entries
            if not line.startswith("#"):
                continue

            # Use regex to robustly extract SIZE and FILENAME
            # Example format: #1: 1013MB -> cloudera/tasks/...
            match = re.search(r":\s*(\d+(\.\d+)?\s*[KMGTPE]?B?)\s*->\s*(.*)", line)

            if not match:
                continue

            human_size = match.group(1).strip()
            repository_relative_filepath = match.group(3).strip()

            size_in_bytes = GitLargeFileMover.parse_human_size(human_size)

            if size_in_bytes is None or size_in_bytes < self.threshold_bytes:
                # Since the input is sorted, we can usually stop early, but checking all lines is safer.
                continue

            # --- File is larger than threshold, proceed with move logic ---

            # 0. NEW CHECK: Filter by allowed extension
            is_allowed = False
            for ext in allowed_extensions:
                if repository_relative_filepath.lower().endswith(ext):
                    is_allowed = True
                    break

            if not is_allowed:
                files_skipped_by_extension += 1
                total_space_reclaimed_non_matching_extension += size_in_bytes
                continue

            # 1. Determine destination paths
            source_path_abs = os.path.join(self.repo_root, repository_relative_filepath)

            # Sanity check
            if not os.path.isfile(source_path_abs):
                print(f"ERROR: File does not exist at source: {source_path_abs}")
                continue

            # Strip the configured prefix from the relative path
            if repository_relative_filepath.startswith(self.path_prefix_to_strip):
                new_relative_path = repository_relative_filepath[len(self.path_prefix_to_strip) :]
            else:
                new_relative_path = repository_relative_filepath

            # Combine the clean relative path with the Google Drive root
            target_path_abs = os.path.join(self.google_drive_root, new_relative_path)
            target_dir_abs = os.path.dirname(target_path_abs)
            placeholder_path = source_path_abs + ".MOVED.txt"

            print(f"\n[MOVE Candidate #{current_candidate_no}: {human_size}]")
            print(f"  SOURCE: {source_path_abs}")
            print(f"  TARGET: {target_path_abs}")

            # 2. Execute/Simulate directory creation
            if not self.dry_run:
                try:
                    os.makedirs(target_dir_abs, exist_ok=True)
                    print(f"  Created directory: {target_dir_abs}")
                except Exception as e:
                    print(f"  ERROR creating directory: {e}")
                    continue
            else:
                print(f"  Dry Run: mkdir -p {target_dir_abs}")

            total_space_saved_bytes += size_in_bytes
            # 3. Execute/Simulate file move
            if not self.dry_run:
                try:
                    shutil.move(source_path_abs, target_path_abs)
                    print("  SUCCESS: Moved file.")

                    placeholder_content = (
                        "--- FILE MOVED ---\n"
                        f"Original file was moved by large_file_mover.py script on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n"
                        f"New location: {target_path_abs}\n"
                        "--------------------\n"
                    )

                    with open(placeholder_path, "w") as ph_file:
                        ph_file.write(placeholder_content)

                    print(f"  SUCCESS: Created placeholder at {os.path.basename(placeholder_path)}")
                    files_moved += 1
                except FileNotFoundError:
                    print(f"  ERROR: Source file not found at {source_path_abs}. Skipping.")
                except Exception as e:
                    print(f"  ERROR moving file: {e}")
            else:
                print(f"  Dry Run: mv {source_path_abs} {target_path_abs}")
                print(f"  Dry Run: Creating placeholder file: {placeholder_path}")
                files_moved += 1
            current_candidate_no += 1

        print("-" * 60)
        print("Summary:")
        print(f"Files meeting size and extension criteria: {files_moved}")
        if files_skipped_by_extension > 0:
            print(f"Files skipped due to extension filter: {files_skipped_by_extension}")

        total_space_saved_human = GitLargeFileMover.convert_bytes_to_human_readable(total_space_saved_bytes)
        non_matching_human = GitLargeFileMover.convert_bytes_to_human_readable(
            total_space_reclaimed_non_matching_extension
        )
        if self.dry_run:
            print(f"Would save estimated space: {total_space_saved_human}")
            print(f"Would save estimated space for non-matching extensions: {non_matching_human}")
            print("\nNote: Re-run with --execute to perform the actual move.")
        else:
            print(f"Estimated Space Saved: {total_space_saved_human}")
            print(f"Space for non-matching extensions (not moved): {non_matching_human}")


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
