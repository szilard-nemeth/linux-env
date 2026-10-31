#!/usr/bin/env python3

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class RepoSetup:
    setup_type: Optional[str]
    command: Optional[str]
    dockerfile: Optional[str]
    docker_context: Optional[str]
    image: Optional[str]
    container: Optional[str]
    run_args: Optional[str]
    run_args_env: Optional[str]


@dataclass(frozen=True)
class RepoConfig:
    repo_id: str
    url: Optional[str]
    repo_dir: Optional[str]
    ref: Optional[str]
    sparse_paths: List[str]
    setup: RepoSetup


_START = time.monotonic()

# Set to 1 to always 'git fetch', even when the pinned ref is already present locally.
FORCE_FETCH_ENV = "EXTERNAL_REPOS_FORCE_FETCH"


def _log(*args) -> None:
    """print() with a wall-clock timestamp and the seconds elapsed since the script started."""
    stamp = time.strftime("%H:%M:%S") + f".{int(time.time() * 1000) % 1000:03d}"
    print(f"[{stamp} +{time.monotonic() - _START:6.3f}s]", *args, flush=True)


def _run(cmd: List[str], cwd: Optional[str] = None, check: bool = False, **kwargs) -> subprocess.CompletedProcess:
    """subprocess.run() that logs the command and how long it took."""
    _log("Running:", shlex.join(cmd))
    started = time.monotonic()
    result = subprocess.run(cmd, cwd=cwd, check=False, **kwargs)
    _log(f"  done in {time.monotonic() - started:.3f}s (rc={result.returncode})")
    if check:
        result.check_returncode()
    return result


def _run_command(
    cmd: List[str], cwd: Optional[str] = None, check: bool = True, stdout=None, stderr=None
) -> subprocess.CompletedProcess:
    return _run(cmd, cwd=cwd, check=check, stdout=stdout, stderr=stderr)


def _run_capture(cmd: List[str], cwd: Optional[str] = None) -> str:
    return _run(cmd, cwd=cwd, capture_output=True, text=True).stdout.strip()


def _expand(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return os.path.expandvars(os.path.expanduser(value))


def _config_path() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    default_path = repo_root / "config" / "external-repos.json"
    return Path(os.environ.get("EXTERNAL_REPOS_CONFIG", str(default_path)))


def _load_config() -> dict:
    config_path = _config_path()
    if not config_path.exists():
        raise FileNotFoundError(f"External repo config not found: {config_path}")
    with config_path.open() as handle:
        return json.load(handle)


def _repo_ids(config: dict, requested: List[str]) -> List[str]:
    if requested:
        return requested
    return config.get("ids") or list(config.get("repos", {}).keys())


def _normalize_sparse_paths(value: Optional[Iterable[str] | str]) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [part for part in value.split() if part]
    return [str(part) for part in value]


def _normalize_sparse_paths_for_no_cone(paths: List[str]) -> List[str]:
    normalized = []
    for path in paths:
        if not path:
            continue
        if path.startswith("/"):
            normalized.append(path)
        else:
            normalized.append(f"/{path}")
    return normalized


def _repo_setup(repo: dict) -> RepoSetup:
    setup = repo.get("setup") or {}
    return RepoSetup(
        setup_type=setup.get("type"),
        command=setup.get("command") or setup.get("cmd"),
        dockerfile=setup.get("dockerfile"),
        docker_context=setup.get("context") or setup.get("docker_context"),
        image=setup.get("image"),
        container=setup.get("container"),
        run_args=setup.get("run_args"),
        run_args_env=setup.get("run_args_env"),
    )


def _repo_config(repo_id: str, repo: dict) -> RepoConfig:
    setup = _repo_setup(repo)
    return RepoConfig(
        repo_id=repo_id,
        url=_expand(repo.get("url")),
        repo_dir=_expand(repo.get("dir")),
        ref=_expand(repo.get("ref")),
        sparse_paths=_normalize_sparse_paths(repo.get("sparse_paths")),
        setup=RepoSetup(
            setup_type=setup.setup_type,
            command=_expand(setup.command) if setup.command else None,
            dockerfile=_expand(setup.dockerfile),
            docker_context=_expand(setup.docker_context),
            image=_expand(setup.image),
            container=_expand(setup.container),
            run_args=_expand(setup.run_args),
            run_args_env=setup.run_args_env,
        ),
    )


def _is_commit_sha(ref: Optional[str]) -> bool:
    return bool(ref) and len(ref) == 40 and all(c in "0123456789abcdef" for c in ref.lower())


def _resolve_commit(repo: RepoConfig) -> Optional[str]:
    """Return the commit SHA repo.ref points to in the local clone, or None if it is not present."""
    result = _run(
        ["git", "-C", repo.repo_dir, "rev-parse", "--verify", "--quiet", f"{repo.ref}^{{commit}}"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _ensure_sparse_checkout(repo: RepoConfig) -> None:
    """Apply repo.sparse_paths, unless the clone already has exactly these patterns."""
    no_cone_paths = _normalize_sparse_paths_for_no_cone(repo.sparse_paths)
    enabled = _run_capture(["git", "-C", repo.repo_dir, "config", "--get", "core.sparseCheckout"]) == "true"
    current = set(_run_capture(["git", "-C", repo.repo_dir, "sparse-checkout", "list"]).splitlines())
    if enabled and current in (set(repo.sparse_paths), set(no_cone_paths)):
        _log(f"External repo '{repo.repo_id}' sparse-checkout already configured; skipping")
        return

    _run_command(["git", "-C", repo.repo_dir, "sparse-checkout", "init", "--cone"])
    try:
        _run_command(["git", "-C", repo.repo_dir, "sparse-checkout", "set", *repo.sparse_paths])
    except subprocess.CalledProcessError:
        _run_command(["git", "-C", repo.repo_dir, "sparse-checkout", "set", "--no-cone", *no_cone_paths])


def _sync_repo(repo: RepoConfig) -> None:
    if not repo.url or not repo.repo_dir:
        _log(f"External repo '{repo.repo_id}' missing url or dir; skipping")
        return

    repo_path = Path(repo.repo_dir)
    if not (repo_path / ".git").exists():
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        _run_command(["git", "clone", repo.url, repo.repo_dir])

    if repo.sparse_paths:
        _ensure_sparse_checkout(repo)

    # A pinned commit SHA never moves, so once it is present locally there is nothing to fetch.
    # Branch/tag refs can move, so those are always fetched.
    target = _resolve_commit(repo) if repo.ref else None
    if _is_commit_sha(repo.ref) and target and not os.environ.get(FORCE_FETCH_ENV):
        _log(
            f"Pinned commit {repo.ref[:12]} already present locally; skipping fetch (set {FORCE_FETCH_ENV}=1 to force)"
        )
    else:
        _run_command(["git", "-C", repo.repo_dir, "fetch", "--all", "--tags", "--prune"])
        target = _resolve_commit(repo) if repo.ref else None

    if repo.ref:
        if target and target == _run_capture(["git", "-C", repo.repo_dir, "rev-parse", "HEAD"]):
            _log(f"External repo '{repo.repo_id}' is already at {repo.ref[:12]}; skipping checkout")
            return
        status = _run_capture(["git", "-C", repo.repo_dir, "status", "--porcelain"])
        if status:
            _log(f"External repo '{repo.repo_id}' has local changes; skipping checkout")
            return
        _run_command(["git", "-C", repo.repo_dir, "checkout", "--detach", repo.ref])


def _ensure_repo(repo: RepoConfig) -> None:
    """Clone the repo if it is missing (no fetch/checkout otherwise), then print its dir on stdout.

    Meant for shell callers: `dir=$(external-repos.py ensure <id>)`. Progress output goes to stderr
    so stdout carries only the path.
    """
    if not repo.repo_dir:
        raise ValueError(f"External repo '{repo.repo_id}' has no dir configured")
    if not (Path(repo.repo_dir) / ".git").exists():
        with contextlib.redirect_stdout(sys.stderr):
            _sync_repo(repo)
    print(repo.repo_dir)


def get_repo_config_prefix(repo: RepoConfig) -> str:
    return f"External repo config: '{repo.repo_id}' //"


def print_prefixed(repo: RepoConfig, s: str):
    prefix = get_repo_config_prefix(repo)
    _log(f"{prefix}{s}")


def _docker_image_built_commit(image: str) -> Optional[str]:
    """Return the git-commit label baked into an existing image, or None if the image does not exist."""
    result = _run(
        ["docker", "image", "inspect", "--format", '{{index .Config.Labels "git-commit"}}', image],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _docker_image_id(image: str) -> Optional[str]:
    """Return the full image ID for the given image name/tag, or None if it does not exist."""
    result = _run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _docker_container_image_id(container: str) -> Optional[str]:
    """Return the image ID that a container (running or stopped) was created from, or None."""
    result = _run(
        ["docker", "inspect", "--format", "{{.Image}}", container],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _docker_build(repo: RepoConfig, current_commit: Optional[str]) -> None:
    setup = repo.setup
    cmd = [
        "docker",
        "build",
        "-f",
        f"{repo.repo_dir}/{setup.dockerfile}",
        "-t",
        setup.image,
    ]
    if current_commit:
        cmd += ["--label", f"git-commit={current_commit}"]
    cmd.append(f"{repo.repo_dir}/{setup.docker_context}")
    _run_command(cmd)


def _docker_ensure_running(repo: RepoConfig) -> None:
    _log("Ensuring Docker is running...")
    if shutil.which("docker") is None:
        _log(f"docker not available; skipping {repo.repo_id}")
        return

    if (
        _run_command(["docker", "info"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
        != 0
    ):
        _log(f"Docker daemon is not running; skipping {repo.repo_id}")
        return

    setup = repo.setup
    container = setup.container
    if not setup.dockerfile or not setup.docker_context or not setup.image or not container:
        _log(f"Missing docker settings for external repo '{repo.repo_id}'; skipping")
        return

    run_args = setup.run_args
    if setup.run_args_env:
        run_args = os.environ.get(setup.run_args_env, run_args)

    # Determine the commit the repo is currently at (may be None for non-git repos).
    current_commit: Optional[str] = None
    if repo.repo_dir and (Path(repo.repo_dir) / ".git").exists():
        current_commit = _run_capture(["git", "-C", repo.repo_dir, "rev-parse", "HEAD"]) or None

    built_commit = _docker_image_built_commit(setup.image)

    image_rebuilt = False
    if built_commit is None:
        print_prefixed(repo, f"Docker image '{setup.image}' is not built! Building...")
        _docker_build(repo, current_commit)
        image_rebuilt = True
    elif current_commit and built_commit != current_commit:
        print_prefixed(
            repo,
            f"Docker image '{setup.image}' was built at {built_commit[:12]}, "
            f"but repo is at {current_commit[:12]}. Rebuilding...",
        )
        _docker_build(repo, current_commit)
        image_rebuilt = True
    else:
        print_prefixed(
            repo,
            f"Docker image '{setup.image}' is up to date (commit {(current_commit or built_commit or 'unknown')[:12]})",
        )

    # If the image was just rebuilt, tear down any existing container so it is
    # recreated from the new image below.
    if image_rebuilt:
        all_containers = _run_capture(["docker", "ps", "-a", "--format", "{{.Names}}"]).splitlines()
        if container in all_containers:
            print_prefixed(repo, f"Stopping and removing stale container '{container}' after image rebuild...")
            _run_command(["docker", "stop", container])
            _run_command(["docker", "rm", container])

    # Check whether the container (running or stopped) is using the current image.
    # This catches the case where the image was rebuilt in a previous run but the
    # container was never restarted.
    current_image_id = _docker_image_id(setup.image)
    container_image_id = _docker_container_image_id(container)
    if current_image_id and container_image_id and current_image_id != container_image_id:
        print_prefixed(
            repo,
            f"Container '{container}' is using a stale image; stopping and removing it...",
        )
        _run_command(["docker", "stop", container], check=False)
        _run_command(["docker", "rm", container])

    running = _run_capture(["docker", "ps", "--format", "{{.Names}}"]).splitlines()
    if container in running:
        print_prefixed(repo, f"Docker container '{container}' is already running; skipping")
        return

    stopped = _run_capture(["docker", "ps", "-a", "--format", "{{.Names}}"]).splitlines()
    if container in stopped:
        _run_command(["docker", "start", container])
        return

    run_cmd = ["docker", "run", "-d", "--name", container]
    if run_args:
        run_cmd.extend(shlex.split(run_args))
    run_cmd.append(setup.image)
    _run_command(run_cmd)


def _setup_repo(repo: RepoConfig) -> None:
    setup = repo.setup
    if not setup.setup_type and not setup.command:
        return

    if setup.setup_type == "docker-ensure-running":
        _docker_ensure_running(repo)
        return
    if setup.command:
        _log(f"Warning! Unknown setup type '{setup.setup_type}'. Running setup command: {setup.command}")
        subprocess.run(setup.command, cwd=repo.repo_dir, shell=True, check=True)
    else:
        raise ValueError(f"Unknown setup type '{setup.setup_type}' and setup command is not set!")


def _load_repos(config: dict, repo_ids: List[str]) -> List[RepoConfig]:
    repos = config.get("repos", {})
    result = []
    for repo_id in repo_ids:
        repo = repos.get(repo_id)
        if not repo:
            _log(f"External repo '{repo_id}' not found in config; skipping")
            continue
        result.append(_repo_config(repo_id, repo))
    return result


def _sync(repos: List[RepoConfig]) -> None:
    for repo in repos:
        _log("Syncing repo: " + repo.repo_id)
        _sync_repo(repo)


def _setup(repos: List[RepoConfig]) -> None:
    for repo in repos:
        _log("Setting up repo: " + repo.repo_id)
        _setup_repo(repo)


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage external repos.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("sync", "setup", "sync-and-setup", "ensure"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("ids", nargs="*", help="Optional repo ids")

    args = parser.parse_args()
    config = _load_config()
    repo_ids = _repo_ids(config, args.ids)
    repos = _load_repos(config, repo_ids)

    if args.command == "sync":
        _sync(repos)
    elif args.command == "setup":
        _setup(repos)
    elif args.command == "sync-and-setup":
        _sync(repos)
        _setup(repos)
    elif args.command == "ensure":
        for repo in repos:
            _ensure_repo(repo)
    else:
        parser.error(f"Unknown command {args.command}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
