import logging
import unittest

from yarndevfunc.commands.upstream_pr_fetcher import UpstreamPRFetcher
from yarndevfunc.constants import APACHE, TRUNK, HADOOP_REPO_TEMPLATE
from tests.test_utilities import TestUtilities, Object

DEFAULT_BRANCH = TRUNK

LOG = logging.getLogger(__name__)


class TestUpstreamPRFetcher(unittest.TestCase):
    repo = None
    log_dir = None
    sandbox_hadoop_repo_path = None

    @classmethod
    def setUpClass(cls):
        cls.utils = TestUtilities(cls, "dummy")
        cls.utils.setUpClass()
        cls.utils.pull_to_trunk()
        cls.repo = cls.utils.repo
        cls.repo_wrapper = cls.utils.repo_wrapper
        cls.base_branch = cls.utils.checkout_parent_of_branch(DEFAULT_BRANCH)

    def setUp(self):
        self.utils.reset_and_checkout_existing_branch(DEFAULT_BRANCH, pull=False)
        # Setup committer config
        self.utils.prepare_git_config("upstream_user", "upstream_email")

    def test_with_wrong_repo_url(self):
        args = Object()
        args.remote_branch = "dummy"

        pr_fetcher = UpstreamPRFetcher(
            args, HADOOP_REPO_TEMPLATE.format(user="dummyxyz12345"), self.repo_wrapper, self.base_branch
        )
        self.assertRaises(ValueError, pr_fetcher.run)

    def test_with_wrong_remote_name(self):
        args = Object()
        args.remote_branch = "dummyxyz12345"

        pr_fetcher = UpstreamPRFetcher(
            args, HADOOP_REPO_TEMPLATE.format(user=APACHE), self.repo_wrapper, self.base_branch
        )
        self.assertRaises(ValueError, pr_fetcher.run)

    def test_with_valid_url_and_remote_diff_is_more_than_one_commit(self):
        args = Object()
        args.remote_branch = "branch-3.2"

        pr_fetcher = UpstreamPRFetcher(
            args, HADOOP_REPO_TEMPLATE.format(user=APACHE), self.repo_wrapper, self.base_branch
        )
        self.assertRaises(ValueError, pr_fetcher.run)

    def test_with_valid_url_and_remote_one_commit_missing_git_config(self):
        args = Object()
        args.remote_branch = DEFAULT_BRANCH

        # Intentionally remove git config
        self.utils.remove_comitter_git_config()

        pr_fetcher = UpstreamPRFetcher(
            args, HADOOP_REPO_TEMPLATE.format(user=APACHE), self.repo_wrapper, self.base_branch
        )
        self.assertRaises(ValueError, pr_fetcher.run)

    def test_with_valid_url_and_remote_one_commit_proper_git_config(self):
        args = Object()
        args.remote_branch = DEFAULT_BRANCH
        self.utils.checkout_parent_of_branch(DEFAULT_BRANCH)

        pr_fetcher = UpstreamPRFetcher(
            args, HADOOP_REPO_TEMPLATE.format(user=APACHE), self.repo_wrapper, self.base_branch
        )
        pr_fetcher.run()


if __name__ == "__main__":
    unittest.main()
