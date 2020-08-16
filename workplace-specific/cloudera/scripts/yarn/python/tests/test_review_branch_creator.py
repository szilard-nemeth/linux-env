import logging
import unittest

from commands.review_branch_creator import ReviewBranchCreator
from tests.test_utilities import TestUtilities, Object
from utils import FileUtils
from yarn_dev_func import YarnDevFunc

LOG = logging.getLogger(__name__)
YARN_TEST_BRANCH = 'YARNTEST-12345'


class TestReviewBranchCreator(unittest.TestCase):
    repo = None
    log_dir = None
    sandbox_hadoop_repo_path = None

    @classmethod
    def setUpClass(cls):
        cls.utils = TestUtilities(cls, YARN_TEST_BRANCH)
        cls.utils.setUpClass()
        cls.repo = cls.utils.repo
        cls.repo_wrapper = cls.utils.repo_wrapper
        cls.saved_patches_dir = cls.utils.saved_patches_dir
        cls.dummy_patches_dir = cls.utils.dummy_patches_dir

    def cleanup_and_checkout_branch(self, test_branch):
        self.utils.cleanup_and_checkout_branch()
        self.assertEqual(test_branch, str(self.repo.head.ref))

    def test_with_not_existing_patch(self):
        args = Object()
        args.patch_file = "/tmp/blablabla"
        review_branch_creator = ReviewBranchCreator(args, self.repo_wrapper)
        self.assertRaises(ValueError, review_branch_creator.run)

    def test_with_oddly_named_patch(self):
        args = Object()
        patch_file = FileUtils.join_path(self.dummy_patches_dir, "testpatch1.patch")
        FileUtils.create_files(patch_file)
        args.patch_file = patch_file

        review_branch_creator = ReviewBranchCreator(args, self.repo_wrapper)
        self.assertRaises(ValueError, review_branch_creator.run)

    def test_with_bad_patch_content(self):
        args = Object()
        patch_file = FileUtils.join_path(self.dummy_patches_dir, "YARN-12345.001.patch")
        FileUtils.save_to_file(patch_file, "dummycontents")
        args.patch_file = patch_file

        review_branch_creator = ReviewBranchCreator(args, self.repo_wrapper)
        self.assertRaises(ValueError, review_branch_creator.run)

    def test_with_normal_patch(self):
        review_branch = "review-YARN-12345"
        patch_file_name = "YARN-12345.001.patch"

        self.utils.reset_changes()
        self.utils.remove_branch(review_branch)

        args = Object()
        patch_file = FileUtils.join_path(self.dummy_patches_dir, patch_file_name)
        self.utils.add_file_changes_and_save_to_patch(patch_file)
        args.patch_file = patch_file

        review_branch_creator = ReviewBranchCreator(args, self.repo_wrapper)
        review_branch_creator.run()
        self.assertTrue(review_branch in self.repo.heads, "Review branch does not exist: {}".format(review_branch))

        commit = self.repo.heads[review_branch].commit
        expected_message = "patch file: {file}".format(file=patch_file)
        self.assertEqual(expected_message, commit.message)

    def test_with_normal_patch_from_yarn_dev_func(self):
        review_branch = "review-YARN-12345"
        patch_file_name = "YARN-12345.001.patch"

        self.cleanup_and_checkout_branch(YARN_TEST_BRANCH)
        self.utils.add_some_file_changes(commit=False)

        self.utils.set_env_vars(self.utils.sandbox_hadoop_repo_path, self.utils.sandbox_hadoop_repo_path)
        yarn_functions = YarnDevFunc()
        yarn_functions.upstream_repo = self.repo_wrapper

        args = Object()
        patch_file = FileUtils.join_path(self.dummy_patches_dir, patch_file_name)
        self.utils.add_file_changes_and_save_to_patch(patch_file)
        args.patch_file = patch_file

        yarn_functions.create_review_branch(args)

        self.assertTrue(review_branch in self.repo.heads, "Review branch does not exist: {}".format(review_branch))
        commit = self.repo.heads[review_branch].commit
        expected_message = "patch file: {file}".format(file=patch_file)
        self.assertEqual(expected_message, commit.message)

