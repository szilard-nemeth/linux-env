import shutil
import subprocess
import os
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional

import humanfriendly

DEVELOPMENT_ROOT = Path(os.path.expanduser("~/development"))
ASDF_GOLANG_ROOT = Path(os.path.expanduser("~/.asdf/installs/golang"))
# TODO Prepare commands, before execute prompt user for all tools or for each tool one by one
# TODO Use ~/.snemeth-dev-projects/disk-cleanup/logs for logging dir
# TODO Extract commandrunner
# TODO Each command should log stdout + stderr to a file: subprocess.run
# TODO Add JetBrains tool cleanup


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
class CleanupDetails:
    # TODO Similar to CleanupResult, refactor
    dir: Path
    before_size: Optional[int] = None
    after_size: Optional[int] = None


@dataclass
class AggregateCleanupDetails:
    keys: List[str]
    components: List[CleanupDetails]
    sum_before_size: Optional[int] = None
    sum_after_size: Optional[int] = None

    def __post_init__(self):
        self.recalculate()

    def recalculate(self):
        self.sum_before_size = 0
        self.sum_after_size = 0
        for detail in self.components:
            self.sum_before_size += detail.before_size
            self.sum_after_size += detail.after_size if detail.after_size else 0


class CleanupDetailsTracker:
    def __init__(self):
        self._details: Dict[str, CleanupDetails] = {}
        self._aggregate_details: Dict[str, AggregateCleanupDetails] = {}

    def register_directory(self, key: str, dir: Path):
        self._details[key] = CleanupDetails(dir, FileUtils.get_dir_size(dir), None)

    def register_dir_aggregate(self, new_key: str, *keys):
        not_found = set()
        for key in keys:
            if key not in self._details:
                not_found.add(key)

        if not_found:
            raise ValueError(f"Cannot find keys '{not_found}'. Registered keys are: {self._details.keys()}")

        if new_key in self._details:
            raise ValueError(f"Attempted to override already existing key: {new_key}")

        self._aggregate_details[new_key] = AggregateCleanupDetails(
            keys=keys, components=[self._details[k] for k in keys]
        )

    def calculate_after_sizes(self, *keys):
        simple_keys = [k for k in keys if k in self._details]
        aggregate_keys = [k for k in keys if k in self._aggregate_details]

        for k in simple_keys:
            self._details[k].after_size = FileUtils.get_dir_size(self._details[k].dir)
        for k in aggregate_keys:
            self._aggregate_details[k].recalculate()

    def get_before_size(self, key: str):
        if key in self._details:
            return self._details[key].before_size
        if key in self._aggregate_details:
            return self._aggregate_details[key].sum_before_size
        raise ValueError("Key not found: " + key)

    def get_after_size(self, key: str):
        if key in self._details:
            return self._details[key].after_size
        if key in self._aggregate_details:
            return self._aggregate_details[key].sum_after_size
        raise ValueError("Key not found: " + key)

    def get_size_diff(self, key: str):
        if key in self._details:
            return self._details[key].before_size - self._details[key].after_size
        if key in self._aggregate_details:
            return self._aggregate_details[key].sum_before_size - self._aggregate_details[key].sum_after_size
        raise ValueError("Key not found: " + key)


@dataclass
class CleanupResult:
    bytes_reclaimed: int
    # TODO remove this
    files_removed: int
    success: bool
    logs: List[str]


class CleanupTool(ABC):
    def __init__(self):
        self.cleanup_result = None

    @abstractmethod
    def prepare(self):
        pass

    @abstractmethod
    def execute(self):
        pass

    @abstractmethod
    def verify(self) -> CleanupResult:
        pass

    # TODO This should be get_summary and print logic should be decoupled
    @abstractmethod
    def print_summary(self):
        pass


class MavenCleanup(CleanupTool):
    def __init__(self):
        super().__init__()
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

                cmd = ["mvn", "clean", "-f", pom_path]
                full_cmd = " ".join(cmd)
                print("Executing command: " + full_cmd)

                # Write start marker to log
                log_file.write(f"\n{'='*20}\nCLEANING: {root}\n{'='*20}\n")
                log_file.flush()

                # Execute Maven
                result = subprocess.run(cmd, stdout=log_file, stderr=log_file)
                executed_commands.append(full_cmd)
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
    # TODO Limit is hardcoded
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


class AsdfGolangCleanup(CleanupTool):
    def __init__(self, keep_versions: List[str]):
        super().__init__()
        self.keep_versions = keep_versions
        self.to_remove = []
        self.reclaimed = 0
        self.tracker = CleanupDetailsTracker()

    def prepare(self):
        self.tracker.register_directory("asdf_golang_root", ASDF_GOLANG_ROOT)
        print("--- Scanning ASDF Golang versions ---")
        if not ASDF_GOLANG_ROOT.exists():
            print(f"asdf golang root does not exist at: {ASDF_GOLANG_ROOT}")
            return

        self.before_size_asdf_golang_root = FileUtils.get_dir_size(ASDF_GOLANG_ROOT)
        for item in ASDF_GOLANG_ROOT.iterdir():
            if item.is_dir() and item.name not in self.keep_versions:
                size = FileUtils.get_dir_size(item)
                self.to_remove.append({"path": item, "version": item.name, "size": size})
                print(f"Found old version: {item.name} ({format_du_style(size)})")

        go_cache = subprocess.check_output(["go", "env", "GOCACHE"]).decode().strip()
        go_mod_cache = subprocess.check_output(["go", "env", "GOMODCACHE"]).decode().strip()
        self.tracker.register_directory("go_cache", Path(go_cache))
        self.tracker.register_directory("go_mod_cache", Path(go_mod_cache))
        self.tracker.register_dir_aggregate("go_caches", "go_cache", "go_mod_cache")
        self.tracker.register_dir_aggregate("total", "go_cache", "go_mod_cache", "asdf_golang_root")

    def execute(self):
        for item in self.to_remove:
            print(f"Uninstalling golang {item['version']}...")
            subprocess.run(["asdf", "uninstall", "golang", item["version"]])

        # TODO store previous size + new size after deletion and print diff
        print("Cleaning Go modcache...")
        subprocess.run(["go", "clean", "-modcache", "-cache"])

    def verify(self) -> CleanupResult:
        self.tracker.calculate_after_sizes("total", "go_caches", "go_cache", "go_mod_cache", "asdf_golang_root")

        logs = []
        for key, description in [("go_caches", "go cache and modcache"), ("asdf_golang_root", "ASDF golang root")]:
            logs.append(
                f"{description} / Sum size before cleanup: {format_du_style(self.tracker.get_before_size(key))}"
            )
            logs.append(f"{description} / Sum size after cleanup: {format_du_style(self.tracker.get_after_size(key))}")
            logs.append(f"{description} / Space reclaimed: {format_du_style(self.tracker.get_size_diff(key))}")
            logs.append("-" * 30)

        self.reclaimed = sum(item["size"] for item in self.to_remove)
        logs.append(f"Space reclaimed for known removed items: {format_du_style(self.reclaimed)}")
        self.cleanup_result = CleanupResult(self.reclaimed, -1, True, logs)
        return self.cleanup_result

    def print_summary(self):
        for log in self.cleanup_result.logs:
            print(log)
        print(f"ASDF Golang cleanup: Total reclaimed {format_du_style(self.reclaimed)}")


class DockerCleanup(CleanupTool):
    def prepare(self):
        print("--- Preparing Docker Prune ---")

    def execute(self):
        # -f forces without prompt
        subprocess.run(["docker", "system", "prune", "-a", "--volumes", "-f"])

    def verify(self) -> CleanupResult:
        return CleanupResult(0, -1, True)  # Docker doesn't easily return bytes saved via CLI

    def print_summary(self):
        print("Docker: System pruned (All unused images/volumes removed)")


class DiscoveryCleanup(CleanupTool):
    """Generic tool to find and delete specific directory patterns."""

    def __init__(self, name, root_path, patterns: List[str]):
        super().__init__()
        self.name = name
        self.root_path = Path(root_path)
        self.patterns = patterns
        self.found_dirs = []
        self.reclaimed = 0

    def prepare(self):
        print(f"--- Scanning for {self.name} ---")
        for pattern in self.patterns:
            for p in self.root_path.rglob(pattern):
                if p.is_dir():
                    size = FileUtils.get_dir_size(p)
                    self.found_dirs.append((p, size))
                    print(f"Found {p} ({format_du_style(size)})")

    def execute(self):
        for path, size in self.found_dirs:
            print(f"Removing {path}...")
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            self.reclaimed += size

    def verify(self) -> CleanupResult:
        return CleanupResult(self.reclaimed, -1, True)

    def print_summary(self):
        print(f"{self.name}: Reclaimed {format_du_style(self.reclaimed)}")


class PoetryCacheCleanup(CleanupTool):
    def __init__(self):
        super().__init__()
        self.name = "Poetry cache cleanup"
        self.log_path = Path(tempfile.gettempdir()) / "poetry_cache_clean.log"
        self._cache_dir_size_after = -1
        self._cache_dir_size_before = -1
        self._poetry_cache_dir = None
        self.total_reclaimed_bytes = -1

    def prepare(self):
        cmd = ["poetry", "config", "cache-dir"]
        full_cmd = " ".join(cmd)
        print("Executing command: " + full_cmd)
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        self._poetry_cache_dir = result.stdout.rstrip()

    def execute(self):
        self._cache_dir_size_before = FileUtils.get_dir_size(self._poetry_cache_dir)

        cmd = ["poetry", "cache", "clear", ".", "--all"]
        full_cmd = " ".join(cmd)
        print("Executing command: " + full_cmd)
        _ = subprocess.run(cmd, check=True, capture_output=True, text=True)

    def verify(self) -> CleanupResult:
        self._cache_dir_size_after = FileUtils.get_dir_size(self._poetry_cache_dir)
        self.total_reclaimed_bytes = self._cache_dir_size_before - self._cache_dir_size_after
        return CleanupResult(self.total_reclaimed_bytes, -1, True)

    def print_summary(self):
        print(f"{self.name}: Reclaimed {format_du_style(self.total_reclaimed_bytes)}")


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
    tools: List[CleanupTool] = [
        # MavenCleanup(), # (From your original code)
        AsdfGolangCleanup(keep_versions=["1.24.11"]),
        # DockerCleanup(),
        # DiscoveryCleanup("Python Venvs", DEVELOPMENT_ROOT, ["venv", ".venv"]),
        # DiscoveryCleanup("Terraform", DEVELOPMENT_ROOT, [".terraform"]),
        # DiscoveryCleanup("Pip Cache", "~/Library/Caches/pip", ["*"]),
        # PoetryCacheCleanup()
    ]
    for tool in tools:
        tool.prepare()
        tool.execute()
        _ = tool.verify()
        tool.print_summary()
        print("-" * 30)


if __name__ == "__main__":
    main()
