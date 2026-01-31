import subprocess
import os
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import humanfriendly

DEVELOPMENT_ROOT = Path(os.path.expanduser("~/development"))


class FileUtils:
    @staticmethod
    def get_dir_size(path):
        """Calculates total size of a directory in bytes natively."""
        path = Path(path)
        if not path.exists():
            return 0
        total = 0
        try:
            for entry in os.scandir(path):
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += FileUtils.get_dir_size(entry.path)
        except (PermissionError, OSError):
            pass
        return total


@dataclass
class CleanupResult:
    bytes_reclaimed: int
    files_removed: int
    success: bool


class CleanupTool(ABC):
    @abstractmethod
    def prepare(self):
        pass

    @abstractmethod
    def execute(self):
        pass

    @abstractmethod
    def verify(self) -> CleanupResult:
        pass

    @abstractmethod
    def print_summary(self):
        pass


class MavenCleanup(CleanupTool):
    def __init__(self):
        self.targets = []
        self.root_to_targets = {}
        self.total_reclaimed_bytes = 0
        self.log_path = Path(tempfile.gettempdir()) / "maven_clean.log"

    def prepare(self):
        print("--- 1. Scanning for heavy mvn target directories ---")
        self.targets = self._get_mvn_target_dirs("100M")

        if not self.targets:
            print("No heavy targets found.")
            return

        # Map target paths to their project roots to avoid redundant 'mvn clean' calls
        root_to_targets = {}
        for t in self.targets:
            root = str(self.get_project_root(t["path"]))
            if root not in root_to_targets:
                root_to_targets[root] = []
            root_to_targets[root].append(t)
            print(f"Found {format_du_style(t['before'])}: {t['path']}")

        self.root_to_targets = root_to_targets

    def execute(self):
        # Create a temporary log file
        print(f"\n--- 2. Executing maven clean (Logging to: {self.log_path}) ---")

        executed_commands = []
        with open(self.log_path, "w") as log_file:
            for root in sorted(self.root_to_targets.keys()):
                print(f"Cleaning Project: {root}")
                pom_path = os.path.join(root, "pom.xml")
                if not os.path.exists(pom_path):
                    print(f"Skipping: {root} (pom.xml missing)")
                    continue

                print("Executing maven command")
                cmd = ["mvn", "clean", "-f", pom_path]

                # Write start marker to log
                log_file.write(f"\n{'='*20}\nCLEANING: {root}\n{'='*20}\n")
                log_file.flush()

                # Execute Maven
                result = subprocess.run(cmd, stdout=log_file, stderr=log_file)
                executed_commands.append(" ".join(cmd))
                if result.returncode == 0:
                    print("✅ Done.")
                else:
                    print("❌ Failed (Check log).")

    def verify(self) -> CleanupResult:
        print("\n--- 3. Verifying reclaimed space ---")
        self.total_reclaimed_bytes = 0

        for t in self.targets:
            after_size = FileUtils.get_dir_size(t["path"])  # Will be 0 if folder was deleted
            reclaimed = t["before"] - after_size
            self.total_reclaimed_bytes += reclaimed

            status = "DELETED" if not os.path.exists(t["path"]) else f"REDUCED TO {format_du_style(after_size)}"
            print(f"Target: {t['path']}")
            print(f"  {format_du_style(t['before'])} -> {status} (Saved {format_du_style(reclaimed)})")

        return CleanupResult(bytes_reclaimed=self.total_reclaimed_bytes, files_removed=-1, success=True)

    def print_summary(self):
        print("\n--- Maven cleanup summary ---")
        print(f"Total Projects Cleaned: {len(self.root_to_targets)}")
        print(f"Actual Space Reclaimed: {format_du_style(self.total_reclaimed_bytes)}")
        print(f"Log file available at: {self.log_path}")

    @staticmethod
    def _get_mvn_target_dirs(size_limit="100M"):
        byte_limit = humanfriendly.parse_size(size_limit)
        found = []
        # Using rglob to find all target folders
        for p in DEVELOPMENT_ROOT.rglob("target"):
            if p.is_dir():
                size = FileUtils.get_dir_size(p)
                if size >= byte_limit:
                    found.append({"path": str(p), "before": size})
        return found

    @staticmethod
    def get_project_root(path):
        """
        Finds the directory containing the top-level pom.xml.
        Ascends from the /target folder until it finds a pom or hits the dev root.
        """
        current = Path(path).parent
        project_root = current
        while str(current) != str(DEVELOPMENT_ROOT) and str(current) != "/":
            if (current / "pom.xml").exists():
                project_root = current
            current = current.parent
        return project_root


def format_du_style(size_in_bytes):
    """Formats bytes to 1.2G, 400M, etc. using humanfriendly 10.0"""
    # Use binary=True to get 1024-base (MiB/GiB)
    readable = humanfriendly.format_size(size_in_bytes, binary=True)

    # Logic to match 'du -sh' output style:
    # 1. Remove the 'iB' (making GiB -> G, MiB -> M)
    # 2. Remove the space
    return readable.replace("iB", "").replace(" ", "")


def parse_to_bytes(size_str):
    """Converts du human-readable strings to bytes using humanfriendly."""
    # binary=True ensures 'M' is treated as 1024^2 (MiB) and 'G' as 1024^3 (GiB)
    # This matches the 'du -sh' behavior on macOS/Linux.
    return humanfriendly.parse_size(size_str, binary=True)


def main():
    mvn_cleanup = MavenCleanup()
    mvn_cleanup.prepare()
    mvn_cleanup.execute()
    mvn_cleanup.verify()
    mvn_cleanup.print_summary()


if __name__ == "__main__":
    main()
