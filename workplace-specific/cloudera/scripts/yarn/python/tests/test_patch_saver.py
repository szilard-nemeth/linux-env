import logging
import os
import unittest
from os.path import expanduser

from git import Repo, InvalidGitRepositoryError, GitCommandError, Actor

from constants import HADOOP_REPO_APACHE
from git_wrapper import GitWrapper, ProgressPrinter
from commands.patch_saver import PatchSaver
from utils import FileUtils
from yarn_dev_func import Setup, YarnDevFunc

YARN_TEST_BRANCH = 'YARNTEST-1234'
YARNCONFIGURATION_PATH = "hadoop-yarn-project/hadoop-yarn/hadoop-yarn-api/src/main/java/org/apache/hadoop/yarn/conf/YarnConfiguration.java"
LOG = logging.getLogger(__name__)


class TestPatchSaver(unittest.TestCase):
    @classmethod
    def setup_dirs(cls):
        cls.project_out_root = FileUtils.join_path(expanduser("~"), "yarn_dev_func-test")
        cls.log_dir = FileUtils.join_path(cls.project_out_root, 'logs')
        cls.sandbox_hadoop_repo_path = FileUtils.join_path(cls.project_out_root, "sandbox_repo")
        cls.saved_patches_dir = FileUtils.join_path(cls.project_out_root, 'saved-patches')
        FileUtils.ensure_dir_created(cls.project_out_root)
        FileUtils.ensure_dir_created(cls.sandbox_hadoop_repo_path)
        FileUtils.ensure_dir_created(cls.log_dir)

    @classmethod
    def setUpClass(cls):
        cls.setup_dirs()
        Setup.init_logger(cls.log_dir, console_debug=False, postfix='TEST')
        try:
            cls.repo_wrapper = GitWrapper(cls.sandbox_hadoop_repo_path)
            cls.repo = cls.repo_wrapper._repo
            LOG.info("Hadoop is already cloned.")
            cls.checkout_trunk()
        except InvalidGitRepositoryError as e:
            LOG.info("Cloning Hadoop for the first time...")
            Repo.clone_from(HADOOP_REPO_APACHE, cls.sandbox_hadoop_repo_path, progress=ProgressPrinter("clone"))

    def tearDown(self):
        self.checkout_trunk()

    @classmethod
    def checkout_trunk(cls):
        default_branch = 'trunk'
        LOG.info("[TEARDOWN] Checking out branch: %s", default_branch)
        cls.repo.heads[default_branch].checkout()

    def cleanup_and_checkout_branch(self, test_branch):
        LOG.info("Reset all changes...")
        self.repo.head.reset(commit='origin/trunk', index=True, working_tree=True)
        self.repo.git.clean('-xdf')

        LOG.info("Checkout trunk")
        self.checkout_trunk()

        LOG.info("Pulling trunk")
        self.repo.remotes.origin.pull()
        try:
            LOG.info("Resetting changes on branch: %s", test_branch)
            if test_branch in self.repo.heads:
                self.repo.heads[test_branch].checkout()
                self.repo.git.reset('--hard')
                # Checkout trunk, so branch can be deleted
                self.checkout_trunk()
            LOG.info("Removing branch: %s", test_branch)
            self.repo.delete_head(test_branch, force=True)
        except GitCommandError:
            # Do nothing if branch not exists
            LOG.exception("Failed to remove branch.", exc_info=True)
            pass

        LOG.info("Checking out branch: %s", test_branch)
        self.repo.git.checkout('-b', test_branch)
        self.assertEqual(test_branch, str(self.repo.head.ref))

    def does_file_contain(self, file, str):
        with open(file) as f:
            if str in f.read():
                return True
        self.fail("File '{}' does not contain expected string: '{}'".format(file, str))

    def add_some_file_changes(self, commit=False):
        dummyfile_1 = "dummyfile1"
        dummyfile_2 = "dummyfile2"
        FileUtils.save_to_file(FileUtils.join_path(self.sandbox_hadoop_repo_path, dummyfile_1), "dummyfile1")
        FileUtils.save_to_file(FileUtils.join_path(self.sandbox_hadoop_repo_path, dummyfile_2), "dummyfile2")
        yarn_config_java = FileUtils.join_path(self.sandbox_hadoop_repo_path, YARNCONFIGURATION_PATH)
        FileUtils.append_to_file(yarn_config_java, "dummy_changes_to_conf_1\n")
        FileUtils.append_to_file(yarn_config_java, "dummy_changes_to_conf_2\n")

        if commit:
            author = Actor("A test author", "unittest@example.com")
            committer = Actor("A test committer", "unittest@example.com")
            self.repo.index.add([dummyfile_1, dummyfile_2, yarn_config_java])
            self.repo.index.commit("test commit", author=author, committer=committer)
            # self.repo.git.commit('-am', 'test commit', author='unittest@xxx.com')

    def test_save_patch_on_trunk_fails(self):
        self.repo.heads.trunk.checkout()
        self.assertEqual('trunk', str(self.repo.head.ref))
        patch_saver = PatchSaver(object(), self.repo_wrapper, self.saved_patches_dir)
        self.assertRaises(ValueError, patch_saver.run)

    def test_save_patch_on_testbranch_fails_without_changes(self):
        self.cleanup_and_checkout_branch(YARN_TEST_BRANCH)
        patch_saver = PatchSaver(object(), self.repo_wrapper, self.saved_patches_dir)
        self.assertRaises(ValueError, patch_saver.run)

    def test_save_patch_on_testbranch_fails_with_uncommitted_changes(self):
        self.cleanup_and_checkout_branch(YARN_TEST_BRANCH)
        self.add_some_file_changes(commit=False)
        patch_saver = PatchSaver(object(), self.repo_wrapper, self.saved_patches_dir)
        self.assertRaises(ValueError, patch_saver.run)

    def test_save_patch_on_testbranch_runs_with_committed_changes(self):
        self.cleanup_and_checkout_branch(YARN_TEST_BRANCH)
        self.add_some_file_changes(commit=True)
        patch_saver = PatchSaver(object(), self.repo_wrapper, self.saved_patches_dir)
        new_patch_file = patch_saver.run()

        # Verify file
        self.does_file_contain(new_patch_file, "+dummyfile1")
        self.does_file_contain(new_patch_file, "+dummyfile2")
        self.does_file_contain(new_patch_file, "+dummy_changes_to_conf_1")
        self.does_file_contain(new_patch_file, "+dummy_changes_to_conf_2")

    def test_save_patch_started_from_yarn_dev_func(self):
        self.cleanup_and_checkout_branch(YARN_TEST_BRANCH)
        self.add_some_file_changes(commit=True)

        os.environ["HADOOP_DEV_DIR"] = self.sandbox_hadoop_repo_path
        os.environ["CLOUDERA_HADOOP_ROOT"] = self.sandbox_hadoop_repo_path
        yarn_functions = YarnDevFunc()
        yarn_functions.upstream_repo = self.repo_wrapper
        yarn_functions.yarn_patch_dir = self.saved_patches_dir
        args = object()
        new_patch_file = yarn_functions.save_patch(args)

        # Verify file
        self.does_file_contain(new_patch_file, "+dummyfile1")
        self.does_file_contain(new_patch_file, "+dummyfile2")
        self.does_file_contain(new_patch_file, "+dummy_changes_to_conf_1")
        self.does_file_contain(new_patch_file, "+dummy_changes_to_conf_2")


if __name__ == '__main__':
    unittest.main()