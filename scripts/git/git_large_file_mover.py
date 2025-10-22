import re
import sys
import os
import shutil
from typing import Optional, Dict

# --- Configuration Constants ---
# Set to False to actually execute the file move operations
DRY_RUN = True
# Threshold for moving files (20 Megabytes in bytes)
THRESHOLD_BYTES = 20 * 1024 * 1024
# The root destination directory on your local machine
GOOGLE_DRIVE_ROOT = os.path.expanduser('~/googledrive')
# -------------------------------


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


def process_and_move(input_filepath: str):
    """
    Reads the file list, identifies files larger than the threshold, and moves them
    to the Google Drive root, preserving the relative path.
    """
    if DRY_RUN:
        print("!!! DRY RUN MODE ACTIVE !!!")
        print("No files will be moved. Commands are printed below.")
    else:
        print("!!! REAL MOVE MODE ACTIVE !!!")
        print(f"Files > {THRESHOLD_BYTES // 1024 // 1024}MB will be MOVED to {GOOGLE_DRIVE_ROOT}")

    print("-" * 60)

    try:
        with open(input_filepath, 'r') as f:
            raw_data = f.read()
    except Exception as e:
        print(f"Error reading input file: {e}")
        return

    lines = raw_data.strip().split('\n')
    files_moved = 0
    total_space_saved_bytes = 0

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
        relative_source_filepath = match.group(3).strip()

        size_in_bytes = parse_human_size(human_size)

        if size_in_bytes is None or size_in_bytes < THRESHOLD_BYTES:
            # Since the input is sorted, we can often stop early when we hit the threshold
            # but we'll process all lines to be safe.
            continue

        # --- File is larger than 20MB, proceed with move logic ---

        # 1. Determine destination paths
        source_path_abs = os.path.abspath(relative_source_filepath)
        target_path_abs = os.path.join(GOOGLE_DRIVE_ROOT, relative_source_filepath)
        target_dir_abs = os.path.dirname(target_path_abs)

        print(f"\n[MOVE Candidate: {human_size}]")
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

        # 3. Execute/Simulate file move
        if not DRY_RUN:
            try:
                # Use shutil.move for a robust atomic move operation
                shutil.move(source_path_abs, target_path_abs)
                print(f"  SUCCESS: Moved file.")
                files_moved += 1
                total_space_saved_bytes += size_in_bytes
            except FileNotFoundError:
                print(f"  ERROR: Source file not found at {source_path_abs}. Skipping.")
            except Exception as e:
                print(f"  ERROR moving file: {e}")
        else:
            print(f"  Dry Run: mv {source_path_abs} {target_path_abs}")
            files_moved += 1 # Count for summary, even if dry run

    print("-" * 60)
    print(f"Summary:")
    print(f"Files selected for move (> {THRESHOLD_BYTES // 1024 // 1024}MB): {files_moved}")

    # Only show space saved if it was a real run
    if not DRY_RUN:
        total_space_saved_human = f"{total_space_saved_bytes / 1024**3:.2f} GB" if total_space_saved_bytes > 1024**3 else f"{total_space_saved_bytes / 1024**2:.2f} MB"
        print(f"Estimated Space Saved: {total_space_saved_human}")

    if DRY_RUN:
        print("\nNote: Change DRY_RUN = False inside the script to execute the actual move.")


if __name__ == "__main__":
    # Ensure the script is called with exactly one argument (the path to the output file)
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <path_to_commit_size_output_file>")
        print(f"Example: python {sys.argv[0]} /Users/snemeth/Downloads/git-details-kb-private-hash-60f41a56.txt")
        sys.exit(1)

    input_filepath = sys.argv[1]
    process_and_move(input_filepath)
