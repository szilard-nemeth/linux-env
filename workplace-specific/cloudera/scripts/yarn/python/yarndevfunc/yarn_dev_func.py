#!/usr/bin/python

import sys
import logging
import os

from os.path import expanduser
import datetime
import time
from logging.handlers import TimedRotatingFileHandler

from pythoncommons.date_utils import DateUtils
from pythoncommons.file_utils import FileUtils

from yarndevfunc.commands.branch_comparator import BranchComparator
from yarndevfunc.commands.send_latest_command_data_in_mail import SendLatestCommandDataInEmail
from yarndevfunc.commands.zip_latest_command_data import ZipLatestCommandData
from yarndevfunc.utils import FileUtils2
from yarndevfunc.argparser import ArgParser, CommandType
from yarndevfunc.commands.backporter import Backporter
from yarndevfunc.commands.format_patch_saver import FormatPatchSaver
from yarndevfunc.commands.patch_saver import PatchSaver
from yarndevfunc.commands.review_branch_creator import ReviewBranchCreator
from yarndevfunc.commands.upstream_jira_patch_differ import UpstreamJiraPatchDiffer
from yarndevfunc.commands.upstream_jira_umbrella_fetcher import UpstreamJiraUmbrellaFetcher
from yarndevfunc.commands.upstream_pr_fetcher import UpstreamPRFetcher
from yarndevfunc.constants import (
    PROJECT_NAME,
    ENV_HADOOP_DEV_DIR,
    ENV_CLOUDERA_HADOOP_ROOT,
    LOADED_ENV_DOWNSTREAM_DIR,
    LOADED_ENV_UPSTREAM_DIR,
    TRUNK,
    ORIGIN_TRUNK,
    GERRIT_REVIEWER_LIST,
    HADOOP_REPO_TEMPLATE,
    LATEST_LOG,
    LATEST_SESSION,
    LATEST_DATA_ZIP,
)
from yarndevfunc.git_wrapper import GitWrapper

DEFAULT_BASE_BRANCH = TRUNK

LOG = logging.getLogger(__name__)
__author__ = "Szilard Nemeth"

IGNORE_LATEST_SYMLINK_COMMANDS = {CommandType.ZIP_LATEST_COMMAND_DATA}


class Setup:
    @staticmethod
    def init_logger(log_dir, console_debug=False, postfix="", repos=None, verbose=False):
        # get root logger
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        # create file handler which logs even debug messages
        prefix = f"{PROJECT_NAME}-{postfix}-"
        logfilename = datetime.datetime.now().strftime(prefix + "%Y_%m_%d_%H%M%S.log")

        log_file = FileUtils.join_path(log_dir, logfilename)
        fh = TimedRotatingFileHandler(log_file, when="midnight")
        fh.suffix = "%Y_%m_%d.log"
        fh.setLevel(logging.DEBUG)

        # create console handler with a higher log level
        ch = logging.StreamHandler(stream=sys.stdout)
        ch.setLevel(logging.INFO)
        if console_debug:
            ch.setLevel(logging.DEBUG)

        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        # add the handlers to the logger
        logger.addHandler(fh)
        logger.addHandler(ch)

        # https://gitpython.readthedocs.io/en/stable/tutorial.html#git-command-debugging-and-customization
        # THIS WON'T WORK BECAUSE GITPYTHON MODULE IS LOADED BEFORE THIS CALL
        # os.environ["GIT_PYTHON_TRACE"] = "1"
        # https://github.com/gitpython-developers/GitPython/issues/222#issuecomment-68597780
        LOG.warning("Cannot enable GIT_PYTHON_TRACE because repos list is empty!")
        if repos:
            for repo in repos:
                val = "full" if verbose else "1"
                type(repo.git).GIT_PYTHON_TRACE = val
        return log_file


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
        self.project_out_root = FileUtils.join_path(home, PROJECT_NAME)
        self.log_dir = FileUtils.join_path(self.project_out_root, "logs")
        self.yarn_patch_dir = FileUtils.join_path(home, "yarn-tasks")
        self.jira_umbrella_data_dir = FileUtils.join_path(home, "jira-umbrella-data")
        self.jira_patch_differ_dir = FileUtils.join_path(home, "jira-patch-differ")
        self.branch_comparator_output_dir = FileUtils.join_path(home, "branch-comparator")
        FileUtils.ensure_dir_created(self.project_out_root)
        FileUtils.ensure_dir_created(self.log_dir)
        FileUtils.ensure_dir_created(self.yarn_patch_dir)
        FileUtils.ensure_dir_created(self.jira_umbrella_data_dir)
        FileUtils.ensure_dir_created(self.branch_comparator_output_dir)

    def ensure_required_env_vars_are_present(self):
        import os

        upstream_hadoop_dir = os.environ[ENV_HADOOP_DEV_DIR]
        downstream_hadoop_dir = os.environ[ENV_CLOUDERA_HADOOP_ROOT]

        if not upstream_hadoop_dir:
            raise ValueError(f"Upstream Hadoop dir (env var: {ENV_HADOOP_DEV_DIR}) is not set!")
        if not downstream_hadoop_dir:
            raise ValueError(f"Downstream Hadoop dir (env var: {ENV_CLOUDERA_HADOOP_ROOT}) is not set!")

        # Verify if dirs are created
        FileUtils.verify_if_dir_is_created(downstream_hadoop_dir)
        FileUtils.verify_if_dir_is_created(upstream_hadoop_dir)

        self.env = {LOADED_ENV_DOWNSTREAM_DIR: downstream_hadoop_dir, LOADED_ENV_UPSTREAM_DIR: upstream_hadoop_dir}

    def init_repos(self):
        self.ensure_required_env_vars_are_present()
        self.downstream_repo = GitWrapper(self.env[LOADED_ENV_DOWNSTREAM_DIR])
        self.upstream_repo = GitWrapper(self.env[LOADED_ENV_UPSTREAM_DIR])

    def save_patch(self, args):
        patch_saver = PatchSaver(args, self.upstream_repo, self.yarn_patch_dir, DEFAULT_BASE_BRANCH)
        return patch_saver.run()

    def create_review_branch(self, args):
        review_branch_creator = ReviewBranchCreator(args, self.upstream_repo, DEFAULT_BASE_BRANCH, ORIGIN_TRUNK)
        review_branch_creator.run()

    def backport_c6(self, args):
        mvn_cmd = "mvn clean install -Pdist -DskipTests -Pnoshade  -Dmaven.javadoc.skip=true"
        build_cmd = (
            "!! Remember to build project to verify the backported commit compiles !!"
            f"Run this command to build the project: {mvn_cmd}"
        )
        gerrit_push_cmd = (
            "Run this command to push to gerrit: "
            f"git push cauldron HEAD:refs/for/{args.cdh_branch}%{GERRIT_REVIEWER_LIST}"
        )
        post_commit_messages = [build_cmd, gerrit_push_cmd]

        downstream_base_ref = f"cauldron/{args.cdh_branch}"
        if "cdh_base_ref" in args and args.cdh_base_ref is not None:
            downstream_base_ref = args.cdh_base_ref
        backporter = Backporter(
            args,
            self.upstream_repo,
            self.downstream_repo,
            downstream_base_ref,
            post_commit_messages=post_commit_messages,
        )
        backporter.run()

    def upstream_pr_fetch(self, args):
        remote_repo_url = HADOOP_REPO_TEMPLATE.format(user=args.github_username)
        upstream_pr_fetcher = UpstreamPRFetcher(args, remote_repo_url, self.upstream_repo, DEFAULT_BASE_BRANCH)
        upstream_pr_fetcher.run()

    def save_patches(self, args):
        format_patch_saver = FormatPatchSaver(args, os.getcwd(), DateUtils.get_current_datetime())
        format_patch_saver.run()

    def diff_patches_of_jira(self, args):
        """
        THIS SCRIPT ASSUMES EACH PROVIDED BRANCH WITH PARAMETERS (e.g. trunk, 3.2, 3.1) has the given commit committed
        Example workflow:
        1. git log --oneline trunk | grep YARN-10028
        * 13cea0412c1 - YARN-10028. Integrate the new abstract log servlet to the JobHistory server.
        Contributed by Adam Antal 24 hours ago) <Szilard Nemeth>

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
        jira_umbrella_fetcher = UpstreamJiraUmbrellaFetcher(
            args, self.upstream_repo, self.downstream_repo, self.jira_umbrella_data_dir, DEFAULT_BASE_BRANCH
        )
        jira_umbrella_fetcher.run()

    def compare_branches(self, args):
        branch_comparator = BranchComparator(args, self.downstream_repo, self.branch_comparator_output_dir)
        FileUtils2.create_symlink(LATEST_SESSION, branch_comparator.config.output_dir, self.project_out_root)
        branch_comparator.run()

    def zip_latest_command_results(self, args):
        zip_latest_cmd_data = ZipLatestCommandData(args, yarn_functions.project_out_root)
        zip_latest_cmd_data.run()

    def send_latest_command_results(self, args):
        file_to_send = FileUtils.join_path(yarn_functions.project_out_root, LATEST_DATA_ZIP)
        send_latest_cmd_data = SendLatestCommandDataInEmail(args, file_to_send)
        send_latest_cmd_data.run()


if __name__ == "__main__":
    start_time = time.time()

    # TODO Revisit all exception handling: ValueError vs. exit() calls
    # Methods should throw exceptions, exit should be handled in this method
    yarn_functions = YarnDevFunc()

    # Parse args, commands will be mapped to YarnDevFunc functions in ArgParser.parse_args
    args = ArgParser.parse_args(yarn_functions)
    log_file = Setup.init_logger(
        yarn_functions.log_dir,
        console_debug=args.debug,
        postfix=args.command,
        repos=[yarn_functions.upstream_repo.repo, yarn_functions.downstream_repo.repo],
        verbose=args.verbose,
    )

    if CommandType.from_str(args.command) not in IGNORE_LATEST_SYMLINK_COMMANDS:
        FileUtils2.create_symlink(LATEST_LOG, log_file, yarn_functions.project_out_root)
    else:
        LOG.info(f"Skipping to re-create symlink as command is: {args.command}")

    # Call the handler function
    args.func(args)

    end_time = time.time()
    # TODO make a switch to turn execution time printing on
    # LOG.info("Execution of script took %d seconds", end_time - start_time)
