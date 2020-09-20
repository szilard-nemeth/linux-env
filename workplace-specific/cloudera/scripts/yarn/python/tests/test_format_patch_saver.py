import logging
import unittest

from pythoncommons.date_utils import DateUtils
from pythoncommons.file_utils import FileUtils

from yarndevfunc.commands.format_patch_saver import FormatPatchSaver
from yarndevfunc.constants import TRUNK, DEST_DIR_PREFIX
from tests.test_utilities import TestUtilities, Object

DEFAULT_BASE_BRANCH = TRUNK

FORMAT_PATCH_FILE_PREFIX = "000.*"

YARN_TEST_BRANCH = "YARNTEST-1234567"
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
        self.current_datetime = DateUtils.get_current_datetime()
        self.patches_basedir = FileUtils.join_path(self.saved_patches_dir, DEST_DIR_PREFIX, self.current_datetime)
        self.assertIsNotNone(self.patches_basedir)
        self.assertNotEqual(self.patches_basedir, "~")
        self.assertNotEqual(self.patches_basedir, "/")
        self.assertTrue(self.saved_patches_dir in self.patches_basedir)
        FileUtils.remove_files(self.patches_basedir, FORMAT_PATCH_FILE_PREFIX)

    def cleanup_and_checkout_branch(self, test_branch):
        self.utils.cleanup_and_checkout_test_branch(pull=False)
        self.assertEqual(test_branch, str(self.repo.head.ref))

    def setup_args(self, base_ref=DEFAULT_BASE_BRANCH, other_ref=DEFAULT_BASE_BRANCH):
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
        format_patch_saver = FormatPatchSaver(
            self.setup_args(base_ref="dummy"), self.repo.working_dir, self.current_datetime
        )
        self.assertRaises(ValueError, format_patch_saver.run)

    def test_wrong_other_refspec(self):
        format_patch_saver = FormatPatchSaver(
            self.setup_args(other_ref="dummy"), self.repo.working_dir, self.current_datetime
        )
        self.assertRaises(ValueError, format_patch_saver.run)

    def test_base_and_other_refs_are_same(self):
        format_patch_saver = FormatPatchSaver(
            self.setup_args(base_ref=DEFAULT_BASE_BRANCH, other_ref=DEFAULT_BASE_BRANCH),
            self.repo.working_dir,
            self.current_datetime,
        )
        self.assertRaises(ValueError, format_patch_saver.run)

    def test_base_and_other_refs_are_valid(self):
        format_patch_saver = FormatPatchSaver(
            self.setup_args(base_ref=DEFAULT_BASE_BRANCH + "^", other_ref=DEFAULT_BASE_BRANCH),
            self.repo.working_dir,
            self.current_datetime,
        )
        format_patch_saver.run()

        # Verify files
        self.utils.assert_files_not_empty(self.patches_basedir, expected_files=1)

    def test_base_and_other_refs_are_valid_more_commits(self):
        LOG.debug(
            "Found files in patches output dir: %s",
            FileUtils.find_files(self.patches_basedir, regex=".*", single_level=True, full_path_result=True),
        )
        parent_level = 5
        format_patch_saver = FormatPatchSaver(
            self.setup_args(base_ref=DEFAULT_BASE_BRANCH + "^" * parent_level, other_ref=DEFAULT_BASE_BRANCH),
            self.repo.working_dir,
            self.current_datetime,
        )
        format_patch_saver.run()

        # Verify files
        self.utils.assert_files_not_empty(self.patches_basedir, expected_files=5)


if __name__ == "__main__":
    unittest.main()
