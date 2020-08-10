import logging
from git import Repo, RemoteProgress, GitCommandError

LOG = logging.getLogger(__name__)


class GitWrapper:
  def __init__(self, base_path):
    self.repo_path = base_path
    self.repo = Repo(self.repo_path)

  def get_current_branch_name(self):
    return self.repo.git.rev_parse('HEAD', symbolic_full_name=True, abbrev_ref=True)

  def checkout_branch(self, branch):
    prev_branch = self.get_current_branch_name()
    LOG.info("Checking out branch: %s (Previous branch was: %s)", branch, prev_branch)
    self.repo.git.checkout(branch)
    # self.repo.heads.past_branch.checkout()

  def pull(self, remote_name):
    progress = ProgressPrinter("pull")
    remote = self.repo.remote(name=remote_name)
    LOG.info("Pulling remote: %s", remote_name)
    remote.pull(progress=progress)

  def checkout_previous_branch(self):
    prev_branch = self.get_current_branch_name()
    self.repo.git.checkout('-')
    LOG.info("Checked out: %s (Previous branch was: %s)", self.get_current_branch_name(), prev_branch)

  def rebase(self, rebase_onto):
    LOG.info("Rebasing onto branch: %s", rebase_onto)

    try:
      self.repo.git.rebase(rebase_onto)
    except GitCommandError as e1:
      LOG.exception("Rebase failed!", exc_info=True)
      try:
        self.abort_rebase()
        LOG.error("Rebase was aborted! Please rebase manually!")
      except GitCommandError as e2:
        LOG.debug("Rebase was not in progress, but probably this is normal. Exception data: %s", e2)
      return False

    return True

  def abort_rebase(self):
    LOG.info("Aborting rebase...")
    self.repo.git.rebase(abort=True)

  def diff_check(self):
    try:
      self.repo.git.diff(check=True)
    except GitCommandError as e:
      LOG.error("Git diff --check failed. There are trailing whitespaces in the diff, please fix them!")
      raise e

  def apply_check(self, patch):
    try:
      self.repo.git.apply(patch, check=True)
      return True
    except GitCommandError as e:
      LOG.exception("Git apply --check failed", exc_info=True)
      return False

  def diff(self, branch):
    LOG.info("Making diff against %s", branch)
    return self.repo.git.diff(branch)


class ProgressPrinter(RemoteProgress):
  def __init__(self, operation):
    super(ProgressPrinter, self).__init__()
    self.operation = operation

  def update(self, op_code, cur_count, max_count=None, message=''):
    percentage = cur_count / (max_count or 100.0) * 100
    LOG.debug("Progress of git %s: %s%% (speed: %s)", self.operation, percentage, message or "-")