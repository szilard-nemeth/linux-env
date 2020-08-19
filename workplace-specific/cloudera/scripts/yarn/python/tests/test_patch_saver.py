import logging
import unittest

from tests.test_utilities import TestUtilities
from yarndevfunc.commands.patch_saver import PatchSaver
from yarndevfunc.constants import TRUNK
from yarndevfunc.yarn_dev_func import YarnDevFunc

YARN_TEST_BRANCH = "YARNTEST-1234"
LOG = logging.getLogger(__name__)


class TestPatchSaver(unittest.TestCase):
    repo = None
    log_dir = None
    sandbox_hadoop_repo_path = None

    @classmethod
    def setUpClass(cls):
        cls.utils = TestUtilities(cls, YARN_TEST_BRANCH)
        cls.utils.setUpClass()
        cls.utils.pull_to_trunk()
        cls.repo = cls.utils.repo
        cls.repo_wrapper = cls.utils.repo_wrapper
        cls.saved_patches_dir = cls.utils.saved_patches_dir
        cls.base_branch = TRUNK

    def cleanup_and_checkout_branch(self, test_branch):
        self.utils.cleanup_and_checkout_test_branch(pull=False)
        self.assertEqual(test_branch, str(self.repo.head.ref))

    def test_save_patch_on_trunk_fails(self):
        self.repo.heads.trunk.checkout()
        self.assertEqual("trunk", str(self.repo.head.ref))
        patch_saver = PatchSaver(object(), self.repo_wrapper, self.saved_patches_dir, self.base_branch)
        self.assertRaises(ValueError, patch_saver.run)

    def test_save_patch_on_testbranch_fails_without_changes(self):
        self.cleanup_and_checkout_branch(YARN_TEST_BRANCH)
        patch_saver = PatchSaver(object(), self.repo_wrapper, self.saved_patches_dir, self.base_branch)
        self.assertRaises(ValueError, patch_saver.run)

    def test_save_patch_on_testbranch_fails_with_uncommitted_changes(self):
        self.cleanup_and_checkout_branch(YARN_TEST_BRANCH)
        self.utils.add_some_file_changes(commit=False)
        patch_saver = PatchSaver(object(), self.repo_wrapper, self.saved_patches_dir, self.base_branch)
        self.assertRaises(ValueError, patch_saver.run)

    def test_save_patch_on_testbranch_runs_with_committed_changes(self):
        self.cleanup_and_checkout_branch(YARN_TEST_BRANCH)
        self.utils.add_some_file_changes(commit=True)
        patch_saver = PatchSaver(object(), self.repo_wrapper, self.saved_patches_dir, self.base_branch)
        new_patch_file = patch_saver.run()

        # Verify file
        self.utils.does_file_contain(new_patch_file, "+dummyfile1")
        self.utils.does_file_contain(new_patch_file, "+dummyfile2")
        self.utils.does_file_contain(new_patch_file, "+dummy_changes_to_conf_1")
        self.utils.does_file_contain(new_patch_file, "+dummy_changes_to_conf_2")

    def test_save_patch_started_from_yarn_dev_func(self):
        self.cleanup_and_checkout_branch(YARN_TEST_BRANCH)
        self.utils.add_some_file_changes(commit=True)

        self.utils.set_env_vars(self.utils.sandbox_repo_path, self.utils.sandbox_repo_path)
        yarn_functions = YarnDevFunc()
        yarn_functions.upstream_repo = self.repo_wrapper
        yarn_functions.yarn_patch_dir = self.saved_patches_dir
        args = object()
        new_patch_file = yarn_functions.save_patch(args)

        # Verify file
        self.utils.does_file_contain(new_patch_file, "+dummyfile1")
        self.utils.does_file_contain(new_patch_file, "+dummyfile2")
        self.utils.does_file_contain(new_patch_file, "+dummy_changes_to_conf_1")
        self.utils.does_file_contain(new_patch_file, "+dummy_changes_to_conf_2")


if __name__ == "__main__":
    unittest.main()
