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

from git import GitCommandError, InvalidGitRepositoryError

from git_wrapper import GitWrapper
from utils import FileUtils, PatchUtils, StringUtils, DateTimeUtils

LOG = logging.getLogger(__name__)
__author__ = 'Szilard Nemeth'


ENV_CLOUDERA_HADOOP_ROOT = 'CLOUDERA_HADOOP_ROOT'
ENV_HADOOP_DEV_DIR = 'HADOOP_DEV_DIR'

# Do not leak bad ENV variable namings into the python code
LOADED_ENV_UPSTREAM_DIR="upstream-hadoop-dir"
LOADED_ENV_DOWNSTREAM_DIR="downstream-hadoop-dir"
PROJECT_NAME="yarn_dev_func"
YARN_PATCH_FILENAME_REGEX = ".*(YARN-[0-9]+).*\.patch"
HADOOP_REPO_TEMPLATE = "https://github.com/{user}/hadoop.git"


class CommandType(Enum):
    SAVE_PATCH = 'save_patch'
    CREATE_REVIEW_BRANCH = 'create_review_branch'
    BACKPORT_C6 = "backport_c6"
    UPSTREAM_PR_FETCH = "upstream_pr_fetch"
    SAVE_DIFF_AS_PATCHES = "save_diff_as_patches"


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
        Setup.add_save_patch_parser(subparsers)
        Setup.add_create_review_branch_parser(subparsers)
        Setup.add_backport_c6_parser(subparsers)
        Setup.add_upstream_pull_request_fetcher(subparsers)
        Setup.add_save_diff_as_patches(subparsers)

        # Normal arguments
        parser.add_argument('-v', '--verbose', action='store_true',
                            dest='verbose', default=None, required=False,
                            help='More verbose log')

        return parser.parse_args()

    @staticmethod
    def add_save_patch_parser(subparsers):
        parser = subparsers.add_parser(CommandType.SAVE_PATCH.value,
                                                  help='Saves patch from upstream repository to yarn patches dir')
        parser.set_defaults(command=CommandType.SAVE_PATCH)

    @staticmethod
    def add_create_review_branch_parser(subparsers):
        parser = subparsers.add_parser(CommandType.CREATE_REVIEW_BRANCH.value,
                                                  help='Creates review branch from upstream patch file')
        parser.add_argument('patch_file', type=str, help='Path to patch file')
        parser.set_defaults(command=CommandType.CREATE_REVIEW_BRANCH)

    @staticmethod
    def add_backport_c6_parser(subparsers):
        parser = subparsers.add_parser(CommandType.BACKPORT_C6.value,
                                                   help='Backports upstream commit to C6 branch, '
                                                        'Example usage: <command> YARN-7948 CDH-64201 cdh6.x')
        parser.add_argument('upstream_jira_id', type=str, help='Upstream jira id. Example: YARN-4567')
        parser.add_argument('cdh_jira_id', type=str, help='CDH jira id. Example: CDH-4111')
        parser.add_argument('cdh_branch', type=str, help='CDH branch name')
        parser.set_defaults(command=CommandType.BACKPORT_C6)

    @staticmethod
    def add_upstream_pull_request_fetcher(subparsers):
        parser = subparsers.add_parser(CommandType.UPSTREAM_PR_FETCH.value,
                                       help='Fetches upstream changes from a repo then cherry-picks single commit.'
                                            'Example usage: <command> szilard-nemeth YARN-9999')
        parser.add_argument('github_username', type=str, help='Github username')
        parser.add_argument('remote_branch', type=str, help='Name of the remote branch.')
        parser.set_defaults(command=CommandType.UPSTREAM_PR_FETCH)

    @staticmethod
    def add_save_diff_as_patches(subparsers):
        parser = subparsers.add_parser(CommandType.SAVE_DIFF_AS_PATCHES.value,
                                       help='Diffs branches and creates patch files with git format-patch and saves them to a directory.'
                                            'Example: <command> master gpu')
        parser.add_argument('base_refspec', type=str, help='Git base refspec to diff with.')
        parser.add_argument('other_refspec', type=str, help='Git other refspec to diff with.')
        parser.add_argument('dest_basedir', type=str, help='Destination basedir.')
        parser.add_argument('dest_dir_prefix', type=str, help='Directory as prefix to export the patch files to.')
        parser.set_defaults(command=CommandType.SAVE_DIFF_AS_PATCHES)


class YarnDevHighLevelFunctions:
    pass


class YarnDevFunc:
    GERRIT_REVIEWER_LIST = "r=shuzirra,r=adam.antal,r=pbacsko,r=kmarton,r=gandras,r=bteke"

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

        # TODO if there's no commit between trunk..branch, don't move forward and exit
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

    def create_review_branch(self, patch_file):
        FileUtils.ensure_file_exists(patch_file)
        patch_file_name = FileUtils.path_basename(patch_file)
        matches = StringUtils.ensure_matches_pattern(patch_file_name, YARN_PATCH_FILENAME_REGEX)
        if not matches:
            LOG.error("Filename '%s' (full path: %s) does not match usual patch file pattern: '%s', exiting...!", patch_file_name, patch_file, YARN_PATCH_FILENAME_REGEX)
            exit(1)

        orig_branch = self.upstream_repo.get_current_branch_name()
        LOG.info("Current branch: %s", orig_branch)

        target_branch = "review-" + StringUtils.get_matched_group(patch_file, YARN_PATCH_FILENAME_REGEX, 1)
        LOG.info("Target branch: %s", target_branch)

        clean = self.upstream_repo.is_working_directory_clean()
        if not clean:
            LOG.error("git working directory is not clean, please stash or drop your changes")
            exit(2)

        self.upstream_repo.checkout_branch('trunk')
        self.upstream_repo.pull('origin')
        diff = self.upstream_repo.diff_between_refs('origin/trunk', 'trunk')
        if diff:
            LOG.error("There is a diff between local trunk and origin/trunk! Run 'git reset origin/trunk --hard' and re-run the script! Exiting...")
            exit(3)

        apply_result = self.upstream_repo.apply_check(patch_file, raise_exception=False)
        if not apply_result:
            cmd = "git apply " + patch_file
            LOG.error("Patch does not apply to trunk, please resolve the conflicts manually. Run this command to apply the patch again: %s", cmd)
            self.upstream_repo.checkout_previous_branch()
            exit(4)

        LOG.info("Patch %s applies cleanly to trunk", patch_file)

        branch_exists = self.upstream_repo.is_branch_exist(target_branch)
        base_ref = 'trunk'
        if not branch_exists:
            success = self.upstream_repo.checkout_new_branch(target_branch, base_ref)
            if not success:
                LOG.error("Cannot checkout new branch %s based on ref %s", target_branch, base_ref)
                exit(5)
            LOG.info("Checked out branch %s based on ref %s", target_branch, base_ref)
        else:
            branch_pattern = target_branch + "*"
            branches = self.upstream_repo.list_branches(branch_pattern)
            LOG.info("Found existing review branches for this patch: %s", branches)
            target_branch = PatchUtils.get_next_review_branch_name(branches)
            LOG.info("Creating new version of review branch as: %s", target_branch)
            success = self.upstream_repo.checkout_new_branch(target_branch, base_ref)
            if not success:
                LOG.error("Cannot checkout new branch %s based on ref %s", target_branch, base_ref)
                exit(6)

        self.upstream_repo.apply_patch(patch_file, include_check=False)
        LOG.info("Successfully applied patch: %s", patch_file)
        commit_msg = "patch file: {}".format(patch_file)
        self.upstream_repo.add_all_and_commit(commit_msg)
        LOG.info("Committed changes of patch: %s with message: %s", patch_file, commit_msg)

    def backport_c6(self, upstream_jira_id, cdh_jira_id, cdh_branch):
        # TODO decide on the cdh branch whether this is C5 or C6 backport (remote is different)
        curr_branch = self.upstream_repo.get_current_branch_name()
        LOG.info("Current branch: %s", curr_branch)

        self.upstream_repo.fetch(all=True)
        self.upstream_repo.checkout_branch('trunk')
        self.upstream_repo.pull('origin')

        git_log_result = self.upstream_repo.log(oneline=True, grep=upstream_jira_id)
        # Restore original branch in either error-case or normal case
        self.upstream_repo.checkout_previous_branch()
        if not git_log_result:
            raise ValueError("No match found for upsream commit with name: %s", upstream_jira_id)
        if len(git_log_result) > 1:
            raise ValueError("Ambiguous upsream commit with name: %s. Results: %s", upstream_jira_id, git_log_result)

        commit_hash = git_log_result[0].split(' ')[0]

        # DO THE REST OF THE WORK IN THE DOWNSTREAM REPO
        self.downstream_repo.fetch(all=True)

        # TODO handle if branch already exist (is it okay to silently ignore?) or should use current branch with switch?
        # git checkout -b "$CDH_JIRA_NO-$CDH_BRANCH" cauldron/${CDH_BRANCH}
        self.downstream_repo.checkout_new_branch('{}-{}'.format(cdh_jira_id, cdh_branch), 'cauldron/{}'.format(cdh_branch))
        cherry_pick_result = self.downstream_repo.cherry_pick(commit_hash, x=True)

        # TODO add resume functionality so that commit message rewrite can happen
        if not cherry_pick_result:
            LOG.error("Failed to cherry-pick commit: %s. "
                      "Perhaps there were some merge conflicts, "
                      "please resolve them and run: git cherry-pick --continue", commit_hash)
            # TODO print git commit and git push command, print it to a script that can continue!
            exit(1)

        # Add downstream (CDH jira) number as a prefix.
        # Since it triggers a commit, it will also add gerrit Change-Id to the commit.
        old_commit_msg = self.downstream_repo.log(format='%B', n=1)
        self.downstream_repo.commit(amend=True, message="{}: {}".format(cdh_jira_id, old_commit_msg))

        # TODO make an option that decides if mvn clean install should be run!
        # Run build to verify backported commit compiles fine
        # mvn clean install -Pdist -DskipTests -Pnoshade  -Dmaven.javadoc.skip=true

        # Push to gerrit (intentionally commented out)
        LOG.info("Commit was successful! "
                 "Run this command to push to gerrit: "
                 "git push cauldron HEAD:refs/for/{cdh_branch}%{reviewers}".format(cdh_branch=cdh_branch,
                                                                                   reviewers=YarnDevFunc.GERRIT_REVIEWER_LIST))

    def upstream_pr_fetch(self, github_username, remote_branch, prefix):
        curr_branch = self.upstream_repo.get_current_branch_name()
        LOG.info("Current branch: %s", curr_branch)

        repo_url = HADOOP_REPO_TEMPLATE.format(user=github_username)
        success = self.upstream_repo.fetch(repo_url=repo_url, remote_name=remote_branch)
        if not success:
            LOG.error("Cannot fetch from remote branch: {url}/{remote}".format(url=repo_url, remote=remote_branch))
            exit(1)

        log_result = self.upstream_repo.log('FETCH_HEAD', n=10)
        LOG.info("Printing 10 topmost commits of FETCH_HEAD:\n %s", '\n'.join(log_result))

        log_result = self.upstream_repo.log("trunk..FETCH_HEAD", oneline=True)
        LOG.info("\n\nPrinting diff of trunk..FETCH_HEAD:\n %s", '\n'.join(log_result))
        num_commits = len(log_result)
        if num_commits > 1:
            LOG.error("Number of commits between trunk..FETCH_HEAD is not only one! Exiting...")
            exit(2)

        success = self.upstream_repo.cherry_pick("FETCH_HEAD")
        if not success:
            LOG.error("Cherry-pick failed. Exiting")
            exit(3)

        LOG.info("REMEMBER to change the commit message with command: 'git commit --amend'")
        LOG.info("REMEMBER to reset the author with command: 'git commit --amend --reset-author")

    def save_patches(self, base_refspec, other_refspec, dest_basedir, dest_dir_prefix):
        # TODO check if git is clean (no modified, unstaged files, etc)
        repo = None
        try:
            repo = GitWrapper(os.getcwd())
        except InvalidGitRepositoryError as e:
            LOG.error("Current directory is not a git repo: %s", os.getcwd())
            exit(1)

        exists = repo.is_branch_exist(base_refspec)
        if not exists:
            LOG.error("Specified base refspec is not valid: %s", base_refspec)
            exit(2)

        exists = repo.is_branch_exist(other_refspec)
        if not exists:
            LOG.error("Specified other refspec is not valid: %s", other_refspec)
            exit(2)

        # Check if dest_basedir exists
        dest_basedir = expanduser(dest_basedir)
        patch_file_dest_path = FileUtils.join_path(dest_basedir, dest_dir_prefix, DateTimeUtils.get_current_datetime())
        FileUtils.ensure_dir_created(patch_file_dest_path)

        refspec = '{}..{}'.format(base_refspec, other_refspec)
        LOG.info("Saving git patches based on refspec '%s', to directory: %s", refspec, patch_file_dest_path)
        repo.format_patch(refspec, output_dir=patch_file_dest_path, full_index=True)


if __name__ == '__main__':
    start_time = time.time()

    # Parse args
    args = Setup.parse_args()
    verbose = args.verbose
    if verbose:
        print("Args: " + str(args))

    # TODO Revisit all exception handling: ValueError vs. exit() calls
    # Methods should throw exceptions, exit should be handled in this method
    yarn_functions = YarnDevFunc(args)
    yarn_functions.init_repos()

    # Initialize logging
    # verbose = True if args.verbose else False
    Setup.init_logger(yarn_functions.log_dir, console_debug=False)

    command = args.command
    if command == CommandType.SAVE_PATCH:
        yarn_functions.save_patch()
    elif command == CommandType.CREATE_REVIEW_BRANCH:
        yarn_functions.create_review_branch(args.patch_file)
    elif command == CommandType.BACKPORT_C6:
        yarn_functions.backport_c6(args.upstream_jira_id, args.cdh_jira_id, args.cdh_branch)
    elif command == CommandType.UPSTREAM_PR_FETCH:
        yarn_functions.upstream_pr_fetch(args.github_username, args.remote_branch, args.dest_dir_prefix)
    elif command == CommandType.SAVE_DIFF_AS_PATCHES:
        yarn_functions.save_patches(args.base_refspec, args.other_refspec, args.dest_basedir, args.dest_dir_prefix)

    end_time = time.time()
    #LOG.info("Execution of script took %d seconds", end_time - start_time)
