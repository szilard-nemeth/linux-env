import logging

from yarndevfunc.constants import ORIGIN, HEAD
from yarndevfunc.git_wrapper import GitWrapper

LOG = logging.getLogger(__name__)


class Backporter:
    """
    A class used to backport changes from an upstream repository to a downstream repository, having an assumption
    that the specified upstream commit is committed on the base branch.

    Attributes
    ----------
    args : str
        Command line arguments passed to this command.
    downtream jira id : str
        Jira ID of the downstream jira.
        Specified with args.
    downstream_branch : str
        Downstream branch to create in the downstream repo for this backport.
        Specified with args.
    upstream_jira_id : str
        Jira ID of the upstream jira to backport.
        Specified with args.

    upstream_repo : GitWrapper
        A GitWrapper, representing the upstream repository.
    downstream_repo : GitWrapper
        A GitWrapper, representing the downstream repository.
    cherry_pick_base_ref : str
        A branch that is the base of the newly created downstream branch for this backport.
    default_branch : str
        The upstream branch to check out, assuming that the specified commit will be already committed on this branch.
    commit_hash : str
        Hash of the commit to backport from the upstream repository.
    post_commit_messages : list[str]
        List of messages to print as post-commit guidance.

    Methods
    -------
    run()
        Executes this command.
        The steps are roughly are:
        1. Sync upstream repository: Fetch and checkout base branch.
        2. Gather the hash of the upstream commit and set it to self.commit_hash.
        3. Fetch all remotes of the downstream repository.
        4. Chrerry-pick the upstream commit to the downstream repository.
        5. Rewrite the commit message, add the downstream jira ID as a prefix.
        6. Print post-commit guidance.
    """

    def __init__(
        self, args, upstream_repo, downstream_repo, cherry_pick_base_ref, default_branch, post_commit_messages=None
    ):
        self.args = args
        # Parsed from args
        self.downstream_jira_id = self.args.cdh_jira_id
        self.downstream_branch = self.args.cdh_branch
        self.upstream_jira_id = self.args.upstream_jira_id

        self.upstream_repo = upstream_repo
        self.downstream_repo = downstream_repo
        self.cherry_pick_base_ref = cherry_pick_base_ref
        self.default_branch = default_branch
        self.post_commit_messages = post_commit_messages

        # Dynamic attributes
        self.commit_hash = None

    def run(self):
        self.sync_upstream_repo()
        self.get_upstream_commit_hash()

        # DO THE REST OF THE WORK IN THE DOWNSTREAM REPO
        self.downstream_repo.fetch(all=True)
        self.cherry_pick_commit()
        self.rewrite_commit_message()
        self.print_post_commit_guidance()

    def get_upstream_commit_hash(self):
        git_log_result = self.upstream_repo.log(HEAD, oneline=True, grep=self.upstream_jira_id)
        # Restore original branch in either error-case or normal case
        self.upstream_repo.checkout_previous_branch()
        if not git_log_result:
            raise ValueError("Upstream commit not found with string in commit message: %s", self.upstream_jira_id)
        if len(git_log_result) > 1:
            raise ValueError(
                "Ambiguous upsream commit with string in commit message: %s. Results: %s",
                self.upstream_jira_id,
                git_log_result,
            )
        self.commit_hash = GitWrapper.extract_commit_hash_from_gitlog_result(git_log_result[0])

    def sync_upstream_repo(self):
        # TODO decide on the downstream branch whether this is C5 or C6 backport (remote is different)
        curr_branch = self.upstream_repo.get_current_branch_name()
        LOG.info("Current branch: %s", curr_branch)
        self.upstream_repo.fetch(all=True)
        self.upstream_repo.checkout_branch(self.default_branch)
        self.upstream_repo.pull(ORIGIN)

    def cherry_pick_commit(self):
        # TODO handle if branch already exist (is it okay to silently ignore?) or should use current branch with switch?
        # Example checkout command: git checkout -b "$CDH_JIRA_NO-$CDH_BRANCH" cauldron/${CDH_BRANCH}
        new_branch_name = "{}-{}".format(self.downstream_jira_id, self.downstream_branch)
        success = self.downstream_repo.checkout_new_branch(new_branch_name, self.cherry_pick_base_ref)
        if not success:
            raise ValueError(
                "Cannot checkout new branch {} based on ref {}".format(new_branch_name, self.cherry_pick_base_ref)
            )

        exists = self.downstream_repo.is_branch_exist(self.commit_hash)
        if not exists:
            raise ValueError(
                "Cannot find commit with hash {}. "
                "Please verify if downstream repo has a remote to the upstream repo!",
                self.commit_hash,
            )
        cherry_pick_result = self.downstream_repo.cherry_pick(self.commit_hash, x=True)

        if not cherry_pick_result:
            raise ValueError(
                "Failed to cherry-pick commit: {}. "
                "Perhaps there were some merge conflicts, "
                "please resolve them and run: git cherry-pick --continue".format(self.commit_hash)
            )

    def rewrite_commit_message(self):
        """
        Add downstream jira number as a prefix.
        Since it triggers a commit, it will also add gerrit Change-Id to the commit.
        :return:
        """
        self.downstream_repo.rewrite_head_commit_message(prefix="{}: ".format(self.downstream_jira_id))

    def print_post_commit_guidance(self):
        LOG.info("Commit was successful!")
        if self.post_commit_messages:
            for message in self.post_commit_messages:
                LOG.info("{}\n".format(message))
