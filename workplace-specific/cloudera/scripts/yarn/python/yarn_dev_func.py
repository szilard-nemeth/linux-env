#!/usr/bin/python

import argparse
import sys
import datetime as dt
import logging
import os
import tempfile


from os.path import expanduser
import datetime
import time
from logging.handlers import TimedRotatingFileHandler

from git import GitCommandError, InvalidGitRepositoryError

from argparser import ArgParser
from command_runner import CommandRunner
from git_wrapper import GitWrapper
from patch_saver import PatchSaver
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


class YarnDevHighLevelFunctions:
    pass

@auto_str
class BranchResults:
    def __init__(self, branch_name, exists, commits, commit_hashes):
        self.branch_name = branch_name
        self.exists = exists
        self.commits = commits
        self.commit_hashes = commit_hashes
        self.git_diff = None

    @property
    def number_of_commits(self):
        return len(self.commits)

    @property
    def single_commit_hash(self):
        if len(self.commit_hashes) > 1:
            raise ValueError("This object has multiple commit hashes. The intended use of this method is when there's only one single commit hash!")
        return self.commit_hashes[0]


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

    def save_patch(self, args):
        patch_saver = PatchSaver(args, self.upstream_repo, self.yarn_patch_dir)
        return patch_saver.run()

    def create_review_branch(self, args):
        patch_file = args.patch_file

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

        self.upstream_repo.checkout_branch(TRUNK)
        self.upstream_repo.pull(ORIGIN)
        diff = self.upstream_repo.diff_between_refs(ORIGIN_TRUNK, TRUNK)
        if diff:
            LOG.error("There is a diff between local %s and %s! Run 'git reset %s --hard' and re-run the script! Exiting...", TRUNK, ORIGIN_TRUNK, ORIGIN_TRUNK)
            exit(3)

        apply_result = self.upstream_repo.apply_check(patch_file, raise_exception=False)
        if not apply_result:
            cmd = "git apply " + patch_file
            LOG.error("Patch does not apply to %s, please resolve the conflicts manually. Run this command to apply the patch again: %s", TRUNK, cmd)
            self.upstream_repo.checkout_previous_branch()
            exit(4)

        LOG.info("Patch %s applies cleanly to %s", patch_file, TRUNK)

        branch_exists = self.upstream_repo.is_branch_exist(target_branch)
        base_ref = TRUNK
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

    def backport_c6(self, args):
        upstream_jira_id = args.upstream_jira_id
        cdh_jira_id = args.cdh_jira_id
        cdh_branch = args.cdh_branch

        # TODO decide on the cdh branch whether this is C5 or C6 backport (remote is different)
        curr_branch = self.upstream_repo.get_current_branch_name()
        LOG.info("Current branch: %s", curr_branch)

        self.upstream_repo.fetch(all=True)
        self.upstream_repo.checkout_branch(TRUNK)
        self.upstream_repo.pull(ORIGIN)

        git_log_result = self.upstream_repo.log(HEAD, oneline=True, grep=upstream_jira_id)
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
                                                                                   reviewers=GERRIT_REVIEWER_LIST))

    def upstream_pr_fetch(self, args):
        github_username = args.github_username
        remote_branch = args.remote_branch
        prefix = args.dest_dir_prefix

        curr_branch = self.upstream_repo.get_current_branch_name()
        LOG.info("Current branch: %s", curr_branch)

        repo_url = HADOOP_REPO_TEMPLATE.format(user=github_username)
        success = self.upstream_repo.fetch(repo_url=repo_url, remote_name=remote_branch)
        if not success:
            LOG.error("Cannot fetch from remote branch: {url}/{remote}".format(url=repo_url, remote=remote_branch))
            exit(1)

        log_result = self.upstream_repo.log(FETCH_HEAD, n=10)
        LOG.info("Printing 10 topmost commits of %s:\n %s", FETCH_HEAD, '\n'.join(log_result))

        trunk_vs_fetch_head = '{}..{}'.format(TRUNK, FETCH_HEAD)
        log_result = self.upstream_repo.log(trunk_vs_fetch_head, oneline=True)
        LOG.info("\n\nPrinting diff of %s:\n %s", trunk_vs_fetch_head, '\n'.join(log_result))
        num_commits = len(log_result)
        if num_commits > 1:
            LOG.error("Number of commits between %s is not only one! Exiting...", trunk_vs_fetch_head)
            exit(2)

        success = self.upstream_repo.cherry_pick(FETCH_HEAD)
        if not success:
            LOG.error("Cherry-pick failed. Exiting")
            exit(3)

        LOG.info("REMEMBER to change the commit message with command: 'git commit --amend'")
        LOG.info("REMEMBER to reset the author with command: 'git commit --amend --reset-author")

    def save_patches(self, args):
        base_refspec = args.base_refspec
        other_refspec = args.other_refspec
        dest_basedir = args.dest_basedir
        dest_dir_prefix = args.dest_dir_prefix

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
        jira_id = args.jira_id
        branches = args.branches
        tmpdirname = "/tmp/yarndiffer"
        FileUtils.ensure_dir_created(tmpdirname)

        branch_results = {}
        for branch in branches:
            LOG.info("Processing branch: %s", branch)

            exists = self.upstream_repo.is_branch_exist(branch)
            commits = self.upstream_repo.log(branch, grep=jira_id, oneline=True)
            commit_hashes = [c.split(' ')[0] for c in commits]
            branch_result = BranchResults(branch, exists, commits, commit_hashes)
            branch_results[branch] = branch_result

            # Only store diff if number of matched commits for this branch is 1
            if branch_result.number_of_commits == 1:
                commit_hash = branch_result.single_commit_hash
                # TODO create diff_with_parent helper method to GitWrapper
                diff = self.upstream_repo.diff_between_refs(commit_hash + "^", commit_hash)
                branch_result.git_diff = diff

                diff_filename = "{}-{}.diff".format(jira_id, branch)
                PatchUtils.save_diff_to_patch_file(diff, FileUtils.join_path(tmpdirname, diff_filename))

        # Validate results
        branch_does_not_exist = [b_res.branch_name for br, b_res in branch_results.items() if not b_res.exists]
        zero_commit = [b_res.branch_name for br, b_res in branch_results.items() if b_res.number_of_commits == 0]
        multiple_commits = [b_res.branch_name for br, b_res in branch_results.items() if b_res.number_of_commits > 1]

        LOG.debug("Branch result objects: %s", branch_results)
        if branch_does_not_exist:
            LOG.error("The following branches are not existing for Jira id '%s': %s", branch_does_not_exist)
            exit(1)

        if zero_commit:
            LOG.error("The following branches do not contain commit for Jira id '%s': %s", jira_id, zero_commit)
            exit(1)

        if multiple_commits:
            LOG.error("The following branches contain multiple commits for Jira id '%s': %s", jira_id, multiple_commits)
            exit(1)

        LOG.info("Generated diff files: ")
        diff_files = FileUtils.find_files(tmpdirname, jira_id + '-.*', single_level=True, full_path_result=True)
        for f in diff_files:
            LOG.info("%s: %s", f, FileUtils.get_file_size(f))

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
    # TODO make a swtich to turn execution time printing on
    # LOG.info("Execution of script took %d seconds", end_time - start_time)
