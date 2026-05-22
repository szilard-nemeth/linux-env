import click
import logging
import re
import shutil
import subprocess
import os
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
    success: bool
    logs: List[str]


class CleanupTool(ABC):
    summary_name: str = ""

    def __init__(self, interactive: bool = True):
        self.interactive = interactive
        self._execute_skipped = False
        self.cleanup_result: Optional[CleanupResult] = None

    def reclaimed_bytes(self) -> int:
        if self.cleanup_result is None:
            return 0
        return self.cleanup_result.bytes_reclaimed

    def _summary_label(self) -> str:
        return self.summary_name or self.__class__.__name__

    def print_summary(self) -> None:
        label = self._summary_label()
        if self._execute_skipped and self.reclaimed_bytes() == 0:
            logger.info("%s: 0 disk space reclaimed (skipped or canceled)", label)
        else:
            logger.info("%s: %s disk space reclaimed", label, format_du_style(self.reclaimed_bytes()))

    def _has_pending_work(self) -> bool:
        """Return True if prepare found actionable cleanup work."""
        return False

    def _confirmation_prompt(self) -> str:
        return "Proceed with cleanup as described above? (y/n): "

    def _confirm_execution(self, prompt: str) -> bool:
        try:
            answer = input(prompt)
        except EOFError:
            return False
        return answer.strip().lower() in ("y", "yes")

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

    def execute_flow(self):
        self.prepare()
        if self.interactive and self._has_pending_work():
            if not self._confirm_execution(self._confirmation_prompt()):
                logger.info("Operation canceled by user.")
                self._execute_skipped = True
        if not self._execute_skipped:
            self.execute()
        _ = self.verify()
        self.print_summary()
        logger.info("-" * 30)


class MavenCleanup(CleanupTool):
    summary_name = "Maven cleanup"

    def __init__(self, limit: str, interactive: bool = True):
        """
        :param limit: Human-readable limit for directory size, e.g. 100M
        """
        super().__init__(interactive=interactive)
        self.root_to_targets: Dict[Path, List[Path]] = defaultdict(list)
        self.tracker = CleanupDetailsTracker()
        self._limit_str: str = limit
        self._limit_bytes: int = humanfriendly.parse_size(limit)

    def _has_pending_work(self) -> bool:
        return bool(self.root_to_targets)

    def _confirmation_prompt(self) -> str:
        count = len(self.root_to_targets)
        return f"Proceed with Maven clean on {count} project(s)? (y/n): "

    def prepare(self):
        logger.info(f"Scanning for Maven target directories > {self._limit_str}...")
        self._get_mvn_target_dirs(self._limit_bytes)
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

            if target.dir.exists() and reclaimed == 0:
                logger.info(f"Target: {target.dir}")
                logger.info("NO CHANGE IN SIZE")
            else:
                status = "DELETED" if not target.dir.exists() else f"REDUCED TO {format_du_style(target.after_size)}"
                logger.info(f"Target: {target.dir}")
                logger.info(f"  {format_du_style(target.before_size)} -> {status} (Saved {format_du_style(reclaimed)})")

        total_reclaimed_bytes = self.tracker.get_space_reclaimed_total()
        self.cleanup_result = CleanupResult(bytes_reclaimed=total_reclaimed_bytes, success=True, logs=[])
        return self.cleanup_result

    def _get_mvn_target_dirs(self, limit_bytes: int):
        # Using rglob to find all target folders
        for p in DEVELOPMENT_ROOT.rglob("target"):
            if p.is_dir():
                size = FileUtils.get_dir_size(p)
                if size >= limit_bytes:
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
    summary_name = "ASDF Golang cleanup"

    def __init__(self, keep_versions: List[str], interactive: bool = True):
        super().__init__(interactive=interactive)
        self.keep_versions = keep_versions
        self.tracker = CleanupDetailsTracker()

    def _has_pending_work(self) -> bool:
        if self.tracker.unnamed_cleanup:
            return True
        try:
            return self.tracker.get_before_size("go_caches") > 0
        except ValueError:
            return False

    def _confirmation_prompt(self) -> str:
        versions = [d.metadata["version"] for d in self.tracker.unnamed_cleanup]
        if versions:
            return f"Proceed with uninstalling Go {', '.join(versions)} and cleaning caches? (y/n): "
        return "Proceed with Go cache cleanup? (y/n): "

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

        for key, description in [
            ("go_caches", "go cache and modcache"),
            ("asdf_golang_root", "ASDF golang root"),
            (CleanupDetailsTracker.TOTAL_KEY, "ASDF Golang cleanup total"),
        ]:
            logger.info(
                "%s: before %s, after %s",
                description,
                format_du_style(self.tracker.get_before_size(key)),
                format_du_style(self.tracker.get_after_size(key)),
            )
            logger.info(
                "%s: %s disk space reclaimed",
                description,
                format_du_style(self.tracker.get_space_reclaimed_for_named_cleanup(key)),
            )

        logger.info(
            "Removed Go versions: %s disk space reclaimed",
            format_du_style(self.tracker.get_space_reclaimed_for_unnamed_cleanup()),
        )
        total_reclaimed = self.tracker.get_space_reclaimed_for_named_cleanup(CleanupDetailsTracker.TOTAL_KEY)
        self.cleanup_result = CleanupResult(total_reclaimed, True, [])
        return self.cleanup_result


class _DockerPruneMixin:
    """Shared Docker daemon checks and prune output parsing."""

    _docker_available: bool
    _bytes_reclaimed: int
    _prune_failed: bool

    def _init_docker_prune_state(self) -> None:
        self._docker_available = True
        self._bytes_reclaimed = 0
        self._prune_failed = False

    def _check_docker(self) -> bool:
        try:
            self.run_command_check_output(["docker", "info", "--format", "{{.ServerVersion}}"])
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            logger.error("Docker is not available: %s", exc)
            self._docker_available = False
            return False

    def _run_prune(self, cmd: List[str]) -> int:
        full_cmd = " ".join(cmd)
        logger.debug("Executing: %s", full_cmd)
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        except subprocess.CalledProcessError as exc:
            logger.error("Docker prune failed (%s): %s", exc.returncode, full_cmd)
            self._prune_failed = True
            if exc.output:
                for line in exc.output.splitlines():
                    logger.debug("[Subprocess] %s", line)
            return 0

        for line in output.splitlines():
            logger.debug("[Subprocess] %s", line)
        return self._parse_total_reclaimed(output)

    @staticmethod
    def _parse_total_reclaimed(output: str) -> int:
        reclaimed = 0
        for line in output.splitlines():
            match = re.search(r"Total reclaimed space:\s*(.+)$", line)
            if match:
                reclaimed += humanfriendly.parse_size(match.group(1).strip())
        return reclaimed


class DockerCleanup(CleanupTool, _DockerPruneMixin):
    """Remove unused dangling images, then unused images older than a time limit."""

    summary_name = "Docker images cleanup"

    IMAGE_FORMAT = "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}\t{{.Size}}"
    DEFAULT_TIME_LIMIT = "1440h"  # ~60 days; Go duration (h=hours, not calendar months)

    def __init__(self, time_limit: str = DEFAULT_TIME_LIMIT, interactive: bool = True):
        super().__init__(interactive=interactive)
        self._init_docker_prune_state()
        self.time_limit = time_limit
        self.until_filter = f"until={time_limit}"
        self._dangling_ids: List[str] = []
        self._old_ids: List[str] = []
        self._has_work = False

    def _has_pending_work(self) -> bool:
        return self._docker_available and self._has_work

    def prepare(self):
        logger.info("--- Docker image cleanup ---")
        logger.info("Policy:")
        logger.info("  1. Remove all unused dangling images (any age)")
        logger.info(f"  2. Remove unused images older than {self.time_limit} (tagged and untagged)")

        if not self._check_docker():
            return

        self._dangling_ids = self._list_image_ids(["dangling=true"])
        logger.info("--- DRY RUN (step 1): unused dangling images ---")
        if not self._dangling_ids:
            logger.info("(none)")
        else:
            self._log_images_table(["dangling=true"])

        self._old_ids = self._list_image_ids([self.until_filter])
        logger.info(f"--- DRY RUN (step 2): images older than {self.time_limit} ---")
        logger.info("(Unused only at deletion; images referenced by containers are kept.)")
        if not self._old_ids:
            logger.info("(none matching age filter)")
        else:
            self._log_images_table([self.until_filter])

        self._has_work = bool(self._dangling_ids or self._old_ids)
        if not self._has_work:
            logger.info("Nothing to clean up.")

    def execute(self):
        if not self._docker_available:
            logger.info("Skipping Docker deletion (daemon unavailable).")
            self._execute_skipped = True
            return

        if not self._has_work:
            logger.info("Skipping Docker deletion (nothing to clean up).")
            self._execute_skipped = True
            return

        logger.info("--- DELETING (step 1): unused dangling images ---")
        self._bytes_reclaimed += self._run_prune(["docker", "image", "prune", "--force", "--verbose"])

        logger.info(f"--- DELETING (step 2): unused images older than {self.time_limit} ---")
        self._bytes_reclaimed += self._run_prune(
            ["docker", "image", "prune", "--all", "--force", "--filter", self.until_filter, "--verbose"]
        )

    def verify(self) -> CleanupResult:
        success = self._docker_available and not self._prune_failed
        self.cleanup_result = CleanupResult(self._bytes_reclaimed, success, [])
        return self.cleanup_result

    def print_summary(self) -> None:
        if not self._docker_available:
            logger.info("%s: skipped (daemon unavailable)", self._summary_label())
            return
        super().print_summary()

    def _list_image_ids(self, filters: List[str]) -> List[str]:
        cmd = ["docker", "images", "-q"]
        for image_filter in filters:
            cmd.extend(["--filter", image_filter])
        try:
            output, _ = self.run_command_check_output(cmd)
        except subprocess.CalledProcessError as exc:
            logger.error("Failed to list Docker images: %s", exc)
            self._docker_available = False
            return []
        return [line for line in output.splitlines() if line.strip()]

    def _log_images_table(self, filters: List[str]) -> None:
        cmd = ["docker", "images", "--format", self.IMAGE_FORMAT]
        for image_filter in filters:
            cmd.extend(["--filter", image_filter])
        output, _ = self.run_command_check_output(cmd)
        for line in output.splitlines():
            logger.info(line)


class DockerSystemPruneCleanup(CleanupTool, _DockerPruneMixin):
    """
    Aggressive Docker cleanup: all unused images (any age), stopped containers,
    unused networks, and unused volumes.
    """

    summary_name = "Docker system prune"

    SYSTEM_PRUNE_CMD = ["docker", "system", "prune", "-a", "--volumes", "-f"]

    def __init__(self, interactive: bool = True):
        super().__init__(interactive=interactive)
        self._init_docker_prune_state()

    def _has_pending_work(self) -> bool:
        return self._docker_available

    def _confirmation_prompt(self) -> str:
        return "Proceed with 'docker system prune -a --volumes -f'? (y/n): "

    def prepare(self):
        logger.info("--- Docker system prune (aggressive) ---")
        logger.info("Policy: remove ALL unused images (any age), stopped containers, networks, and volumes")
        logger.warning("Unused volumes may contain database or app data. Review before confirming.")

        if not self._check_docker():
            return

        logger.info("--- DRY RUN: current Docker disk usage ---")
        try:
            output, _ = self.run_command_check_output(["docker", "system", "df"])
            for line in output.splitlines():
                logger.info(line)
        except subprocess.CalledProcessError as exc:
            logger.warning("Could not read docker system df: %s", exc)

    def execute(self):
        if not self._docker_available:
            logger.info("Skipping Docker system prune (daemon unavailable).")
            self._execute_skipped = True
            return

        logger.info("--- DELETING: docker system prune -a --volumes ---")
        self._bytes_reclaimed = self._run_prune(self.SYSTEM_PRUNE_CMD)

    def verify(self) -> CleanupResult:
        success = self._docker_available and not self._prune_failed
        self.cleanup_result = CleanupResult(self._bytes_reclaimed, success, [])
        return self.cleanup_result

    def print_summary(self) -> None:
        if not self._docker_available:
            logger.info("%s: skipped (daemon unavailable)", self._summary_label())
            return
        super().print_summary()


class DiscoveryCleanup(CleanupTool):
    """Generic tool to find and delete specific directory patterns."""

    def __init__(self, name, root_path, patterns: List[str], age_days: int = 30, interactive: bool = True):
        super().__init__(interactive=interactive)
        self.name = name
        self.summary_name = name
        self.root_path = Path(root_path)
        self.patterns = patterns
        self.age_days = age_days
        self.tracker = CleanupDetailsTracker()

    def _has_pending_work(self) -> bool:
        return bool(self.tracker.unnamed_cleanup)

    def _confirmation_prompt(self) -> str:
        count = len(self.tracker.unnamed_cleanup)
        return f"Proceed with removing {count} {self.name} director(ies)? (y/n): "

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
        self.cleanup_result = CleanupResult(reclaimed, True, [])
        return self.cleanup_result


class PoetryCacheCleanup(CleanupTool):
    summary_name = "Poetry cache cleanup"

    def __init__(self, interactive: bool = True):
        super().__init__(interactive=interactive)
        self.tracker = CleanupDetailsTracker()

    def _has_pending_work(self) -> bool:
        details = self.tracker._named_cleanup.get("poetry_cache")
        return details is not None and details.before_size > 0

    def _confirmation_prompt(self) -> str:
        return "Proceed with clearing the Poetry cache? (y/n): "

    def prepare(self):
        cache_dir, _ = self.run_command_check_output(["poetry", "config", "cache-dir"])
        self.tracker.register_named_dir("poetry_cache", Path(cache_dir))

    def execute(self):
        _ = self.run_command(["poetry", "cache", "clear", ".", "--all"])

    def verify(self) -> CleanupResult:
        self.tracker.calculate_after_sizes()
        total_reclaimed_bytes = self.tracker.get_space_reclaimed_total()
        self.cleanup_result = CleanupResult(total_reclaimed_bytes, True, [])
        return self.cleanup_result


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


def build_default_tools(interactive: bool, docker_time_limit: str) -> List[CleanupTool]:
    pip_cache_root = Path(os.path.expanduser("~/Library/Caches/pip"))
    return [
        MavenCleanup("100M", interactive=interactive),
        AsdfGolangCleanup(keep_versions=["1.24.11"], interactive=interactive),
        DockerCleanup(time_limit=docker_time_limit, interactive=interactive),
        DockerSystemPruneCleanup(interactive=interactive),
        DiscoveryCleanup("Python Venvs", DEVELOPMENT_ROOT, ["venv", ".venv"], interactive=interactive),
        DiscoveryCleanup("Terraform", DEVELOPMENT_ROOT, [".terraform"], interactive=interactive),
        DiscoveryCleanup("Pip Cache", pip_cache_root, ["*"], interactive=interactive),
        PoetryCacheCleanup(interactive=interactive),
    ]


class ToolRunner:
    @staticmethod
    def run_tools(tools: List[CleanupTool]):
        setup_logging()
        TOOL_OUTPUT_BASEDIR.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting cleanup. Detailed logs: {LOG_FILE_PATH}")
        total_reclaimed = 0
        for tool in tools:
            tool.execute_flow()
            total_reclaimed += tool.reclaimed_bytes()
        logger.info("All tools: %s disk space reclaimed", format_du_style(total_reclaimed))


@click.command()
@click.option(
    "--docker-only",
    is_flag=True,
    help="Run Docker image cleanup only (dangling + age-based prune)",
)
@click.option(
    "--docker-system-prune-only",
    is_flag=True,
    help="Run aggressive Docker system prune (all unused images, containers, networks, volumes)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Run all tools without confirmation prompts (default: prompt before each deletion)",
)
@click.option(
    "--docker-time-limit",
    default=DockerCleanup.DEFAULT_TIME_LIMIT,
    show_default=True,
    help="Docker until= filter duration",
)
def main(docker_only: bool, docker_system_prune_only: bool, force: bool, docker_time_limit: str):
    """Disk cleanup utilities."""
    if docker_only and docker_system_prune_only:
        raise click.UsageError("Use only one of --docker-only or --docker-system-prune-only")

    interactive = not force

    if docker_only:
        tools: List[CleanupTool] = [
            DockerCleanup(time_limit=docker_time_limit, interactive=interactive),
        ]
    elif docker_system_prune_only:
        tools = [DockerSystemPruneCleanup(interactive=interactive)]
    else:
        tools = build_default_tools(interactive, docker_time_limit)
    ToolRunner.run_tools(tools)


if __name__ == "__main__":
    main()
