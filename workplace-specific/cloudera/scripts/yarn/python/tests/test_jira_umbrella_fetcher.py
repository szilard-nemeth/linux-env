import logging
import unittest

from commands.upstream_jira_umbrella_fetcher import UpstreamJiraUmbrellaFetcher
from constants import TRUNK
from tests.test_utilities import TestUtilities, Object

# Umbrella: OrgQueue for easy CapacityScheduler queue configuration management
from utils import FileUtils

UPSTREAM_JIRA_ID = 'YARN-5734'
UPSTREAM_JIRA_WITH_0_SUBJIRAS = 'YARN-9629'
UPSTREAM_JIRA_NOT_EXISTING = 'YARN-1111111'
UPSTREAM_JIRA_DOES_NOT_HAVE_COMMIT = 'YARN-3525'
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

    def cleanup_and_checkout_branch(self, test_branch):
        self.utils.cleanup_and_checkout_test_branch(pull=False)
        self.assertEqual(test_branch, str(self.repo.head.ref))

    def setup_args(self, jira=UPSTREAM_JIRA_ID):
        args = Object()
        args.jira_id = jira
        return args

    def test_fetch_on_branch_other_than_trunk_fails(self):
        self.utils.checkout_parent_of_branch(TRUNK)

        # Can't use self.repo.head.ref as HEAD is a detached reference
        # self.repo.head.ref would raise: TypeError: HEAD is a detached symbolic reference as it points to
        self.assertNotEqual(self.utils.get_hash_of_commit(TRUNK), self.repo.head.commit.hexsha)
        umbrella_fetcher = UpstreamJiraUmbrellaFetcher(self.setup_args(), self.repo_wrapper, self.repo_wrapper)
        self.assertRaises(ValueError, umbrella_fetcher.run)

    def test_fetch_with_upstream_jira_that_is_not_an_umbrella_works(self):
        self.utils.checkout_trunk()
        umbrella_fetcher = UpstreamJiraUmbrellaFetcher(self.setup_args(jira=UPSTREAM_JIRA_WITH_0_SUBJIRAS), self.repo_wrapper, self.utils.jira_umbrella_data_dir)
        umbrella_fetcher.run()

    def test_fetch_with_upstream_jira_not_existing(self):
        self.utils.checkout_trunk()
        umbrella_fetcher = UpstreamJiraUmbrellaFetcher(self.setup_args(jira=UPSTREAM_JIRA_NOT_EXISTING), self.repo_wrapper, self.utils.jira_umbrella_data_dir)
        self.assertRaises(ValueError, umbrella_fetcher.run)

    def test_fetch_with_upstream_jira_that_does_not_have_commit(self):
        self.utils.checkout_trunk()
        umbrella_fetcher = UpstreamJiraUmbrellaFetcher(self.setup_args(jira=UPSTREAM_JIRA_DOES_NOT_HAVE_COMMIT),
                                                       self.repo_wrapper, self.utils.jira_umbrella_data_dir)
        self.assertRaises(ValueError, umbrella_fetcher.run)

    def test_fetch_with_upstream_umbrella(self):
        self.utils.checkout_trunk()
        umbrella_fetcher = UpstreamJiraUmbrellaFetcher(self.setup_args(),
                                                       self.repo_wrapper, self.utils.jira_umbrella_data_dir)
        umbrella_fetcher.run()

        # Verify files
        patches_basedir = FileUtils.join_path(self.utils.jira_umbrella_data_dir, UPSTREAM_JIRA_ID)
        self.utils.assert_file_not_empty(FileUtils.join_path(patches_basedir, "changed-files.txt"))
        self.utils.assert_file_not_empty(FileUtils.join_path(patches_basedir, "commit-hashes.txt"))
        self.utils.assert_file_not_empty(FileUtils.join_path(patches_basedir, "intermediate-results.txt"))
        self.utils.assert_file_not_empty(FileUtils.join_path(patches_basedir, "jira-list.txt"))
        self.utils.assert_file_not_empty(FileUtils.join_path(patches_basedir, "summary.txt"))
        self.utils.assert_file_not_empty(FileUtils.join_path(patches_basedir, "jira.html"))


if __name__ == '__main__':
    unittest.main()
