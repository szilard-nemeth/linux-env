import logging
import unittest

from pythoncommons.file_utils import FileUtils

from yarndevfunc.commands.review_branch_creator import ReviewBranchCreator
from yarndevfunc.constants import TRUNK, ORIGIN_TRUNK
from tests.test_utilities import TestUtilities, Object
from yarndevfunc.yarn_dev_func import YarnDevFunc

LOG = logging.getLogger(__name__)
COMMIT_MSG_TEMPLATE = "patch file: {file}"
PATCH_FILENAME = "YARN-12345.001.patch"
REVIEW_BRANCH = "review-YARN-12345"
YARN_TEST_BRANCH = "YARNTEST-12345"
REMOTE_BASE_BRANCH = ORIGIN_TRUNK
BASE_BRANCH = TRUNK


class TestReviewBranchCreator(unittest.TestCase):
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
        cls.dummy_patches_dir = cls.utils.dummy_patches_dir

    def setUp(self):
        self.utils.reset_and_checkout_existing_branch(BASE_BRANCH, pull=False)
        self.utils.remove_branches(REVIEW_BRANCH)

    def cleanup_and_checkout_branch(self):
        self.utils.cleanup_and_checkout_test_branch(pull=False)
        self.assertEqual(YARN_TEST_BRANCH, str(self.repo.head.ref))

    def test_with_not_existing_patch(self):
        args = Object()
        args.patch_file = FileUtils.join_path("tmp", "blablabla")
        review_branch_creator = ReviewBranchCreator(args, self.repo_wrapper, BASE_BRANCH, REMOTE_BASE_BRANCH)
        self.assertRaises(ValueError, review_branch_creator.run)

    def test_with_oddly_named_patch(self):
        patch_file = FileUtils.join_path(self.dummy_patches_dir, "testpatch1.patch")
        FileUtils.create_files(patch_file)
        args = Object()
        args.patch_file = patch_file

        review_branch_creator = ReviewBranchCreator(args, self.repo_wrapper, BASE_BRANCH, REMOTE_BASE_BRANCH)
        self.assertRaises(ValueError, review_branch_creator.run)

    def test_with_bad_patch_content(self):
        patch_file = FileUtils.join_path(self.dummy_patches_dir, "YARN-12345.001.patch")
        FileUtils.save_to_file(patch_file, "dummycontents")
        args = Object()
        args.patch_file = patch_file

        review_branch_creator = ReviewBranchCreator(args, self.repo_wrapper, BASE_BRANCH, REMOTE_BASE_BRANCH)
        self.assertRaises(ValueError, review_branch_creator.run)

    def test_with_normal_patch(self):
        patch_file = FileUtils.join_path(self.dummy_patches_dir, PATCH_FILENAME)
        self.utils.add_file_changes_and_save_to_patch(patch_file)
        args = Object()
        args.patch_file = patch_file

        review_branch_creator = ReviewBranchCreator(args, self.repo_wrapper, BASE_BRANCH, REMOTE_BASE_BRANCH)
        review_branch_creator.run()

        self.assertTrue(REVIEW_BRANCH in self.repo.heads, f"Review branch does not exist: {REVIEW_BRANCH}")
        self.utils.verify_commit_message_of_branch(REVIEW_BRANCH, COMMIT_MSG_TEMPLATE.format(file=patch_file))

    def test_with_normal_patch_two_consecutive_branches(self):
        patch_file = FileUtils.join_path(self.dummy_patches_dir, PATCH_FILENAME)
        self.utils.add_file_changes_and_save_to_patch(patch_file)
        args = Object()
        args.patch_file = patch_file

        review_branch_creator = ReviewBranchCreator(args, self.repo_wrapper, BASE_BRANCH, REMOTE_BASE_BRANCH)
        review_branch_creator.run()
        review_branch_creator.run()

        branch_2 = REVIEW_BRANCH + "-2"
        self.assertTrue(REVIEW_BRANCH in self.repo.heads, f"Review branch does not exist: {REVIEW_BRANCH}")
        self.assertTrue(branch_2 in self.repo.heads, f"Review branch does not exist: {branch_2}")
        self.utils.verify_commit_message_of_branch(REVIEW_BRANCH, COMMIT_MSG_TEMPLATE.format(file=patch_file))
        self.utils.verify_commit_message_of_branch(branch_2, COMMIT_MSG_TEMPLATE.format(file=patch_file))

    def test_with_normal_patch_from_yarn_dev_func(self):
        self.cleanup_and_checkout_branch()
        self.utils.add_some_file_changes(commit=False)

        self.utils.set_env_vars(self.utils.sandbox_repo_path, self.utils.sandbox_repo_path)
        yarn_functions = YarnDevFunc()
        yarn_functions.upstream_repo = self.repo_wrapper

        args = Object()
        patch_file = FileUtils.join_path(self.dummy_patches_dir, PATCH_FILENAME)
        self.utils.add_file_changes_and_save_to_patch(patch_file)
        args.patch_file = patch_file

        yarn_functions.create_review_branch(args)

        self.assertTrue(REVIEW_BRANCH in self.repo.heads, f"Review branch does not exist: {REVIEW_BRANCH}")
        self.utils.verify_commit_message_of_branch(REVIEW_BRANCH, COMMIT_MSG_TEMPLATE.format(file=patch_file))
