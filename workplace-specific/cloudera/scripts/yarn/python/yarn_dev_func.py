#!/usr/bin/python

import sys
import logging
import os

from os.path import expanduser
import datetime
import time
from logging.handlers import TimedRotatingFileHandler

from git import InvalidGitRepositoryError

from argparser import ArgParser
from command_runner import CommandRunner
from commands.backporter import Backporter
from commands.format_patch_saver import FormatPatchSaver
from commands.upstream_jira_umbrella_fetcher import UpstreamJiraUmbrellaFetcher
from commands.review_branch_creator import ReviewBranchCreator
from commands.upstream_jira_patch_differ import UpstreamJiraPatchDiffer
from commands.upstream_pr_fetcher import UpstreamPRFetcher
from git_wrapper import GitWrapper
from commands.patch_saver import PatchSaver
from utils import FileUtils, PatchUtils, StringUtils, DateTimeUtils, auto_str, JiraUtils
from constants import *

LOG = logging.getLogger(__name__)
__author__ = 'Szilard Nemeth'


class Setup:
    @staticmethod
    def init_logger(log_dir, console_debug=False, postfix=""):
        # get root logger
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        # create file handler which logs even debug messages
        prefix = 'yarn_dev_func-{postfix}-'.format(postfix=postfix)
        logfilename = datetime.datetime.now().strftime(prefix + '%Y_%m_%d_%H%M%S.log')

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


class YarnDevFunc:
    def __init__(self):
        self.env = {}
        self.downstream_repo = None
        self.upstream_repo = None
        self.project_out_root = None
        self.log_dir = None
        self.yarn_patch_dir = None
        self.setup_dirs()
        self.init_repos()

    def setup_dirs(self):
        home = expanduser("~")
        self.project_out_root = os.path.join(home, PROJECT_NAME)
        self.log_dir = os.path.join(self.project_out_root, 'logs')
        self.yarn_patch_dir = os.path.join(home, 'yarn-tasks')
        self.jira_umbrella_data_dir = os.path.join(home, 'jira-umbrella-data')
        self.jira_patch_differ_dir = os.path.join(home, 'jira-patch-differ')
        FileUtils.ensure_dir_created(self.project_out_root)
        FileUtils.ensure_dir_created(self.log_dir)
        FileUtils.ensure_dir_created(self.yarn_patch_dir)
        FileUtils.ensure_dir_created(self.jira_umbrella_data_dir)

    def ensure_required_env_vars_are_present(self):
        import os
        upstream_hadoop_dir = os.environ[ENV_HADOOP_DEV_DIR]
        downstream_hadoop_dir = os.environ[ENV_CLOUDERA_HADOOP_ROOT]

        if not upstream_hadoop_dir:
            raise ValueError("Upstream Hadoop dir (env var: {}) is not set!".format(ENV_HADOOP_DEV_DIR))
        if not downstream_hadoop_dir:
            raise ValueError("Downstream Hadoop dir (env var: {}) is not set!".format(ENV_CLOUDERA_HADOOP_ROOT))

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

    def save_patch(self, args):
        patch_saver = PatchSaver(args, self.upstream_repo, self.yarn_patch_dir)
        return patch_saver.run()

    def create_review_branch(self, args):
        review_branch_creator = ReviewBranchCreator(args, self.upstream_repo)
        review_branch_creator.run()

    def backport_c6(self, args):
        backporter = Backporter(args, self.upstream_repo, self.downstream_repo, 'cauldron/{}'.format(args.cdh_branch))
        backporter.run()

    def upstream_pr_fetch(self, args):
        upstream_pr_fetcher = UpstreamPRFetcher(args, self.upstream_repo, TRUNK)
        upstream_pr_fetcher.run()

    def save_patches(self, args):
        format_patch_saver = FormatPatchSaver(args, os.getcwd(), DateTimeUtils.get_current_datetime())
        format_patch_saver.run()

    def diff_patches_of_jira(self, args):
        """
        THIS SCRIPT ASSUMES EACH PROVIDED BRANCH WITH PARAMETERS (e.g. trunk, 3.2, 3.1) has the given commit committed
        Example workflow:
        1. git log --oneline trunk | grep YARN-10028
        * 13cea0412c1 - YARN-10028. Integrate the new abstract log servlet to the JobHistory server. Contributed by Adam Antal 24 hours ago) <Szilard Nemeth>

        2. git diff 13cea0412c1..13cea0412c1^ > /tmp/YARN-10028-trunk.diff
        3. git checkout branch-3.2
        4. git apply ~/Downloads/YARN-10028.branch-3.2.001.patch
        5. git diff > /tmp/YARN-10028-branch-32.diff
        6. diff -Bibw /tmp/YARN-10028-trunk.diff /tmp/YARN-10028-branch-32.diff
        :param args:
        :return:
        """
        patch_differ = UpstreamJiraPatchDiffer(args, self.upstream_repo, self.jira_patch_differ_dir)
        patch_differ.run()

    def fetch_jira_umbrella_data(self, args):
        jira_umbrella_fetcher = UpstreamJiraUmbrellaFetcher(args, self.upstream_repo, self.jira_umbrella_data_dir)
        jira_umbrella_fetcher.run()


if __name__ == '__main__':
    start_time = time.time()

    # TODO Revisit all exception handling: ValueError vs. exit() calls
    # Methods should throw exceptions, exit should be handled in this method
    yarn_functions = YarnDevFunc()

    # Parse args, commands will be mapped to YarnDevFunc functions in ArgParser.parse_args
    args = ArgParser.parse_args(yarn_functions)
    Setup.init_logger(yarn_functions.log_dir, console_debug=False)

    # Call the handler function
    args.func(args)

    end_time = time.time()
    # TODO make a switch to turn execution time printing on
    # LOG.info("Execution of script took %d seconds", end_time - start_time)
