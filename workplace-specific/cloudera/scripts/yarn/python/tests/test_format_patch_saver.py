import logging
import unittest

from commands.format_patch_saver import FormatPatchSaver
from commands.patch_saver import PatchSaver
from constants import TRUNK
from tests.test_utilities import TestUtilities, Object
from utils import FileUtils, DateTimeUtils
from yarn_dev_func import YarnDevFunc

YARN_TEST_BRANCH = 'YARNTEST-1234567'
DEST_DIR_PREFIX = "test"
LOG = logging.getLogger(__name__)


class TestFormatPatchSaver(unittest.TestCase):
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

    def setUp(self):
        self.current_datetime = DateTimeUtils.get_current_datetime()

    def cleanup_and_checkout_branch(self, test_branch):
        self.utils.cleanup_and_checkout_test_branch(pull=False)
        self.assertEqual(test_branch, str(self.repo.head.ref))

    def setup_args(self, base_ref=TRUNK, other_ref=TRUNK):
        args = Object()
        args.base_refspec = base_ref
        args.other_refspec = other_ref
        args.dest_basedir = self.saved_patches_dir
        args.dest_dir_prefix = DEST_DIR_PREFIX
        return args

    def test_run_in_a_non_git_repo_working_dir(self):
        working_dir = FileUtils.join_path("/tmp", "dummydir")
        FileUtils.ensure_dir_created(working_dir)

        format_patch_saver = FormatPatchSaver(self.setup_args(), working_dir, self.current_datetime)
        self.assertRaises(ValueError, format_patch_saver.run)

    def test_wrong_base_refspec(self):
        format_patch_saver = FormatPatchSaver(self.setup_args(base_ref="dummy"), self.repo.working_dir, self.current_datetime)
        self.assertRaises(ValueError, format_patch_saver.run)

    def test_wrong_other_refspec(self):
        format_patch_saver = FormatPatchSaver(self.setup_args(other_ref="dummy"), self.repo.working_dir, self.current_datetime)
        self.assertRaises(ValueError, format_patch_saver.run)

    def test_base_and_other_refs_are_same(self):
        format_patch_saver = FormatPatchSaver(self.setup_args(base_ref=TRUNK, other_ref=TRUNK), self.repo.working_dir, self.current_datetime)
        self.assertRaises(ValueError, format_patch_saver.run)

    def test_base_and_other_refs_are_valid(self):
        format_patch_saver = FormatPatchSaver(self.setup_args(base_ref=TRUNK + "^", other_ref=TRUNK), self.repo.working_dir, self.current_datetime)
        format_patch_saver.run()

        # Verify files
        patches_basedir = FileUtils.join_path(self.saved_patches_dir, DEST_DIR_PREFIX, self.current_datetime)
        self.utils.assert_files_not_empty(patches_basedir, expected_files=1)

    def test_base_and_other_refs_are_valid_more_commits(self):
        parent_level = 5
        format_patch_saver = FormatPatchSaver(self.setup_args(base_ref=TRUNK + "^" * parent_level, other_ref=TRUNK), self.repo.working_dir, self.current_datetime)
        format_patch_saver.run()

        # Verify files
        patches_basedir = FileUtils.join_path(self.saved_patches_dir, DEST_DIR_PREFIX, self.current_datetime)
        self.utils.assert_files_not_empty(patches_basedir, expected_files=5)

if __name__ == '__main__':
    unittest.main()
