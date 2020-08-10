#!/usr/bin/python

import argparse
import sys
import datetime as dt
import logging
import os
from enum import Enum

from os.path import expanduser
import datetime
import time
from logging.handlers import TimedRotatingFileHandler

from git import GitCommandError

from git_wrapper import GitWrapper
from utils import FileUtils, PatchUtils

ENV_CLOUDERA_HADOOP_ROOT = 'CLOUDERA_HADOOP_ROOT'
ENV_HADOOP_DEV_DIR = 'HADOOP_DEV_DIR'

# Do not leak bad ENV variable namings into the python code
LOADED_ENV_UPSTREAM_DIR="upstream-hadoop-dir"
LOADED_ENV_DOWNSTREAM_DIR="downstream-hadoop-dir"

LOG = logging.getLogger(__name__)

__author__ = 'Szilard Nemeth'

PROJECT_NAME="yarn_dev_func"


class CommandType(Enum):
    SAVE_PATCH = 'save_patch'


class Setup:
    @staticmethod
    def init_logger(log_dir, console_debug=False):
        # get root logger
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        # create file handler which logs even debug messages
        logfilename = datetime.datetime.now().strftime(
            'yarn_dev_func-%Y_%m_%d_%H%M%S.log')

        fh = TimedRotatingFileHandler(os.path.join(log_dir, logfilename), when='midnight')
        fh.suffix = '%Y_%m_%d.log'
        fh.setLevel(logging.DEBUG)

        # create console handler with a higher log level
        ch = logging.StreamHandler(stream=sys.stdout)
        ch.setLevel(logging.INFO)
        if console_debug:
            ch.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        # add the handlers to the logger
        logger.addHandler(fh)
        logger.addHandler(ch)

    @staticmethod
    def parse_args():
        """This function parses and return arguments passed in"""

        # Top-level parser
        parser = argparse.ArgumentParser()

        # Subparsers
        subparsers = parser.add_subparsers(title='subcommands', description='valid subcommands', help='bla', required=True, dest='test')

        # Parser 1: save_patch command
        save_patch_parser = subparsers.add_parser('save_patch', help='Saves patch from upstream repository to yarn patches dir')
        save_patch_parser.set_defaults(command=CommandType.SAVE_PATCH)

        # Normal arguments
        parser.add_argument('-v', '--verbose', action='store_true',
                            dest='verbose', default=None, required=False,
                            help='More verbose log')

        args = parser.parse_args()
        return args


class YarnDevFunc:
    def __init__(self, args):
        self.env = {}
        self.setup_dirs()
        self.init_repos()

    def setup_dirs(self):
        home = expanduser("~")
        self.project_out_root = os.path.join(home, PROJECT_NAME)
        self.log_dir = os.path.join(self.project_out_root, 'logs')
        self.yarn_patch_dir = os.path.join(home, 'yarn-tasks')
        FileUtils.ensure_dir_created(self.project_out_root)
        FileUtils.ensure_dir_created(self.log_dir)
        FileUtils.ensure_dir_created(self.yarn_patch_dir)

    def ensure_required_env_vars_are_present(self):
        import os
        upstream_hadoop_dir = os.environ[ENV_HADOOP_DEV_DIR]
        downstream_hadoop_dir = os.environ[ENV_CLOUDERA_HADOOP_ROOT]

        if not upstream_hadoop_dir:
            raise ValueError("Upstream hadoop dir (env var: {}) is not set!".format(ENV_HADOOP_DEV_DIR))
        if not downstream_hadoop_dir:
            raise ValueError("Downstream hadoop dir (env var: {}) is not set!".format(ENV_CLOUDERA_HADOOP_ROOT))

        # Verify if dirs are created
        FileUtils.verify_if_dir_is_created(downstream_hadoop_dir)
        FileUtils.verify_if_dir_is_created(upstream_hadoop_dir)

        self.env = {
            LOADED_ENV_DOWNSTREAM_DIR: downstream_hadoop_dir,
            LOADED_ENV_UPSTREAM_DIR: upstream_hadoop_dir
        }

    def init_repos(self):
        self.ensure_required_env_vars_are_present()
        self.downstream_repo = GitWrapper(self.env[LOADED_ENV_DOWNSTREAM_DIR])
        self.upstream_repo = GitWrapper(self.env[LOADED_ENV_UPSTREAM_DIR])

    def save_patch(self):
        # TODO add force mode: ignore whitespace issues and make backup of patch!
        # TODO add another mode: Create patch based on changes in state, not commits
        curr_branch = self.upstream_repo.get_current_branch_name()
        LOG.info("Current branch: %s", curr_branch)

        if curr_branch == "trunk":
            raise ValueError("Cannot make patch, current branch is trunk. Please use a different branch!")
        patch_branch = curr_branch

        # TODO if there's no commit between trunk..branch, don't run forward
        # TODO check if git is clean (no modified, unstaged files, etc)
        self.upstream_repo.checkout_branch('trunk')
        self.upstream_repo.pull('origin')
        self.upstream_repo.checkout_previous_branch()
        rebase_result = self.upstream_repo.rebase('trunk')
        if not rebase_result:
            raise ValueError("Rebase was not successful, see previous error messages")

        self.upstream_repo.diff_check()
        # TODO add line length check to added lines, ignore imports: 'sed -n "/^+.\{81\}/p"'

        patch_dir = os.path.join(self.yarn_patch_dir, patch_branch)
        FileUtils.ensure_dir_created(patch_dir)
        found_patches = FileUtils.find_files(patch_dir, regex=patch_branch + '\\.\\d.*\\.patch$', single_level=True)
        new_patch_filename, new_patch_num = PatchUtils.get_next_filename(patch_dir, found_patches)

        # Double-check new filename vs. putting it altogether manually
        new_patch_filename_sanity = os.path.join(self.yarn_patch_dir, patch_branch, patch_branch + "." + str(new_patch_num) + ".patch")

        # If this is a new patch, use the appended name,
        # Otherwise, use the generated filename
        if new_patch_num == "001":
            new_patch_filename = new_patch_filename_sanity
        if new_patch_filename != new_patch_filename_sanity:
            raise ValueError("File paths does not match. Calculated: {}, Concatenated: {}".format(new_patch_filename, new_patch_filename_sanity))

        diff = self.upstream_repo.diff('trunk')

        # Save diff patch to file
        if not diff or diff == "":
            LOG.warning("Diff was empty. Patch file is not created!")
            return
        else:
            diff += os.linesep
            LOG.info("Saving diff to patch file: %s", new_patch_filename)
            LOG.debug("Diff: %s", diff)
            FileUtils.save_to_file(new_patch_filename, diff)

        LOG.info("Created patch file: %s [ size: %s ]", new_patch_filename, FileUtils.get_file_size(new_patch_filename))

        # TODO replacing all whitespaces in patch file caused issues when patch applied -> Find a python lib for this
        # sed -i 's/^\([+-].*\)[ \t]*$/\1/' $PATCH_FILE

        # Sanity check: try to apply patch
        self.upstream_repo.checkout_branch('trunk')

        LOG.info("Trying to apply patch %s", new_patch_filename)
        result = self.upstream_repo.apply_check(new_patch_filename)
        if not result:
            raise ValueError("Patch does not apply to trunk! Patch file: %s", new_patch_filename)
        else:
            LOG.info("Patch file applies cleanly to trunk. Patch file: %s", new_patch_filename)

        # Checkout old branch
        self.upstream_repo.checkout_previous_branch()


if __name__ == '__main__':
    start_time = time.time()

    # Parse args
    args = Setup.parse_args()
    verbose = args.verbose
    if verbose:
        print("Args: " + str(args))

    yarn_functions = YarnDevFunc(args)
    yarn_functions.init_repos()

    # Initialize logging
    # verbose = True if args.verbose else False
    Setup.init_logger(yarn_functions.log_dir, console_debug=False)

    command = args.command
    if command == CommandType.SAVE_PATCH:
        yarn_functions.save_patch()


    end_time = time.time()
    #LOG.info("Execution of script took %d seconds", end_time - start_time)
