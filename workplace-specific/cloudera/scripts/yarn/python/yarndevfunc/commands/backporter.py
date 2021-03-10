import logging

from yarndevfunc.constants import ORIGIN, HEAD
from yarndevfunc.git_wrapper import GitWrapper

LOG = logging.getLogger(__name__)


class Backporter:
    """
    A class used to backport changes from an upstream repository to a downstream repository, having an assumption
    that the specified upstream commit is committed on the specified upstream branch.

    Attributes
    ----------
    args : object
        Command line arguments passed to this command.
    downtream_jira_id : str
        Jira ID of the downstream jira.
        Specified with args.
    downstream_branch : str
        Downstream branch to create in the downstream repo for this backport.
        Specified with args.
    upstream_jira_id : str
        Jira ID of the upstream jira to backport.
        Specified with args.

    upstream_repo : GitWrapper
        A GitWrapper object, representing the upstream repository.
    downstream_repo : GitWrapper
        A GitWrapper object, representing the downstream repository.
    cherry_pick_base_ref : str
        A branch that is the base of the newly created downstream branch for this backport.
    upstream_branch : str
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
        4. Cherry-pick the upstream commit to the downstream repository.
        5. Rewrite the commit message, add the downstream jira ID as a prefix.
        6. Print post-commit guidance.
    """

    def __init__(self, args, upstream_repo, downstream_repo, cherry_pick_base_ref, post_commit_messages=None):
        self.args = args
        # Parsed from args
        self.downstream_jira_id = self.args.cdh_jira_id
        self.downstream_branch = self.args.cdh_branch
        self.upstream_jira_id = self.args.upstream_jira_id
        self.upstream_branch = self.args.upstream_branch

        self.upstream_repo = upstream_repo
        self.downstream_repo = downstream_repo
        self.cherry_pick_base_ref = cherry_pick_base_ref
        self.post_commit_messages = post_commit_messages

        # Dynamic attributes
        self.commit_hash = None

    def run(self):
        LOG.info(
            "Starting backport. \n "
            "Upstream Jira ID: %s\n "
            "Upstream branch: %s\n "
            "Downstream Jira ID: %s\n "
            "Downstream ref (base): %s\n "
            "Downstream branch (target): %s\n",
            self.upstream_jira_id,
            self.upstream_branch,
            self.downstream_jira_id,
            self.cherry_pick_base_ref,
            self.downstream_branch,
        )
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
            raise ValueError(
                f"Upstream commit not found on branch {self.upstream_branch} "
                f"with string in commit message: {self.upstream_jira_id}"
            )
        if len(git_log_result) > 1:
            raise ValueError(
                f"Ambiguous upstream commit with string in commit message: {self.upstream_jira_id}. "
                f"Results: {git_log_result}"
            )
        self.commit_hash = GitWrapper.extract_commit_hash_from_gitlog_result(git_log_result[0])

    def sync_upstream_repo(self):
        # TODO decide on the downstream branch whether this is C5 or C6 backport (remote is different)
        curr_branch = self.upstream_repo.get_current_branch_name()
        LOG.info("Current branch: %s", curr_branch)
        self.upstream_repo.fetch(all=True)
        self.upstream_repo.checkout_branch(self.upstream_branch, track=True)

        clean_workingdir = self.upstream_repo.is_working_directory_clean()
        if not clean_workingdir:
            LOG.warning("Working directory is not clean for repository: %s", self.upstream_repo.repo_path)
        self.upstream_repo.pull(ORIGIN)

    def cherry_pick_commit(self):
        # Example checkout command: git checkout -b "$CDH_JIRA_NO-$CDH_BRANCH" cauldron/${CDH_BRANCH}
        new_branch_name = f"{self.downstream_jira_id}-{self.downstream_branch}"

        if self.downstream_repo.is_branch_exist(new_branch_name, exc_info=False):
            LOG.warning("Branch already exists: %s. Continuing execution", new_branch_name)
            # Make sure branch is checked out
            self.downstream_repo.checkout_branch(new_branch_name)
        else:
            success = self.downstream_repo.checkout_new_branch(new_branch_name, self.cherry_pick_base_ref)
            if not success:
                raise ValueError(
                    f"Cannot checkout new branch {new_branch_name} based on ref {self.cherry_pick_base_ref}"
                )

        git_log_result = self.downstream_repo.log(HEAD, oneline=True, grep=self.upstream_jira_id)
        if git_log_result:
            LOG.warning("Commit already cherry-picked to branch. Continuing execution")
        else:
            if not self.downstream_repo.is_branch_exist(self.commit_hash):
                raise ValueError(
                    "Cannot find commit with hash {}. "
                    "Please verify if downstream repo has a remote to the upstream repo!",
                    self.commit_hash,
                )
            cherry_pick_result = self.downstream_repo.cherry_pick(self.commit_hash, x=True)

            if not cherry_pick_result:
                raise ValueError(
                    f"Failed to cherry-pick commit: {self.commit_hash}. "
                    "Perhaps there were some merge conflicts, "
                    "please resolve them and run: git cherry-pick --continue"
                )

    def rewrite_commit_message(self):
        """
        Add downstream jira number as a prefix.
        Since it triggers a commit, it will also add gerrit Change-Id to the commit.
        :return:
        """
        head_commit_msg = self.downstream_repo.get_head_commit_message()
        upstream_jira_id_in_commit_msg = self.upstream_jira_id in head_commit_msg
        commit_msg_starts_with_downstream_jira_id = head_commit_msg.startswith(self.downstream_jira_id)

        if not upstream_jira_id_in_commit_msg:
            raise ValueError(
                "Upstream jira id should be in commit message. "
                f"Current commit mesage: {head_commit_msg}, upstream jira id: {self.upstream_jira_id}"
            )

        if commit_msg_starts_with_downstream_jira_id:
            LOG.info(
                "Commit message already includes downstream jira id in the beginning. Current commit message: %s",
                head_commit_msg,
            )
        else:
            LOG.info("Rewriting commit message. Current commit message: %s", head_commit_msg)
            self.downstream_repo.rewrite_head_commit_message(prefix=f"{self.downstream_jira_id}: ")

    def print_post_commit_guidance(self):
        LOG.info("Backport was successful!")
        if self.post_commit_messages:
            for message in self.post_commit_messages:
                LOG.info(f"{message}\n")
