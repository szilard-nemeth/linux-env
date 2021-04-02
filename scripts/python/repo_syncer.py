#!/usr/bin/python3

import logging
import os
from typing import Dict, Tuple, List

from git import Repo
from pythoncommons.file_utils import FileUtils
from yarndevtools.git_wrapper import GitWrapper, ProgressPrinter

GIT_DIR_NAME = ".git"

LOG = logging.getLogger(__name__)

BASEDIR_PLACEHOLDER = "$$BASEDIR$$"
DELIM = ";"
REPO_LIST_FILE = "repo_list.csv"
HTTPS_PREFIX = "https://"
HTTP_PREFIX = "http://"
ENV_MY_REPOS_DIR = "MY_REPOS_DIR"
DEFAULT_TARGET_DIR = "DEFAULT_DIR"
ORIGIN_MASTER = "origin/master"
ORIGIN_MAIN = "origin/main"


def sync():
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    # TODO move env checker to Pythoncommons
    my_repos_dir = os.environ[ENV_MY_REPOS_DIR] if ENV_MY_REPOS_DIR in os.environ else None
    if not my_repos_dir:
        raise ValueError(f"My repositories dir (env var: {ENV_MY_REPOS_DIR}) is not set!")

    script_dir = FileUtils.get_parent_dir_name(__file__)
    repo_list_abs_path = FileUtils.join_path(script_dir, REPO_LIST_FILE)
    LOG.info(f"Reading repo list from file: {repo_list_abs_path}")
    lines = FileUtils.read_file(repo_list_abs_path)
    lines = lines.splitlines()

    repo_dict = create_repo_dict_from_file(lines)

    dirty_repos: List[str] = []
    failed_to_checkout_branch_repos: List[str] = []
    for line, (repo_url, target_dir) in repo_dict.items():
        repo_url, repo_name = validate_repo_url_and_name(repo_url)
        if not repo_url or not repo_name:
            LOG.error(f"Uncrecognized repo URL: {repo_url}. Original line was: '{line}'. Skipping this line.")
            continue

        if target_dir == DEFAULT_TARGET_DIR:
            final_target_dir = FileUtils.join_path(my_repos_dir, repo_name)
        else:
            final_target_dir = FileUtils.join_path(get_dir_name_from_field(target_dir, basedir=my_repos_dir), repo_name)

        repo_git_dir = FileUtils.join_path(final_target_dir, GIT_DIR_NAME)
        if not FileUtils.is_dir(repo_git_dir, throw_ex=False):
            LOG.info(f"Cloning from {repo_url} to dir: {final_target_dir}")
            Repo.clone_from(repo_url, final_target_dir, progress=ProgressPrinter("clone"))
        else:
            LOG.info(f"Fetching from {repo_url} to dir: {final_target_dir}")
            gw = GitWrapper(final_target_dir)
            gw.fetch(all=True)
            if gw.is_working_directory_clean():
                LOG.info(f"Trying to checkout default branch: {ORIGIN_MASTER}")
                if gw.is_branch_exist(ORIGIN_MASTER):
                    gw.checkout_branch(ORIGIN_MASTER)
                else:
                    LOG.info(f"Trying to checkout branch: {ORIGIN_MAIN}")
                    if gw.is_branch_exist(ORIGIN_MAIN):
                        gw.checkout_branch(ORIGIN_MAIN)
                    else:
                        failed_to_checkout_branch_repos.append(final_target_dir)

            else:
                dirty_repos.append(final_target_dir)

    exit_code = 0
    if len(dirty_repos) > 0:
        LOG.error("Working directory is not clean for the following repos. Please clean them and re-run the script!")
        for repo in dirty_repos:
            LOG.error(repo)
        exit_code += 1

    if len(failed_to_checkout_branch_repos) > 0:
        branches = [ORIGIN_MASTER, ORIGIN_MAIN]
        LOG.error(
            f"Failed to checkout any of the branches of '{branches}' for the following repos. Please check them and re-run the script!"
        )
        for repo in failed_to_checkout_branch_repos:
            LOG.error(repo)
        exit_code += 2

    if exit_code == 0:
        LOG.info("All good :)")

    exit(exit_code)


def create_repo_dict_from_file(lines):
    # Key: line
    # Value: Tuple of <repo URL, target dir>
    repo_dict: Dict[str, Tuple[str, str]] = {}
    for line in lines:
        if DELIM in line:
            fields = line.split(DELIM)
            if len(fields) > 2:
                raise ValueError("Only 2 fields are supported. Line should look like: REPO_URL;<OPTIONAL BASE PATH>")
            if not fields[0]:
                raise ValueError(f"Invalid repo value URL in: {line}")
            if not fields[1]:
                raise ValueError(f"Invalid basedir value in: {line}")
            add_to_repo_dict(repo_dict, line, fields[0], fields[1])
        else:
            add_to_repo_dict(repo_dict, line, line, DEFAULT_TARGET_DIR)
    return repo_dict


def add_to_repo_dict(d, line, repo_url, target_dir):
    if not line:
        LOG.error(f"Skipping empty line: '{line}'")
        return

    if line in d:
        LOG.warning(f"Line is already added to dict: {line}. Skipping this one.")
        return

    d[line] = (repo_url, target_dir)


def get_dir_name_from_field(field, basedir):
    if BASEDIR_PLACEHOLDER in field:
        return field.replace(BASEDIR_PLACEHOLDER, basedir)
    else:
        return field


def validate_repo_url_and_name(repo_url):
    if not repo_url.lower().startswith((HTTP_PREFIX, HTTPS_PREFIX)):
        return None, None
    parts = repo_url.rsplit("/")
    if len(parts) == 0:
        raise ValueError(f"Invalid repo URL: {repo_url}")
    repo_name = repo_url.rsplit("/")[-1]
    return repo_url, repo_name


if __name__ == "__main__":
    sync()
