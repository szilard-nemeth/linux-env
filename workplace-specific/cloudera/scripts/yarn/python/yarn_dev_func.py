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


@auto_str
class CommitData:
    def __init__(self, hash, jira_id, message, date):
        self.hash = hash
        self.jira_id = jira_id
        self.message = message
        self.date = date


@auto_str
class JiraUmbrellaSummary:
    def __init__(self, no_of_jiras, no_of_commits, no_of_files, commit_data_list):
        self.no_of_jiras = no_of_jiras
        self.no_of_commits = no_of_commits
        self.no_of_files = no_of_files
        self.commit_data_list = commit_data_list

    def to_summary_file_str(self):
        summary_str = "Number of jiras: {}\n".format(self.no_of_jiras)
        summary_str += "Number of commits: {}\n".format(self.no_of_commits)
        summary_str += "Number of files changed: {}\n".format(self.no_of_files)

        summary_str += "COMMITS: \n"
        for c_data in self.commit_data_list:
            summary_str += "{} {}\n".format(c_data.message, c_data.date)

        return summary_str


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
        FileUtils.ensure_dir_created(self.project_out_root)
        FileUtils.ensure_dir_created(self.log_dir)
        FileUtils.ensure_dir_created(self.yarn_patch_dir)

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
        patch_differ = UpstreamJiraPatchDiffer(args, self.upstream_repo)
        patch_differ.run()

    def fetch_jira_umbrella_data(self, args):
        jira_id = args.jira_id
        base_tmp_dir = "/tmp/jira-umbrella-data-python"

        curr_branch = self.upstream_repo.get_current_branch_name()
        LOG.info("Current branch: %s", curr_branch)

        if curr_branch != TRUNK:
            LOG.error("Current branch is not %s. Exiting!", TRUNK)
            exit(1)

        result_basedir = FileUtils.join_path(base_tmp_dir, jira_id)
        jira_html_file = FileUtils.join_path(result_basedir, "jira.html")
        jira_list_file = FileUtils.join_path(result_basedir, "jira-list.txt")
        commits_file = FileUtils.join_path(result_basedir, "commit-hashes.txt")
        changed_files_file = FileUtils.join_path(result_basedir, "changed-files.txt")
        summary_file = FileUtils.join_path(result_basedir, "summary.txt")
        intermediate_results_file = FileUtils.join_path(result_basedir, "intermediate-results.txt")
        FileUtils.create_files(jira_html_file, jira_list_file, commits_file, changed_files_file, summary_file, intermediate_results_file)

        LOG.info("Fetching HTML of jira: %s", jira_id)
        jira_html = JiraUtils.download_jira_html(jira_id, jira_html_file)
        jira_ids = JiraUtils.parse_subjiras_from_umbrella_html(jira_html, jira_list_file, filter_ids=[jira_id])
        LOG.info("Found jira IDs: %s", jira_ids)
        piped_jira_ids = '|'.join(jira_ids)

        # It's quite complex to grep for multiple jira IDs with gitpython, so let's rather call an external command
        git_log_result = self.upstream_repo.log(HEAD, oneline=True)
        output = self.egrep_with_cli(git_log_result, intermediate_results_file, piped_jira_ids)
        matched_commit_list = output.split("\n")
        LOG.info("Number of matched commits: %s", len(matched_commit_list))
        LOG.debug("Matched commits: \n%s", '\n'.join(matched_commit_list))

        # Commits in reverse order (oldest first)
        matched_commit_list.reverse()
        matched_commit_hashes = [c.split(' ')[0] for c in matched_commit_list]
        FileUtils.save_to_file(commits_file, '\n'.join(matched_commit_hashes))

        list_of_changed_files = []
        for hash in matched_commit_hashes:
            changed_files = self.upstream_repo.diff_tree(hash, no_commit_id=True, name_only=True, recursive=True)
            list_of_changed_files.append(changed_files)
            LOG.debug("List of changed files for commit hash '%s': %s", hash, changed_files)

        LOG.info("Got %d changed files", len(list_of_changed_files))
        # Filter dupes, flatten list of lists
        list_of_changed_files = [y for x in list_of_changed_files for y in x]
        list_of_changed_files = list(set(list_of_changed_files))
        LOG.info("Got %d unique changed files", len(list_of_changed_files))
        FileUtils.save_to_file(changed_files_file, '\n'.join(list_of_changed_files))

        # Iterate over commit hashes, print the following to summary_file for each commit hash:
        # <hash> <YARN-id> <commit date>
        commit_data_list = []
        for commit_str in matched_commit_list:
            comps = commit_str.split(' ')
            hash = comps[0]
            commit_date = self.upstream_repo.show(hash, no_patch=True, no_notes=True, pretty='%cI')
            commit_data_list.append(CommitData(hash=hash, jira_id=comps[1], message=' '.join(comps[2:]), date=commit_date))

        summary = JiraUmbrellaSummary(len(jira_ids), len(matched_commit_hashes), len(list_of_changed_files), commit_data_list)
        FileUtils.save_to_file(summary_file, summary.to_summary_file_str())

        # Iterate over changed files, print all matching changes to the particular file
        # Create changes file for each touched file
        LOG.info("Recording changes of individual files...")
        for idx, changed_file in enumerate(list_of_changed_files):
            target_file = FileUtils.join_path(result_basedir, 'changes', os.path.basename(changed_file))
            FileUtils.ensure_file_exists(target_file, create=True)

            # NOTE: It seems impossible to call the following command with gitpython:
            # git log --follow --oneline -- <file>
            # Use a simple CLI command instead
            cli_command = "cd {repo_path} && git log --follow --oneline -- {changed_file} | egrep \"{jira_list}\"".format(
                repo_path=self.upstream_repo.repo_path,
                changed_file=changed_file,
                jira_list=piped_jira_ids)
            LOG.info("[%d / %d] CLI command: %s", idx + 1, len(list_of_changed_files), cli_command)
            output = YarnDevFunc.run_cli_command(cli_command, fail_on_empty_output=False)
            LOG.info("Saving changes result to file: %s", target_file)
            FileUtils.save_to_file(target_file, output)

        # Print summary
        LOG.info("=================SUMMARY=================")
        LOG.info(summary.to_summary_file_str())
        LOG.info("=========================================")

        files = FileUtils.find_files(result_basedir, regex=".*", full_path_result=True)
        LOG.info("All result files: \n%s", '\n'.join(files))

    @staticmethod
    def egrep_with_cli(git_log_result, file, piped_jira_ids):
        FileUtils.save_to_file(file, '\n'.join(git_log_result))
        cli_command = "cat {git_log_file} | egrep '{jira_list}'".format(git_log_file=file,
                                                                        jira_list=piped_jira_ids)
        return YarnDevFunc.run_cli_command(cli_command)

    @staticmethod
    def run_cli_command(cli_command, fail_on_empty_output=True):
        LOG.info("Running CLI command: %s", cli_command)
        output = CommandRunner.getoutput(cli_command)
        if fail_on_empty_output and not output:
            LOG.error("Command failed: %s", cli_command)
            exit(1)
        return output


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
