import logging

from constants import HADOOP_REPO_TEMPLATE, FETCH_HEAD

LOG = logging.getLogger(__name__)


class UpstreamPRFetcher:
    def __init__(self, args, upstream_repo, base_branch):
        self.github_username = args.github_username
        self.remote_branch = args.remote_branch
        self.upstream_repo = upstream_repo
        self.base_branch = base_branch

    def run(self):
        curr_branch = self.upstream_repo.get_current_branch_name()
        LOG.info("Current branch: %s", curr_branch)

        repo_url = HADOOP_REPO_TEMPLATE.format(user=self.github_username)
        success = self.upstream_repo.fetch(repo_url=repo_url, remote_name=self.remote_branch)
        if not success:
            raise ValueError("Cannot fetch from remote branch: {url}/{remote}".format(url=repo_url, remote=self.remote_branch))

        log_result = self.upstream_repo.log(FETCH_HEAD, n=10)
        LOG.info("Printing 10 topmost commits of %s:\n %s", FETCH_HEAD, '\n'.join(log_result))

        base_vs_fetch_head = '{}..{}'.format(self.base_branch, FETCH_HEAD)
        log_result = self.upstream_repo.log(base_vs_fetch_head, oneline=True)
        LOG.info("\n\nPrinting diff of %s:\n %s", base_vs_fetch_head, '\n'.join(log_result))

        num_commits = len(log_result)
        if num_commits > 1:
            raise ValueError("Number of commits between {} is more than 1! Exiting...".format(base_vs_fetch_head))

        success = self.upstream_repo.cherry_pick(FETCH_HEAD)
        if not success:
            raise ValueError("Cherry-pick failed. Exiting")

        LOG.info("REMEMBER to change the commit message with command: 'git commit --amend'")
        LOG.info("REMEMBER to reset the author with command: 'git commit --amend --reset-author")