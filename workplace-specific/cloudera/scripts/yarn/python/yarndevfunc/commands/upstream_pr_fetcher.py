import logging

from yarndevfunc.constants import FETCH_HEAD
from yarndevfunc.utils import StringUtils

LOG = logging.getLogger(__name__)


class UpstreamPRFetcher:
    """
    A class used to fetch upstream Pull requests and cherry-pick N number of commits onto the specified base branch.

    Attributes
    ----------
    remote_repo_url : str
        The URL of the remote github repository to fetch changes from.
        Specified with args.
    remote_branch : str
        The remote branch of the repository to fetch changes from.
        Specified with args.
    repo : GitWrapper
        A GitWrapper object, representing the repository to fetch and cherry-pick changes into.
    base_branch : str
        The refspec to use as base branch for git log comparison
    print_n_commits : int
        The number of commits to print upon fetching changes
    cherry_pick_n_commits : int
        The number of commits to cherry-pick upon fetching changes
    Methods
    -------
    run()
        Executes this command.
        The steps are roughly are:
        1. Log current branch.
        2. Fetch changes from remote repository and log commits.
        3. Cherry-pick commits.

    """

    def __init__(self, args, remote_repo_url, upstream_repo, base_branch, print_n_commits=10, cherry_pick_n_commits=1):
        self.remote_branch = args.remote_branch
        self.remote_repo_url = remote_repo_url
        self.repo = upstream_repo
        self.base_branch = base_branch
        self.print_n_commits = print_n_commits
        self.cherry_pick_n_commits = cherry_pick_n_commits

    def run(self):
        self.log_current_branch()
        self.fetch_and_log_commits()
        self.cherry_pick_commits()

    def log_current_branch(self):
        current_branch = self.repo.get_current_branch_name()
        LOG.info("Current branch: %s", current_branch)

    def fetch_and_log_commits(self):
        success = self.repo.fetch(repo_url=self.remote_repo_url, remote_name=self.remote_branch)
        if not success:
            raise ValueError(f"Cannot fetch from remote branch: {self.remote_repo_url}/{self.remote_branch}")
        log_result = self.repo.log(FETCH_HEAD, n=self.print_n_commits)
        LOG.info(
            "Printing %d topmost commits of %s:\n %s",
            self.print_n_commits,
            FETCH_HEAD,
            StringUtils.list_to_multiline_string(log_result),
        )

        base_vs_fetch_head = f"{self.base_branch}..{FETCH_HEAD}"
        log_result = self.repo.log(base_vs_fetch_head, oneline=True)
        LOG.info("\n\nPrinting diff of %s:\n %s", base_vs_fetch_head, StringUtils.list_to_multiline_string(log_result))

        num_commits = len(log_result)
        if num_commits > self.cherry_pick_n_commits:
            raise ValueError(
                f"Number of commits between {base_vs_fetch_head} is more than {self.cherry_pick_n_commits}! Exiting..."
            )

    def cherry_pick_commits(self):
        success = self.repo.cherry_pick(FETCH_HEAD)
        if not success:
            raise ValueError("Cherry-pick failed. Exiting")
        LOG.info("REMEMBER to change the commit message with command: 'git commit --amend'")
        LOG.info("REMEMBER to reset the author with command: 'git commit --amend --reset-author")
