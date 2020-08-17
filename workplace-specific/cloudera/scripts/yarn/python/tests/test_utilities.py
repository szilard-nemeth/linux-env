import logging
import os
import unittest
from os.path import expanduser

from git import InvalidGitRepositoryError, Repo, GitCommandError, Actor

from constants import HADOOP_REPO_APACHE, HEAD
from git_wrapper import GitWrapper, ProgressPrinter
from utils import FileUtils, PatchUtils
from yarn_dev_func import Setup

DUMMYFILE_1 = "dummyfile1"
DUMMYFILE_2 = "dummyfile2"

LOG = logging.getLogger(__name__)
YARNCONFIGURATION_PATH = "hadoop-yarn-project/hadoop-yarn/hadoop-yarn-api/src/main/java/org/apache/hadoop/yarn/conf/YarnConfiguration.java"

TESTCASE = unittest.TestCase('__init__')

class Object(object):
    pass


class TestUtilities:
    repo = None
    log_dir = None
    sandbox_hadoop_repo_path = None

    def __init__(self, test_instance, test_branch):
        self.test_instance = test_instance
        self.test_branch = test_branch
        self.saved_patches_dir = None

    def set_env_vars(self, upstream_repo, downstream_repo):
        os.environ["HADOOP_DEV_DIR"] = upstream_repo
        os.environ["CLOUDERA_HADOOP_ROOT"] = downstream_repo

    def setup_dirs(self):
        self.project_out_root = FileUtils.join_path(expanduser("~"), "yarn_dev_func-test")
        self.log_dir = FileUtils.join_path(self.project_out_root, 'logs')
        self.sandbox_hadoop_repo_path = FileUtils.join_path(self.project_out_root, "sandbox_repo")
        self.saved_patches_dir = FileUtils.join_path(self.project_out_root, 'saved-patches')
        self.dummy_patches_dir = FileUtils.join_path(self.project_out_root, 'dummy-patches')
        FileUtils.ensure_dir_created(self.project_out_root)
        FileUtils.ensure_dir_created(self.sandbox_hadoop_repo_path)
        FileUtils.ensure_dir_created(self.log_dir)

    def setUpClass(self):
        self.setup_dirs()
        Setup.init_logger(self.log_dir, console_debug=False, postfix='TEST')
        try:
            self.repo_wrapper = GitWrapper(self.sandbox_hadoop_repo_path)
            self.repo = self.repo_wrapper._repo
            LOG.info("Hadoop is already cloned.")
            self.reset_changes()
            self.checkout_trunk()
        except InvalidGitRepositoryError as e:
            LOG.info("Cloning Hadoop for the first time...")
            Repo.clone_from(HADOOP_REPO_APACHE, self.sandbox_hadoop_repo_path, progress=ProgressPrinter("clone"))

    def checkout_trunk(self):
        default_branch = 'trunk'
        LOG.info("Checking out branch: %s", default_branch)
        self.repo.heads[default_branch].checkout()
    
    def cleanup_and_checkout_test_branch(self, branch=None, remove=True):
        if not branch:
            branch = self.test_branch
        self.reset_changes()
        self.checkout_trunk()
        LOG.info("Pulling origin")
        self.repo.remotes.origin.pull()
        try:
            LOG.info("Resetting changes on branch: %s", branch)
            if branch in self.repo.heads:
                self.repo.heads[branch].checkout()
                self.repo.git.reset('--hard')
                # Checkout trunk, so branch can be deleted
                self.checkout_trunk()
                if remove:
                    self.remove_branch(branch)
        except GitCommandError:
            # Do nothing if branch not exists
            LOG.exception("Failed to remove branch.", exc_info=True)
            pass

        LOG.info("Checking out branch: %s", branch)
        self.repo.git.checkout('-b', branch)

    def reset_and_checkout_existing_branch(self, branch):
        self.reset_changes()
        self.checkout_trunk()
        LOG.info("Pulling origin")
        self.repo.remotes.origin.pull()
        LOG.info("Checking out branch: %s", branch)
        self.repo.heads[branch].checkout()

    def remove_branch(self, branch):
        LOG.info("Removing branch: %s", branch)
        self.repo.delete_head(branch, force=True)

    def reset_changes(self):
        LOG.info("Reset all changes...")
        self.repo.head.reset(commit='origin/trunk', index=True, working_tree=True)
        self.repo.git.clean('-xdf')

    def does_file_contain(self, file, string):
        with open(file) as f:
            if string in f.read():
                return True
        TESTCASE.fail("File '{}' does not contain expected string: '{}'".format(file, string))

    def add_some_file_changes(self, commit=False):
        FileUtils.save_to_file(FileUtils.join_path(self.sandbox_hadoop_repo_path, DUMMYFILE_1), DUMMYFILE_1)
        FileUtils.save_to_file(FileUtils.join_path(self.sandbox_hadoop_repo_path, DUMMYFILE_2), DUMMYFILE_2)
        yarn_config_java = FileUtils.join_path(self.sandbox_hadoop_repo_path, YARNCONFIGURATION_PATH)
        FileUtils.append_to_file(yarn_config_java, "dummy_changes_to_conf_1\n")
        FileUtils.append_to_file(yarn_config_java, "dummy_changes_to_conf_2\n")

        if commit:
            author = Actor("A test author", "unittest@example.com")
            committer = Actor("A test committer", "unittest@example.com")
            self.repo.index.add([DUMMYFILE_1, DUMMYFILE_2, yarn_config_java])
            self.repo.index.commit("test commit", author=author, committer=committer)
            # self.repo.git.commit('-am', 'test commit', author='unittest@xxx.com')

    def add_file_changes_and_save_to_patch(self, patch_file):
        self.add_some_file_changes()
        yarn_config_java = FileUtils.join_path(self.sandbox_hadoop_repo_path, YARNCONFIGURATION_PATH)
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

    def verify_commit_message_of_branch(self, branch, commit_message):
        commit = self.repo.heads[branch].commit
        TESTCASE.assertEqual(commit_message, commit.message)