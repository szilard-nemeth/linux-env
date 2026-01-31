import subprocess
import os
import re
from pathlib import Path

DEVELOPMENT_ROOT = Path(os.path.expanduser("~/development"))

def get_mvn_target_dirs():
    """Finds all 'target' dirs using Path.glob and runs du on them."""
    # Recursive glob to find all 'target' directories
    target_paths = list(DEVELOPMENT_ROOT.rglob("target"))

    if not target_paths:
        return []

    # Convert PosixPaths to strings for the command
    path_strings = [str(p) for p in target_paths]

    # We use a smaller grep here because we already narrowed it down to 'target' dirs
    # We still use shell=True to allow the pipe to grep
    cmd = f"du -sh {' '.join(path_strings)} 2>/dev/null | grep -E '^([0-9.]+G|[1-9][0-9]{{2}}M)'"

    process = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    results = []
    for line in process.stdout.strip().split('\n'):
        if '\t' in line:
            results.append(line.split('\t'))
    return results

def parse_to_bytes(size_str):
    """Converts du human-readable strings to bytes for math."""
    num = float(re.sub(r'[MG]', '', size_str))
    if 'G' in size_str: return num * 1024**3
    if 'M' in size_str: return num * 1024**2
    return num

def get_project_root(path):
    """
    Finds the directory containing the top-level pom.xml.
    Ascends from the /target folder until it finds a pom or hits the dev root.
    """
    current = os.path.dirname(path)
    project_root = current
    while current != str(DEVELOPMENT_ROOT):
        if os.path.exists(os.path.join(current, "pom.xml")):
            project_root = current
        current = os.path.dirname(current)
    return project_root

def main():
    print("--- 1. Logging heavy mvn target directories ---")
    targets = get_mvn_target_dirs()
    if not targets:
        print("No mvn targets > 100MB found.")
        return

    total_reclaimed_bytes = 0
    projects_to_clean = set()

    for size_str, path in targets:
        print(f"Found {size_str} in {path}")
        total_reclaimed_bytes += parse_to_bytes(size_str)
        projects_to_clean.add(get_project_root(path))

    print("\n--- 2. Executing maven clean commands ---")
    executed_commands = []
    for project in sorted(projects_to_clean):
        cmd = ["mvn", "clean", "-f", os.path.join(project, "pom.xml")]
        print(f"Executing: {' '.join(cmd)}")
        executed_commands.append(" ".join(cmd))

        # Run the clean
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("\n--- 3. Final Summary ---")
    print(f"Total commands executed: {len(executed_commands)}")
    reclaimed_gb = total_reclaimed_bytes / (1024**3)
    print(f"Total space reclaimed: {reclaimed_gb:.2f} GiB")

    print("\n--- 4. Verification ---")
    remaining = get_mvn_target_dirs()
    if not remaining:
        print("Verification Success: No results > 100MB found.")
    else:
        print(f"Warning: {len(remaining)} targets still remain above 100MB.")

if __name__ == "__main__":
    main()