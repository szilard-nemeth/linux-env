#!/usr/bin/python3
import argparse
import logging
import os
from pythoncommons.file_utils import FileUtils

ENV_MY_REPOS_DIR = "MY_REPOS_DIR"
LOG = logging.getLogger(__name__)


def parse_args():
    """This function parses and return arguments passed in"""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-ext",
        "--extension",
        type=str,
        dest="extension",
        help="Include only the matching files for name",
        required=False,
    )
    parser.add_argument(
        "-e",
        "--exclude",
        nargs="+",
        type=str,
        dest="excludes",
        help="Exclude the matching dirs for these exclude names. Should be a full dir name",
        required=False,
    )
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", required=False, help="Verbose logging")

    args = parser.parse_args()
    if args.verbose:
        print("args: " + str(args))
    return args


def filtered_find(args):
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    # TODO move env checker to Pythoncommons
    my_repos_dir = os.environ[ENV_MY_REPOS_DIR] if ENV_MY_REPOS_DIR in os.environ else None
    if not my_repos_dir:
        raise ValueError(f"My repositories dir (env var: {ENV_MY_REPOS_DIR}) is not set!")

    ext = args.extension if "extension" in args else None
    found_files = FileUtils.find_files(
        my_repos_dir, full_path_result=True, extension=ext, debug=True, exclude_dirs=args.excludes
    )
    print("\n".join(found_files))


if __name__ == "__main__":
    args = parse_args()
    filtered_find(args)
