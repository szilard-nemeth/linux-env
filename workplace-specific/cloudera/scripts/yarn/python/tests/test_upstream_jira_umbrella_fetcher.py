import logging
import unittest

from pythoncommons.file_utils import FileUtils

from yarndevfunc.commands.upstream_jira_umbrella_fetcher import UpstreamJiraUmbrellaFetcher
from yarndevfunc.constants import TRUNK
from tests.test_utilities import TestUtilities, Object

# Umbrella: OrgQueue for easy CapacityScheduler queue configuration management

FILE_JIRA_HTML = "jira.html"
FILE_SUMMARY = "summary.txt"
FILE_JIRA_LIST = "jira-list.txt"
FILE_INTERMEDIATE_RESULTS = "intermediate-results.txt"
FILE_COMMIT_HASHES = "commit-hashes.txt"
FILE_CHANGED_FILES = "changed-files.txt"
ALL_OUTPUT_FILES = [
    FILE_JIRA_HTML,
    FILE_SUMMARY,
    FILE_JIRA_LIST,
    FILE_INTERMEDIATE_RESULTS,
    FILE_COMMIT_HASHES,
    FILE_CHANGED_FILES,
]

UPSTREAM_JIRA_ID = "YARN-5734"
UPSTREAM_JIRA_WITH_0_SUBJIRAS = "YARN-9629"
UPSTREAM_JIRA_NOT_EXISTING = "YARN-1111111"
UPSTREAM_JIRA_DOES_NOT_HAVE_COMMIT = "YARN-3525"
LOG = logging.getLogger(__name__)


class TestUpstreamJiraUmbrellaFetcher(unittest.TestCase):
    repo = None
    log_dir = None
    sandbox_hadoop_repo_path = None

    @classmethod
    def setUpClass(cls):
        cls.utils = TestUtilities(cls, None)
        cls.utils.setUpClass()
        cls.utils.pull_to_trunk()
        cls.repo = cls.utils.repo
        cls.repo_wrapper = cls.utils.repo_wrapper
        cls.saved_patches_dir = cls.utils.saved_patches_dir
        cls.base_branch = TRUNK

    def cleanup_and_checkout_branch(self, test_branch):
        self.utils.cleanup_and_checkout_test_branch(pull=False)
        self.assertEqual(test_branch, str(self.repo.head.ref))

    def setup_args(self, jira=UPSTREAM_JIRA_ID, force_mode=False):
        args = Object()
        args.jira_id = jira
        args.force_mode = force_mode
        return args

    def test_fetch_on_branch_other_than_trunk_fails(self):
        self.utils.checkout_parent_of_branch(self.base_branch)

        # Can't use self.repo.head.ref as HEAD is a detached reference
        # self.repo.head.ref would raise: TypeError: HEAD is a detached symbolic reference as it points to
        self.assertNotEqual(self.utils.get_hash_of_commit(self.base_branch), self.repo.head.commit.hexsha)
        umbrella_fetcher = UpstreamJiraUmbrellaFetcher(
            self.setup_args(), self.repo_wrapper, self.repo_wrapper, self.repo_wrapper, self.base_branch
        )
        self.assertRaises(ValueError, umbrella_fetcher.run)

    def test_fetch_with_upstream_jira_that_is_not_an_umbrella_works(self):
        self.utils.checkout_trunk()
        umbrella_fetcher = UpstreamJiraUmbrellaFetcher(
            self.setup_args(jira=UPSTREAM_JIRA_WITH_0_SUBJIRAS),
            self.repo_wrapper,
            self.repo_wrapper,
            self.utils.jira_umbrella_data_dir,
            self.base_branch,
        )
        umbrella_fetcher.run()

    def test_fetch_with_upstream_jira_not_existing(self):
        self.utils.checkout_trunk()
        umbrella_fetcher = UpstreamJiraUmbrellaFetcher(
            self.setup_args(jira=UPSTREAM_JIRA_NOT_EXISTING),
            self.repo_wrapper,
            self.repo_wrapper,
            self.utils.jira_umbrella_data_dir,
            self.base_branch,
        )
        self.assertRaises(ValueError, umbrella_fetcher.run)

    def test_fetch_with_upstream_jira_that_does_not_have_commit(self):
        self.utils.checkout_trunk()
        umbrella_fetcher = UpstreamJiraUmbrellaFetcher(
            self.setup_args(jira=UPSTREAM_JIRA_DOES_NOT_HAVE_COMMIT),
            self.repo_wrapper,
            self.repo_wrapper,
            self.utils.jira_umbrella_data_dir,
            self.base_branch,
        )
        self.assertRaises(ValueError, umbrella_fetcher.run)

    def test_fetch_with_upstream_umbrella_cached_mode(self):
        self.utils.checkout_trunk()
        umbrella_fetcher = UpstreamJiraUmbrellaFetcher(
            self.setup_args(force_mode=False),
            self.repo_wrapper,
            self.repo_wrapper,
            self.utils.jira_umbrella_data_dir,
            self.base_branch,
        )
        # Run first, to surely have results pickled for this umbrella
        umbrella_fetcher.run()

        # Run again, with using cache
        umbrella_fetcher.run()

        output_dir = FileUtils.join_path(self.utils.jira_umbrella_data_dir, UPSTREAM_JIRA_ID)
        original_mod_dates = FileUtils.get_mod_dates_of_files(output_dir, *ALL_OUTPUT_FILES)

        # Verify files and mod dates
        for out_file in ALL_OUTPUT_FILES:
            self.utils.assert_file_not_empty(FileUtils.join_path(output_dir, out_file))

        # Since we are using non-force mode (cached mode), we expect the files untouched
        new_mod_dates = FileUtils.get_mod_dates_of_files(output_dir, *ALL_OUTPUT_FILES)
        self.assertDictEqual(original_mod_dates, new_mod_dates)

    def test_fetch_with_upstream_umbrella_force_mode(self):
        self.utils.checkout_trunk()
        output_dir = FileUtils.join_path(self.utils.jira_umbrella_data_dir, UPSTREAM_JIRA_ID)
        original_mod_dates = FileUtils.get_mod_dates_of_files(output_dir, *ALL_OUTPUT_FILES)
        umbrella_fetcher = UpstreamJiraUmbrellaFetcher(
            self.setup_args(force_mode=True),
            self.repo_wrapper,
            self.repo_wrapper,
            self.utils.jira_umbrella_data_dir,
            self.base_branch,
        )
        umbrella_fetcher.run()

        # Verify files and mod dates
        for out_file in ALL_OUTPUT_FILES:
            self.utils.assert_file_not_empty(FileUtils.join_path(output_dir, out_file))

        # Since we are using force-mode (non cached mode), we expect all files have a newer mod date
        new_mod_dates = FileUtils.get_mod_dates_of_files(output_dir, *ALL_OUTPUT_FILES)
        for file, mod_date in new_mod_dates.items():
            self.assertTrue(mod_date > original_mod_dates[file], f"File has not been modified: {file}")


if __name__ == "__main__":
    unittest.main()
