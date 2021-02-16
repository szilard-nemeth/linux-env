import logging
import os
import unittest
from os.path import expanduser

from git import InvalidGitRepositoryError, Repo, GitCommandError, Actor
from pythoncommons.file_utils import FileUtils
from pythoncommons.patch_utils import PatchUtils

from yarndevfunc.constants import HADOOP_REPO_APACHE, HEAD, TRUNK, PROJECT_NAME, DEST_DIR_PREFIX
from yarndevfunc.git_wrapper import GitWrapper, ProgressPrinter
from yarndevfunc.yarn_dev_func import Setup

DUMMYFILE_1 = "dummyfile1"
DUMMYFILE_2 = "dummyfile2"

LOG = logging.getLogger(__name__)
YARNCONFIGURATION_PATH = (
    "hadoop-yarn-project/hadoop-yarn/hadoop-yarn-api/src/main/java/org/apache/hadoop/yarn/conf/YarnConfiguration.java"
)

TESTCASE = unittest.TestCase("__init__")


class Object(object):
    pass


class TestUtilities:
    repo = None
    log_dir = None
    sandbox_repo_path = None
    base_branch = TRUNK

    def __init__(self, test_instance, test_branch):
        self.test_instance = test_instance
        self.test_branch = test_branch
        self.saved_patches_dir = None

    def set_env_vars(self, upstream_repo, downstream_repo):
        os.environ["HADOOP_DEV_DIR"] = upstream_repo
        os.environ["CLOUDERA_HADOOP_ROOT"] = downstream_repo

    def setUpClass(self, repo_postfix=None, init_logging=True):
        self.setup_dirs(repo_postfix=repo_postfix)
        try:
            self.setup_repo()
            if init_logging:
                Setup.init_logger(self.log_dir, console_debug=False, postfix="TEST", repos=[self.repo])
            self.reset_and_checkout_trunk()
        except InvalidGitRepositoryError:
            LOG.info("Cloning repo '%s' for the first time...", HADOOP_REPO_APACHE)
            Repo.clone_from(HADOOP_REPO_APACHE, self.sandbox_repo_path, progress=ProgressPrinter("clone"))
            self.setup_repo(log=False)
            self.reset_and_checkout_trunk()

    def setup_repo(self, log=True):
        # This call will raise InvalidGitRepositoryError in case git repo is not cloned yet to this path
        self.repo_wrapper = GitWrapper(self.sandbox_repo_path)
        self.repo = self.repo_wrapper.repo
        if log:
            LOG.info("Repo '%s' is already cloned to path '%s'", self.repo, self.sandbox_repo_path)

    def reset_and_checkout_trunk(self):
        self.reset_changes()
        self.checkout_trunk()

    def setup_dirs(self, repo_postfix):
        self.project_out_root = FileUtils.join_path(expanduser("~"), PROJECT_NAME, DEST_DIR_PREFIX)
        self.log_dir = FileUtils.join_path(self.project_out_root, "logs")

        if not repo_postfix:
            repo_postfix = ""
        self.sandbox_repo_path = FileUtils.join_path(self.project_out_root, "sandbox_repo" + repo_postfix)
        self.saved_patches_dir = FileUtils.join_path(self.project_out_root, "saved-patches")
        self.dummy_patches_dir = FileUtils.join_path(self.project_out_root, "dummy-patches")
        self.jira_umbrella_data_dir = FileUtils.join_path(self.project_out_root, "jira-umbrella-data")
        FileUtils.ensure_dir_created(self.project_out_root)
        FileUtils.ensure_dir_created(self.sandbox_repo_path)
        FileUtils.ensure_dir_created(self.jira_umbrella_data_dir)
        FileUtils.ensure_dir_created(self.dummy_patches_dir)
        FileUtils.ensure_dir_created(self.saved_patches_dir)
        FileUtils.ensure_dir_created(self.log_dir)

    def checkout_trunk(self):
        default_branch = "trunk"
        LOG.info("Checking out branch: %s", default_branch)
        self.repo.heads[default_branch].checkout()

    def cleanup_and_checkout_test_branch(self, branch=None, remove=True, pull=True, checkout_from=None):
        if not branch:
            if not self.test_branch:
                raise ValueError("Test branch must be set!")
            branch = self.test_branch
        self.reset_changes()
        if pull:
            self.pull_to_trunk()
        try:
            if branch in self.repo.heads:
                LOG.info("Resetting changes on branch (hard reset): %s", branch)
                self.repo.heads[branch].checkout()
                self.repo.git.reset("--hard")

                if branch != self.base_branch:
                    # Current branch cannot be removed in git, so checkout trunk then remove branch
                    self.checkout_trunk()
                    if remove:
                        self.remove_branch(branch)
        except GitCommandError:
            # Do nothing if branch does not exist
            LOG.exception("Failed to remove branch.", exc_info=True)
            pass

        if branch != self.base_branch:
            base_ref = checkout_from if checkout_from else self.base_branch
            self.repo_wrapper.checkout_new_branch(branch, base_ref)
        else:
            LOG.info("Checking out branch: %s", branch)
            self.checkout_trunk()

    def pull_to_trunk(self):
        self.checkout_trunk()
        LOG.info("Pulling origin")
        self.repo.remotes.origin.pull()

    def reset_and_checkout_existing_branch(self, branch, pull=True):
        self.reset_changes()
        if pull:
            self.pull_to_trunk()
        LOG.info("Checking out branch: %s", branch)
        self.repo.heads[branch].checkout()

    def remove_branch(self, branch, ignore_error=True):
        LOG.info("Removing branch: %s", branch)

        # Checkout trunk, in case of 'branch' is currently checked out
        self.checkout_trunk()

        try:
            self.repo.delete_head(branch, force=True)
        except GitCommandError as e:
            if not ignore_error:
                raise e

    def reset_changes(self):
        # TODO Move this to GitWrapper
        LOG.info("Reset all changes...")
        self.repo.head.reset(commit="origin/trunk", index=True, working_tree=True)
        self.repo.git.clean("-xdf")

    def does_file_contain(self, file, string):
        with open(file) as f:
            if string in f.read():
                return True
        TESTCASE.fail(f"File '{file}' does not contain expected string: '{string}'")

    def add_some_file_changes(self, commit=False, commit_message_prefix=None):
        FileUtils.save_to_file(FileUtils.join_path(self.sandbox_repo_path, DUMMYFILE_1), DUMMYFILE_1)
        FileUtils.save_to_file(FileUtils.join_path(self.sandbox_repo_path, DUMMYFILE_2), DUMMYFILE_2)
        yarn_config_java = FileUtils.join_path(self.sandbox_repo_path, YARNCONFIGURATION_PATH)
        FileUtils.append_to_file(yarn_config_java, "dummy_changes_to_conf_1\n")
        FileUtils.append_to_file(yarn_config_java, "dummy_changes_to_conf_2\n")

        if commit:
            author = Actor("A test author", "unittest@example.com")
            committer = Actor("A test committer", "unittest@example.com")
            self.repo.index.add([DUMMYFILE_1, DUMMYFILE_2, yarn_config_java])
            commit_msg = "test_commit"
            if commit_message_prefix:
                commit_msg = commit_message_prefix + commit_msg
            self.repo.index.commit(commit_msg, author=author, committer=committer)
            # self.repo.git.commit('-am', 'test commit', author='unittest@xxx.com')

    def add_file_changes_and_save_to_patch(self, patch_file):
        self.add_some_file_changes()
        yarn_config_java = FileUtils.join_path(self.sandbox_repo_path, YARNCONFIGURATION_PATH)
        self.repo.index.add([DUMMYFILE_1, DUMMYFILE_2, yarn_config_java])

        # diff = self.repo.index.diff(self.repo.head.commit, create_patch=True)
        diff = self.repo_wrapper.diff(HEAD, cached=True)
        PatchUtils.save_diff_to_patch_file(diff, patch_file)
        self.reset_changes()

        # Verify file
        self.does_file_contain(patch_file, "+dummyfile1")
        self.does_file_contain(patch_file, "+dummyfile2")
        self.does_file_contain(patch_file, "+dummy_changes_to_conf_1")
        self.does_file_contain(patch_file, "+dummy_changes_to_conf_2")

    def remove_branches(self, prefix):
        branches = self.get_all_branch_names()
        matching_branches = list(filter(lambda br: br.startswith(prefix), branches))

        for branch in matching_branches:
            self.remove_branch(branch)

    def get_all_branch_names(self):
        return [br.name for br in self.repo.heads]

    def verify_commit_message_of_branch(self, branch, expected_commit_message, verify_cherry_picked_from=False):
        commit = self.repo.heads[branch].commit
        actual_commit_message = commit.message.rstrip()
        # Example commit message: 'XXX-1234: YARN-123456: test_commit
        # (cherry picked from commit 51583ec3dbc715f9ff0c5a9b52f1cc7b607b6b26)'

        TESTCASE.assertIn(expected_commit_message, actual_commit_message)
        if verify_cherry_picked_from:
            TESTCASE.assertIn("cherry picked from commit ", actual_commit_message)

    def add_remote(self, name, url):
        try:
            self.repo.create_remote(name, url=url)
        except GitCommandError:
            pass

    def remove_remote(self, name):
        self.repo.delete_remote(name)

    def prepare_git_config(self, user, email):
        self.repo.config_writer().set_value("user", "name", user).release()
        self.repo.config_writer().set_value("user", "email", email).release()

    def remove_comitter_git_config(self):
        self.repo.config_writer().set_value("user", "name", "").release()
        self.repo.config_writer().set_value("user", "email", "").release()

    def checkout_parent_of_branch(self, branch):
        if branch not in self.repo.heads:
            raise ValueError(f"Cannot find branch: {branch}")
        parent_of_branch = branch + "^"
        self.repo.git.checkout(parent_of_branch)
        return self.repo.git.rev_parse("--verify", HEAD)

    def get_hash_of_commit(self, branch):
        return self.repo.heads[branch].commit.hexsha

    def checkout_branch(self, branch):
        if branch not in self.repo.heads:
            raise ValueError(f"Cannot find branch: {branch}")
        self.repo.heads[branch].checkout()

    def assert_files_not_empty(self, basedir, expected_files=None):
        found_files = FileUtils.find_files(basedir, ".*", single_level=True, full_path_result=True)
        for f in found_files:
            self.assert_file_not_empty(f)

        if expected_files:
            TESTCASE.assertEqual(expected_files, len(found_files))

    def assert_file_not_empty(self, f):
        TESTCASE.assertTrue(os.path.getsize(f) > 0)
