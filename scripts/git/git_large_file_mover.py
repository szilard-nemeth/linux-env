import re
import sys
import os
import shutil
import datetime
from typing import Optional, Dict

# --- Configuration Constants ---
# Set to False to actually execute the file move operations
DRY_RUN = True
# The root destination directory on your local machine
GOOGLE_DRIVE_ROOT = os.path.expanduser('~/googledrive/development/KB-private-offloaded')

# The prefix to strip from the relative path before moving.
# This ensures the files are nested correctly inside the GOOGLE_DRIVE_ROOT.
PATH_PREFIX_TO_STRIP = 'cloudera/tasks/cde/'
KB_PRIVATE_ROOT = "/Users/snemeth/development/my-repos/knowledge-base-private"

# NEW CONFIGURATION: Extensions that are allowed to be moved
# All extensions should be lowercase for case-insensitive matching.
ALLOWED_EXTENSIONS = ['.tar.gz', '.gz', '.zip', '.gzip']
# -------------------------------

def convert_to_human_space(total_space_saved_bytes: int):
    return f"{total_space_saved_bytes / 1024**3:.2f} GB" if total_space_saved_bytes > 1024**3 else f"{total_space_saved_bytes / 1024**2:.2f} MB"

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
        None: 1,
        'K': 1024,
        'M': 1024**2,
        'G': 1024**3,
        'T': 1024**4,
        'P': 1024**5,
    }

    multiplier = units_map.get(unit, 1)
    return int(value * multiplier)


def process_and_move(input_filepath: str, threshold_bytes: int):
    """
    Reads the file list, identifies files larger than the threshold, and moves them
    to the Google Drive root, preserving the relative path after stripping the prefix.
    It also creates a placeholder file in the original location upon a successful move.

    Args:
        input_filepath: Path to the file containing the size analysis output.
        threshold_bytes: The minimum file size in bytes required for a move.
    """
    if DRY_RUN:
        print("!!! DRY RUN MODE ACTIVE !!!")
        print("No files will be moved. Commands are printed below.")
    else:
        print("!!! REAL MOVE MODE ACTIVE !!!")
        print(f"Files > {threshold_bytes // 1024 // 1024}MB will be MOVED to {GOOGLE_DRIVE_ROOT}")

    print("-" * 60)
    print(f"NOTE: Stripping prefix '{PATH_PREFIX_TO_STRIP}' from source paths.")
    print(f"NOTE: Only processing files with extensions: {', '.join(ALLOWED_EXTENSIONS)}")

    try:
        with open(input_filepath, 'r') as f:
            raw_data = f.read()
    except Exception as e:
        print(f"Error reading input file: {e}")
        return

    lines = raw_data.strip().split('\n')
    files_moved = 0
    files_skipped_by_extension = 0
    total_space_saved_bytes = 0
    total_space_reclaimed_non_matching_extension = 0

    current_candidate_no = 1
    for line in lines:
        # Skip header/footer lines and lines that don't look like file entries
        if not line.startswith('#'):
            continue

        # Use regex to robustly extract SIZE and FILENAME
        # Example format: #1: 1013MB -> cloudera/tasks/...
        match = re.search(r":\s*(\d+(\.\d+)?\s*[KMGTPE]?B?)\s*->\s*(.*)", line)

        if not match:
            continue

        human_size = match.group(1).strip()
        repository_relative_filepath = match.group(3).strip()

        size_in_bytes = parse_human_size(human_size)

        if size_in_bytes is None or size_in_bytes < threshold_bytes:
            # Since the input is sorted, we can usually stop early, but checking all lines is safer.
            continue

        # --- File is larger than threshold, proceed with move logic ---

        # 0. NEW CHECK: Filter by allowed extension
        is_allowed = False
        for ext in ALLOWED_EXTENSIONS:
            if repository_relative_filepath.lower().endswith(ext):
                is_allowed = True
                break

        if not is_allowed:
            files_skipped_by_extension += 1
            total_space_reclaimed_non_matching_extension += size_in_bytes
            # print(f"[SKIP Candidate #{i + 1}: {human_size}] Extension filter: {repository_relative_filepath}")
            continue

        # 1. Determine destination paths
        source_path_abs = os.path.join(KB_PRIVATE_ROOT, repository_relative_filepath)

        # Sanity check
        if not os.path.isfile(source_path_abs):
            # We don't increment files_moved here, as it was never successfully moved
            print(f"ERROR: File does not exist at source: {source_path_abs}")
            continue

        # Strip the configured prefix from the relative path
        if repository_relative_filepath.startswith(PATH_PREFIX_TO_STRIP):
            # Remove the common repository path prefix
            new_relative_path = repository_relative_filepath[len(PATH_PREFIX_TO_STRIP):]
        else:
            new_relative_path = repository_relative_filepath

        # Combine the clean relative path with the Google Drive root
        target_path_abs = os.path.join(GOOGLE_DRIVE_ROOT, new_relative_path)
        target_dir_abs = os.path.dirname(target_path_abs)
        placeholder_path = source_path_abs + ".MOVED.txt" # Define placeholder path

        print(f"\n[MOVE Candidate #{current_candidate_no}: {human_size}]")
        print(f"  SOURCE: {source_path_abs}")
        print(f"  TARGET: {target_path_abs}")

        # 2. Execute/Simulate directory creation
        if not DRY_RUN:
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
        if not DRY_RUN:
            try:
                # Use shutil.move for a robust atomic move operation
                shutil.move(source_path_abs, target_path_abs)
                print(f"  SUCCESS: Moved file.")

                # --- NEW LOGIC: Create Placeholder File ---
                placeholder_content = (
                    "--- FILE MOVED ---\n"
                    f"Original file was moved by large_file_mover.py script on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n"
                    f"New location: {target_path_abs}\n"
                    "--------------------\n"
                )

                with open(placeholder_path, 'w') as ph_file:
                    ph_file.write(placeholder_content)

                print(f"  SUCCESS: Created placeholder at {os.path.basename(placeholder_path)}")
                # --- END NEW LOGIC ---

                files_moved += 1
            except FileNotFoundError:
                print(f"  ERROR: Source file not found at {source_path_abs}. Skipping.")
            except Exception as e:
                print(f"  ERROR moving file: {e}")
        else:
            # Dry Run Output
            print(f"  Dry Run: mv {source_path_abs} {target_path_abs}")
            print(f"  Dry Run: Creating placeholder file: {placeholder_path}")
            files_moved += 1 # Count for summary, even if dry run
        current_candidate_no += 1

    print("-" * 60)
    print(f"Summary:")
    print(f"Files meeting size and extension criteria: {files_moved}")
    if files_skipped_by_extension > 0:
        print(f"Files skipped due to extension filter: {files_skipped_by_extension}")

    total_space_saved_human = convert_to_human_space(total_space_saved_bytes)
    if not DRY_RUN:
        print(f"Estimated Space Saved: {total_space_saved_human}")
        print(f"Would save estimated space for non-matching extensions: {convert_to_human_space(total_space_reclaimed_non_matching_extension)}")

    if DRY_RUN:
        print(f"Would save estimated space: {total_space_saved_human}")
        print(f"Would save estimated space for non-matching extensions: {convert_to_human_space(total_space_reclaimed_non_matching_extension)}")
        print("\nNote: Change DRY_RUN = False inside the script to execute the actual move.")


if __name__ == "__main__":
    # Ensure the script is called with expected number of arguments
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <path_to_commit_size_output_file> <threshold MB>")
        print(f"Example: python {sys.argv[0]} /Users/snemeth/Downloads/git-details-kb-private-hash-60f41a56.txt 20")
        sys.exit(1)

    input_filepath = sys.argv[1]

    try:
        threshold_mb = int(sys.argv[2])
    except ValueError:
        print(f"Error: Threshold MB must be an integer, got '{sys.argv[2]}'")
        sys.exit(1)

    # Threshold for moving files (20 Megabytes in bytes)
    threshold_bytes = threshold_mb * 1024 * 1024

    process_and_move(input_filepath, threshold_bytes)
