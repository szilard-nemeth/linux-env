import logging
import unittest

from tests.test_utilities import TestUtilities, Object
from yarndevfunc.commands.backporter import Backporter
from yarndevfunc.constants import TRUNK, BRANCH_3_1, ORIGIN
from yarndevfunc.yarn_dev_func import DEFAULT_BASE_BRANCH

UPSTREAM_JIRA_ID = "YARN-123456: "
CDH_BRANCH = "cdh6x"
CDH_JIRA_ID = "CDH-1234"
UPSTREAM_REMOTE_NAME = "upstream"

LOG = logging.getLogger(__name__)

# Commit should be in trunk, this is a prerequisite of the backporter
YARN_TEST_BRANCH = TRUNK
CHERRY_PICK_BASE_REF = TRUNK


class TestBackporter(unittest.TestCase):
    upstream_repo = None
    log_dir = None
    sandbox_hadoop_repo_path = None

    @classmethod
    def setUpClass(cls):
        cls.upstream_utils = TestUtilities(cls, YARN_TEST_BRANCH)
        cls.upstream_utils.setUpClass()
        cls.upstream_utils.pull_to_trunk()
        cls.upstream_repo = cls.upstream_utils.repo
        cls.upstream_repo_wrapper = cls.upstream_utils.repo_wrapper

        cls.downstream_utils = TestUtilities(cls, YARN_TEST_BRANCH)
        cls.downstream_utils.setUpClass(repo_postfix="_downstream", init_logging=False)
        cls.downstream_utils.pull_to_trunk()
        cls.downstream_repo = cls.downstream_utils.repo
        cls.downstream_repo_wrapper = cls.downstream_utils.repo_wrapper

        cls.full_cdh_branch = f"{CDH_JIRA_ID}-{CDH_BRANCH}"

        # Setup committer config
        cls.downstream_utils.prepare_git_config("downstream_user", "downstream_email")

        # Setup debug logging of git commands
        cls.downstream_repo_wrapper.enable_debug_logging(full=True)

    def setUp(self):
        self.upstream_utils.reset_and_checkout_existing_branch(YARN_TEST_BRANCH, pull=False)

        # THIS IS A MUST HAVE!
        # Set up remote of upstream in the downstream repo
        self.downstream_utils.add_remote(UPSTREAM_REMOTE_NAME, self.upstream_repo.git_dir)
        self.downstream_utils.remove_branch(self.full_cdh_branch)

    def setup_args(self):
        args = Object()
        args.upstream_jira_id = UPSTREAM_JIRA_ID
        args.upstream_branch = DEFAULT_BASE_BRANCH
        args.cdh_jira_id = CDH_JIRA_ID
        args.cdh_branch = CDH_BRANCH
        return args

    def cleanup_and_checkout_branch(self, branch=None, checkout_from=None):
        if branch:
            self.upstream_utils.cleanup_and_checkout_test_branch(pull=False, branch=branch, checkout_from=checkout_from)
            self.assertEqual(branch, str(self.upstream_repo.head.ref))
        else:
            self.upstream_utils.cleanup_and_checkout_test_branch(pull=False, checkout_from=checkout_from)
            self.assertEqual(YARN_TEST_BRANCH, str(self.upstream_repo.head.ref))

    def test_with_uncommitted_should_raise_error(self):
        self.upstream_utils.add_some_file_changes(commit=False)
        args = self.setup_args()

        backporter = Backporter(
            args, self.upstream_repo_wrapper, self.downstream_repo_wrapper, CHERRY_PICK_BASE_REF, YARN_TEST_BRANCH
        )
        self.assertRaises(ValueError, backporter.run)

    def test_with_committed_with_wrong_message_should_raise_error(self):
        self.cleanup_and_checkout_branch()
        self.upstream_utils.add_some_file_changes(commit=True, commit_message_prefix="dummy")
        args = self.setup_args()

        backporter = Backporter(
            args, self.upstream_repo_wrapper, self.downstream_repo_wrapper, CHERRY_PICK_BASE_REF, YARN_TEST_BRANCH
        )
        self.assertRaises(ValueError, backporter.run)

    def test_with_committed_with_good_message_remote_to_upstream_does_not_exist(self):
        self.cleanup_and_checkout_branch()
        self.upstream_utils.add_some_file_changes(commit=True, commit_message_prefix=UPSTREAM_JIRA_ID)
        args = self.setup_args()

        # Intentionally remove remote
        self.downstream_utils.remove_remote(UPSTREAM_REMOTE_NAME)

        backporter = Backporter(
            args, self.upstream_repo_wrapper, self.downstream_repo_wrapper, CHERRY_PICK_BASE_REF, YARN_TEST_BRANCH
        )
        self.assertRaises(ValueError, backporter.run)

    def test_with_committed_with_good_message(self):
        self.cleanup_and_checkout_branch()
        self.upstream_utils.add_some_file_changes(commit=True, commit_message_prefix=UPSTREAM_JIRA_ID)
        args = self.setup_args()

        backporter = Backporter(
            args, self.upstream_repo_wrapper, self.downstream_repo_wrapper, CHERRY_PICK_BASE_REF, YARN_TEST_BRANCH
        )
        backporter.run()

        expected_commit_msg = f"{CDH_JIRA_ID}: {UPSTREAM_JIRA_ID}test_commit"
        self.assertTrue(
            self.full_cdh_branch in self.downstream_repo.heads,
            f"Created downstream branch does not exist: {self.full_cdh_branch}",
        )
        self.downstream_utils.verify_commit_message_of_branch(
            self.full_cdh_branch, expected_commit_msg, verify_cherry_picked_from=True
        )

    def test_backport_from_branch31(self):
        self.cleanup_and_checkout_branch(branch=BRANCH_3_1, checkout_from=ORIGIN + "/" + BRANCH_3_1)
        self.upstream_utils.add_some_file_changes(commit=True, commit_message_prefix=UPSTREAM_JIRA_ID)
        args = self.setup_args()
        args.upstream_branch = BRANCH_3_1

        backporter = Backporter(
            args, self.upstream_repo_wrapper, self.downstream_repo_wrapper, CHERRY_PICK_BASE_REF, BRANCH_3_1
        )
        backporter.run()

        expected_commit_msg = f"{CDH_JIRA_ID}: {UPSTREAM_JIRA_ID}test_commit"
        self.assertTrue(
            self.full_cdh_branch in self.downstream_repo.heads,
            f"Created downstream branch does not exist: {self.full_cdh_branch}",
        )
        self.downstream_utils.verify_commit_message_of_branch(
            self.full_cdh_branch, expected_commit_msg, verify_cherry_picked_from=True
        )
