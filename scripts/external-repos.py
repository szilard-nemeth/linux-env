#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
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


def _run_command(
    cmd: List[str], cwd: Optional[str] = None, check: bool = True, stdout=None, stderr=None
) -> subprocess.CompletedProcess:
    print("Running:", shlex.join(cmd))
    return subprocess.run(cmd, cwd=cwd, check=check, stdout=stdout, stderr=stderr)


def _run_capture(cmd: List[str], cwd: Optional[str] = None) -> str:
    print("Running:", shlex.join(cmd))
    result = subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)
    return result.stdout.strip()


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


def _sync_repo(repo: RepoConfig) -> None:
    if not repo.url or not repo.repo_dir:
        print(f"External repo '{repo.repo_id}' missing url or dir; skipping")
        return

    repo_path = Path(repo.repo_dir)
    if not (repo_path / ".git").exists():
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        _run_command(["git", "clone", repo.url, repo.repo_dir])

    if repo.sparse_paths:
        _run_command(["git", "-C", repo.repo_dir, "sparse-checkout", "init", "--cone"])
        try:
            _run_command(["git", "-C", repo.repo_dir, "sparse-checkout", "set", *repo.sparse_paths])
        except subprocess.CalledProcessError:
            no_cone_paths = _normalize_sparse_paths_for_no_cone(repo.sparse_paths)
            _run_command(["git", "-C", repo.repo_dir, "sparse-checkout", "set", "--no-cone", *no_cone_paths])

    _run_command(["git", "-C", repo.repo_dir, "fetch", "--all", "--tags", "--prune"])

    if repo.ref:
        status = _run_capture(["git", "-C", repo.repo_dir, "status", "--porcelain"])
        if status:
            print(f"External repo '{repo.repo_id}' has local changes; skipping checkout")
            return
        _run_command(["git", "-C", repo.repo_dir, "checkout", "--detach", repo.ref])


def get_repo_config_prefix(repo: RepoConfig) -> str:
    return f"External repo config: '{repo.repo_id}' //"


def print_prefixed(repo: RepoConfig, s: str):
    prefix = get_repo_config_prefix(repo)
    print(f"{prefix}{s}")


def _docker_image_built_commit(image: str) -> Optional[str]:
    """Return the git-commit label baked into an existing image, or None if the image does not exist."""
    result = subprocess.run(
        ["docker", "image", "inspect", "--format", '{{index .Config.Labels "git-commit"}}', image],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _docker_image_id(image: str) -> Optional[str]:
    """Return the full image ID for the given image name/tag, or None if it does not exist."""
    result = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _docker_container_image_id(container: str) -> Optional[str]:
    """Return the image ID that a container (running or stopped) was created from, or None."""
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.Image}}", container],
        check=False,
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
    print("Ensuring Docker is running...")
    if shutil.which("docker") is None:
        print(f"docker not available; skipping {repo.repo_id}")
        return

    if (
        _run_command(["docker", "info"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
        != 0
    ):
        print(f"Docker daemon is not running; skipping {repo.repo_id}")
        return

    setup = repo.setup
    container = setup.container
    if not setup.dockerfile or not setup.docker_context or not setup.image or not container:
        print(f"Missing docker settings for external repo '{repo.repo_id}'; skipping")
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
        print(f"Warning! Unknown setup type '{setup.setup_type}'. Running setup command: {setup.command}")
        subprocess.run(setup.command, cwd=repo.repo_dir, shell=True, check=True)
    else:
        raise ValueError(f"Unknown setup type '{setup.setup_type}' and setup command is not set!")


def _load_repos(config: dict, repo_ids: List[str]) -> List[RepoConfig]:
    repos = config.get("repos", {})
    result = []
    for repo_id in repo_ids:
        repo = repos.get(repo_id)
        if not repo:
            print(f"External repo '{repo_id}' not found in config; skipping")
            continue
        result.append(_repo_config(repo_id, repo))
    return result


def _sync(repos: List[RepoConfig]) -> None:
    for repo in repos:
        print("Syncing repo: " + repo.repo_id)
        _sync_repo(repo)


def _setup(repos: List[RepoConfig]) -> None:
    for repo in repos:
        print("Setting up repo: " + repo.repo_id)
        _setup_repo(repo)


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage external repos.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("sync", "setup", "sync-and-setup"):
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
    else:
        parser.error(f"Unknown command {args.command}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
