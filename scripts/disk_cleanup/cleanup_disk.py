import logging
import shutil
import subprocess
import os
import tempfile
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Any, TextIO

import humanfriendly

DEVELOPMENT_ROOT = Path(os.path.expanduser("~/development"))
TOOL_OUTPUT_BASEDIR = Path(os.path.expanduser("~/snemeth-dev-projects/cleanup_disk/"))
ASDF_GOLANG_ROOT = Path(os.path.expanduser("~/.asdf/installs/golang"))
# TODO Use ~/.snemeth-dev-projects/disk_cleanup/logs for logging dir, search for: "log_path" in code
# TODO Prepare commands, before execute prompt user for all tools or for each tool one by one or use dry-run
# TODO Add JetBrains tool cleanup?

# Setup Global Logging Path
TIMESTAMP = time.strftime("%Y%m%d-%H%M%S")
LOG_FILE_PATH = TOOL_OUTPUT_BASEDIR / f"cleanup_{TIMESTAMP}.log"


# Initialize Logger
logger = logging.getLogger("DiskCleanup")
logger.setLevel(logging.DEBUG)


def setup_logging():
    TOOL_OUTPUT_BASEDIR.mkdir(parents=True, exist_ok=True)

    # Formatter for console and file
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S")

    # File Handler: Captures everything including subprocess DEBUG logs
    fh = logging.FileHandler(LOG_FILE_PATH)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)

    # Console Handler: High-level progress only
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)


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
    metadata: Optional[Dict[str, Any]] = None


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
    TOTAL_KEY = "total"

    def __init__(self):
        self._named_cleanup: Dict[str, CleanupDetails] = {}
        self.unnamed_cleanup: List[CleanupDetails] = []
        self._aggregate_cleanup: Dict[str, AggregateCleanupDetails] = {}

    def _register_default_aggregates(self):
        keys = set(self._named_cleanup)
        named_comps = [self._named_cleanup[k] for k in keys]
        self._aggregate_cleanup[CleanupDetailsTracker.TOTAL_KEY] = AggregateCleanupDetails(
            keys=list(keys), components=named_comps + self.unnamed_cleanup
        )

    def register_named_dir(self, key: str, dir: Path):
        new_details = CleanupDetails(dir, FileUtils.get_dir_size(dir), None)
        self._named_cleanup[key] = new_details

        # If a new named dir added, add it to "total"
        if CleanupDetailsTracker.TOTAL_KEY in self._aggregate_cleanup:
            self._aggregate_cleanup[CleanupDetailsTracker.TOTAL_KEY].keys.append(key)
            self._aggregate_cleanup[CleanupDetailsTracker.TOTAL_KEY].components.append(new_details)

    def register_named_dir_aggregate(self, new_key: str, *keys):
        not_found = set()
        for key in keys:
            if key not in self._named_cleanup:
                not_found.add(key)

        if not_found:
            raise ValueError(f"Cannot find keys '{not_found}'. Registered keys are: {self._named_cleanup.keys()}")

        if new_key in self._named_cleanup:
            raise ValueError(f"Attempted to override already existing key: {new_key}")

        self._aggregate_cleanup[new_key] = AggregateCleanupDetails(
            keys=list(keys), components=[self._named_cleanup[k] for k in keys]
        )

    def register_unnamed_dir(self, dir: Path, metadata: Dict[str, Any] = None) -> CleanupDetails:
        details = CleanupDetails(dir, FileUtils.get_dir_size(dir), None, metadata=metadata)
        self.unnamed_cleanup.append(details)
        return details

    def calculate_after_sizes(self):
        self._register_default_aggregates()

        for k in self._named_cleanup.keys():
            self._named_cleanup[k].after_size = FileUtils.get_dir_size(self._named_cleanup[k].dir)

        for details in self.unnamed_cleanup:
            details.after_size = FileUtils.get_dir_size(details.dir)

        for k in self._aggregate_cleanup.keys():
            self._aggregate_cleanup[k].recalculate()

    def get_before_size(self, key: str):
        if key in self._named_cleanup:
            return self._named_cleanup[key].before_size
        if key in self._aggregate_cleanup:
            return self._aggregate_cleanup[key].sum_before_size
        raise ValueError("Key not found: " + key)

    def get_after_size(self, key: str):
        if key in self._named_cleanup:
            return self._named_cleanup[key].after_size
        if key in self._aggregate_cleanup:
            return self._aggregate_cleanup[key].sum_after_size
        raise ValueError("Key not found: " + key)

    def get_space_reclaimed_for_named_cleanup(self, key: str):
        if key in self._named_cleanup:
            details = self._named_cleanup[key]
            return details.before_size - details.after_size
        if key in self._aggregate_cleanup:
            details = self._aggregate_cleanup[key]
            return details.sum_before_size - details.sum_after_size
        raise ValueError("Key not found: " + key)

    def get_space_reclaimed_for_unnamed_cleanup(self) -> int:
        sizes = [item.before_size if item.before_size else 0 for item in self.unnamed_cleanup]
        return sum(item for item in sizes)

    def get_space_reclaimed_total(self):
        details = self._aggregate_cleanup[CleanupDetailsTracker.TOTAL_KEY]
        return details.sum_before_size - details.sum_after_size


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

    def run_command(self, cmd: List[str], cwd: Optional[Path] = None):
        """Runs a command and pipes output directly to the logger."""
        full_cmd = " ".join(cmd)
        logger.debug(f"Executing: {full_cmd}")

        # We use Popen to capture line-by-line to avoid memory issues and keep log order
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=cwd)
        if process.stdout:
            for line in process.stdout:
                logger.debug(f"[Subprocess] {line.strip()}")
        process.wait()
        return process.returncode, full_cmd

    def run_command_check_output(self, cmd: List[str], cwd: Optional[Path] = None):
        full_cmd = " ".join(cmd)
        logger.debug(f"Executing: {full_cmd}")

        output = subprocess.check_output(cmd, cwd=cwd)
        return output.decode().strip(), full_cmd

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
        self.root_to_targets: Dict[Path, List[Path]] = defaultdict(list)
        self.tracker = CleanupDetailsTracker()

    def prepare(self):
        # TODO Limit is hardcoded
        logger.info("Scanning for Maven target directories > 100MB...")
        _ = humanfriendly.parse_size("100M")
        self._get_mvn_target_dirs("100M")
        targets = self.tracker.unnamed_cleanup
        if not targets:
            logger.info("No heavy Maven target dirs found.")
            return

        # Map target paths to their project roots to avoid redundant 'mvn clean' calls (as they are expensive operations)
        for target in targets:
            root = self.get_project_root(target.dir)
            self.root_to_targets[root].append(target.dir)
            logger.info("Found %s: %s", format_du_style(target.before_size), target.dir)

    def execute(self):
        # TODO 'executed_commands' unused
        executed_commands = []
        for root in sorted(self.root_to_targets.keys()):
            logger.info(f"Maven clean: {root}")
            pom_path = root / "pom.xml"
            if not pom_path.exists():
                logger.info(f"Skipping: {root} (pom.xml missing)")
                continue

            logger.info(f"\n{'='*20}\nCLEANING: {root}\n{'='*20}\n")
            # Execute Maven
            returncode, full_cmd = self.run_command(["mvn", "clean", "-f", str(pom_path)])

            executed_commands.append(full_cmd)
            if returncode == 0:
                logger.info("✅ Done.")
            else:
                logger.info("❌ Failed (Check log).")

    def verify(self) -> CleanupResult:
        logger.info("\n--- Verifying reclaimed space ---")
        self.tracker.calculate_after_sizes()

        targets = self.tracker.unnamed_cleanup
        for target in targets:
            reclaimed = target.before_size - target.after_size

            if target.dir.exists and reclaimed == 0:
                logger.info(f"Target: {target.dir}")
                logger.info("NO CHANGE IN SIZE")
            else:
                status = "DELETED" if not target.dir.exists() else f"REDUCED TO {format_du_style(target.after_size)}"
                logger.info(f"Target: {target.dir}")
                logger.info(f"  {format_du_style(target.before_size)} -> {status} (Saved {format_du_style(reclaimed)})")

        total_reclaimed_bytes = self.tracker.get_space_reclaimed_total()
        return CleanupResult(bytes_reclaimed=total_reclaimed_bytes, files_removed=-1, success=True, logs=[])

    def print_summary(self):
        logger.info("\n--- Maven cleanup summary ---")
        logger.info(f"Total Projects Cleaned: {len(self.root_to_targets)}")
        logger.info(f"Actual Space Reclaimed: {format_du_style(self.tracker.get_space_reclaimed_total())}")

    # TODO Limit is hardcoded
    def _get_mvn_target_dirs(self, size_limit="100M"):
        byte_limit = humanfriendly.parse_size(size_limit)
        # Using rglob to find all target folders
        for p in DEVELOPMENT_ROOT.rglob("target"):
            if p.is_dir():
                size = FileUtils.get_dir_size(p)
                if size >= byte_limit:
                    self.tracker.register_unnamed_dir(p)

    @staticmethod
    def get_project_root(path: Path) -> Path:
        """
        Finds the directory containing the top-level pom.xml.
        Ascends from the /target folder until it finds a pom or hits the dev root.
        """
        current = path.parent
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
        self.tracker = CleanupDetailsTracker()

    def prepare(self):
        logger.info("Scanning ASDF Golang versions...")
        self.tracker.register_named_dir("asdf_golang_root", ASDF_GOLANG_ROOT)
        if not ASDF_GOLANG_ROOT.exists():
            logger.info(f"asdf golang root does not exist at: {ASDF_GOLANG_ROOT}")
            return

        for item in ASDF_GOLANG_ROOT.iterdir():
            if item.is_dir() and item.name not in self.keep_versions:
                details = self.tracker.register_unnamed_dir(item, {"version": item.name})
                logger.info(f"Found old version: {item.name} ({format_du_style(details.before_size)})")

        go_cache, _ = self.run_command_check_output(["go", "env", "GOCACHE"])
        go_mod_cache, _ = self.run_command_check_output(["go", "env", "GOMODCACHE"])
        self.tracker.register_named_dir("go_cache", Path(go_cache))
        self.tracker.register_named_dir("go_mod_cache", Path(go_mod_cache))
        self.tracker.register_named_dir_aggregate("go_caches", "go_cache", "go_mod_cache")

    def execute(self):
        for details in self.tracker.unnamed_cleanup:
            version = details.metadata["version"]
            logger.info(f"Uninstalling Go {version}")
            self.run_command(["asdf", "uninstall", "golang", version])

        logger.info("Cleaning Go modcache...")
        self.run_command(["go", "clean", "-modcache", "-cache"])

    def verify(self) -> CleanupResult:
        self.tracker.calculate_after_sizes()

        # TODO unified print logic for all tools?
        logs = []
        for key, description in [
            ("go_caches", "go cache and modcache"),
            ("asdf_golang_root", "ASDF golang root"),
            (CleanupDetailsTracker.TOTAL_KEY, "ASDF Golang cleanup total"),
        ]:
            logs.append(
                f"{description} / Sum size before cleanup: {format_du_style(self.tracker.get_before_size(key))}"
            )
            logs.append(f"{description} / Sum size after cleanup: {format_du_style(self.tracker.get_after_size(key))}")
            logs.append(
                f"{description} / Space reclaimed: {format_du_style(self.tracker.get_space_reclaimed_for_named_cleanup(key))}"
            )
            logs.append("-" * 30)

        logs.append(
            f"Space reclaimed for explicitly removed items: {format_du_style(self.tracker.get_space_reclaimed_for_unnamed_cleanup())}"
        )
        total_reclaimed = self.tracker.get_space_reclaimed_for_named_cleanup("total")
        self.cleanup_result = CleanupResult(total_reclaimed, -1, True, logs)
        return self.cleanup_result

    def print_summary(self):
        for log in self.cleanup_result.logs:
            logger.info(log)


class DockerCleanup(CleanupTool):
    def prepare(self):
        pass

    def execute(self):
        logger.info("Docker system prune...")
        # -f forces without prompt
        self.run_command(["docker", "system", "prune", "-a", "--volumes", "-f"])

    def verify(self) -> CleanupResult:
        return CleanupResult(0, -1, True, [])  # Docker doesn't easily return bytes saved via CLI

    def print_summary(self):
        logger.info("Docker: System pruned (All unused images/volumes removed)")


class DiscoveryCleanup(CleanupTool):
    """Generic tool to find and delete specific directory patterns."""

    def __init__(self, name, root_path, patterns: List[str], age_days: int = 30):
        super().__init__()
        self.name = name
        self.root_path = Path(root_path)
        self.patterns = patterns
        self.age_days = age_days
        self.tracker = CleanupDetailsTracker()

    def prepare(self):
        if self.age_days != -1:
            logger.info(f"--- Scanning for {self.name} (Older than {self.age_days} days) ---")
        else:
            logger.info(f"--- Scanning for {self.name}")
        now = time.time()
        # Convert days to seconds: days * hours * minutes * seconds
        threshold_seconds = self.age_days * 24 * 60 * 60

        for pattern in self.patterns:
            for p in self.root_path.rglob(pattern):
                if p.is_dir():
                    if self.age_days != -1:
                        # Check the last modified time of the directory itself
                        mtime = p.stat().st_mtime
                        if (now - mtime) > threshold_seconds:
                            details = self.tracker.register_unnamed_dir(p)
                            last_touched = time.strftime("%Y-%m-%d", time.localtime(mtime))
                            logger.info(
                                f"Found stale dir: {p} (Last mod: {last_touched}, Size: {format_du_style(details.before_size)})"
                            )
                        else:
                            logger.info(f"Skipping active dir: {p} (Recently modified)")
                    else:
                        details = self.tracker.register_unnamed_dir(p)
                        logger.info(f"Found {p} ({format_du_style(details.before_size)})")

    def execute(self):
        for details in self.tracker.unnamed_cleanup:
            path = details.dir
            logger.info(f"Removing {path}...")
            if details.dir.is_dir():
                shutil.rmtree(details.dir, ignore_errors=True)

    def verify(self) -> CleanupResult:
        self.tracker.calculate_after_sizes()

        reclaimed = self.tracker.get_space_reclaimed_for_unnamed_cleanup()
        logs = [f"{self.name}: Reclaimed {format_du_style(reclaimed)}"]

        self.cleanup_result = CleanupResult(reclaimed, -1, True, logs)
        return self.cleanup_result

    def print_summary(self):
        for log in self.cleanup_result.logs:
            logger.info(log)


class PoetryCacheCleanup(CleanupTool):
    def __init__(self):
        super().__init__()
        self.name = "Poetry cache cleanup"
        self.log_path = Path(tempfile.gettempdir()) / "poetry_cache_clean.log"
        self.tracker = CleanupDetailsTracker()

    def prepare(self):
        cache_dir, _ = self.run_command_check_output(["poetry", "config", "cache-dir"])
        self.tracker.register_named_dir("poetry_cache", Path(cache_dir))

    def execute(self):
        _ = self.run_command(["poetry", "cache", "clear", ".", "--all"])

    def verify(self) -> CleanupResult:
        self.tracker.calculate_after_sizes()
        total_reclaimed_bytes = self.tracker.get_space_reclaimed_total()
        self.cleanup_result = CleanupResult(total_reclaimed_bytes, -1, True, [])
        return self.cleanup_result

    def print_summary(self):
        logger.info(f"{self.name}: Reclaimed {format_du_style(self.cleanup_result.bytes_reclaimed)}")


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


class ToolRunner:
    @staticmethod
    def run_tools(tools: List[CleanupTool]):
        setup_logging()
        TOOL_OUTPUT_BASEDIR.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting cleanup. Detailed logs: {LOG_FILE_PATH}")
        for tool in tools:
            tool.prepare()
            tool.execute()
            _ = tool.verify()
            tool.print_summary()
            logger.info("-" * 30)


def main():
    tools: List[CleanupTool] = [
        # MavenCleanup(), # (From your original code)
        # AsdfGolangCleanup(keep_versions=["1.24.11"]),
        # DockerCleanup(),
        # DiscoveryCleanup("Python Venvs", DEVELOPMENT_ROOT, ["venv", ".venv"]),
        # DiscoveryCleanup("Terraform", DEVELOPMENT_ROOT, [".terraform"]),
        # DiscoveryCleanup("Pip Cache", "~/Library/Caches/pip", ["*"]),
        # PoetryCacheCleanup()
    ]
    ToolRunner.run_tools(tools)


if __name__ == "__main__":
    main()
