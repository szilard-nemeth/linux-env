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

    def checkout_new_branch(self, new_branch, base_ref):
        base_exist = self.is_branch_exist(base_ref)
        if not base_exist:
            return False

        prev_branch = self.get_current_branch_name()
        LOG.info("Checking out new branch: %s based on ref: %s (Previous branch was: %s)", new_branch, base_ref,
                 prev_branch)
        self.repo.git.checkout(base_ref, b=new_branch)
        return True

    def pull(self, remote_name):
        progress = ProgressPrinter("pull")
        remote = self.repo.remote(name=remote_name)
        LOG.info("Pulling remote: %s", remote_name)
        remote.pull(progress=progress)

    def fetch(self, repo_url=None, remote_name=None, all=False):
        progress = ProgressPrinter("fetch")
        if not repo_url and not remote_name and not all:
            raise ValueError("Please specify remote or use the 'all' switch")

        if repo_url:
            try:
                LOG.info("Fetching from provided repo URL: %s", repo_url)
                self.repo.git.fetch(repo_url, remote_name)
                return True
            except GitCommandError as e:
                LOG.exception("Git fetch failed.", exc_info=True)
                return False

        if all:
            LOG.info("Fetching all remotes...")
            for remote in self.repo.remotes:
                remote.fetch()
        else:
            LOG.info("Fetching remote: %s", remote_name)
            remote = self.repo.remote(name=remote_name)
            remote.fetch(progress=progress)

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

    def diff_check(self, raise_exception=True):
        try:
            self.repo.git.diff(check=True)
            return True
        except GitCommandError as e:
            LOG.error("Git diff --check failed. There are trailing whitespaces in the diff, please fix them!")
            if raise_exception:
                raise e
            return False

    def apply_check(self, patch, raise_exception=False):
        try:
            self.repo.git.apply(patch, check=True)
            return True
        except GitCommandError as e:
            LOG.exception("Git apply --check failed", exc_info=True)
            if raise_exception:
                raise e
            return False

    def apply_patch(self, patch, include_check=True, raise_exception=False):
        try:
            if include_check:
                self.apply_check(patch, raise_exception=False)
            LOG.info("Applying patch: %s", patch)
            self.repo.git.apply(patch)
            return True
        except GitCommandError as e:
            LOG.error("Git apply failed for patch %s!", patch)
            if raise_exception:
                raise e
            return False

    def diff(self, branch):
        LOG.info("Making diff against %s", branch)
        return self.repo.git.diff(branch)

    def diff_between_refs(self, ref1, ref2):
        LOG.info("Making diff: %s..%s", ref1, ref2)
        return self.repo.git.diff("{}..{}".format(ref1, ref2))

    def is_working_directory_clean(self):
        status = self.repo.git.status(porcelain=True)
        LOG.debug("Git status: %s", status)
        return False if len(status) > 0 else True

    def is_branch_exist(self, branch):
        try:
            self.repo.git.rev_parse('--verify', branch)
            return True
        except GitCommandError as e:
            LOG.exception("Branch does not exist", exc_info=True)
            return False

    def list_branches(self, name):
        try:
            branches = self.repo.git.branch('--list', name)
            branches = branches.split('\n')
            return [b.replace(" ", "") for b in branches]
        except GitCommandError as e:
            LOG.exception("Branch does not exist with name: {}".format(name), exc_info=True)
            return []

    def add_all_and_commit(self, commit_msg, raise_exception=False):
        try:
            self.repo.git.add('-A')
            self.repo.index.commit(commit_msg)
            return True
        except GitCommandError as e:
            LOG.exception("Failed to commit changes from index", exc_info=True)
            return False

    def commit(self, amend=False, message=None):
        kwargs = {}

        if amend:
            kwargs['amend'] = amend
        if message:
            kwargs['m'] = message
        LOG.info("Running git commit with arguments: %s", kwargs)
        self.repo.git.commit(**kwargs)

    def log(self, revision_range, oneline=False, grep=None, format=None, n=None):
        args = []
        if revision_range:
            args.append(revision_range)

        kwargs = {}
        if oneline:
            kwargs['oneline'] = True
        if grep:
            kwargs['grep'] = grep
        if format:
            kwargs['format'] = format
        if n:
            kwargs['n'] = n
            kwargs['oneline'] = True

        # TODO these logs can be replaced with: https://gitpython.readthedocs.io/en/stable/tutorial.html#git-command-debugging-and-customization
        LOG.info("Running git log with arguments, args: %s, kwargs: %s", args, kwargs)
        return self.repo.git.log(*args, **kwargs).splitlines()

    def cherry_pick(self, ref, x=False):
        kwargs = {}
        if x:
            kwargs['x'] = x
        try:
            self.repo.git.cherry_pick(**kwargs)
            return True
        except GitCommandError as e:
            LOG.exception("Failed to cherry-pick commit: " + ref, exc_info=True)
            return False

    def format_patch(self, revision_range, output_dir=None, full_index=None):
        # git format-patch ${GIT_BASE_BRANCH} --output-directory ${GIT_FORMAT_PATCH_OUTPUT_DIR} --full-index
        args = []
        if revision_range:
            args.append(revision_range)

        kwargs = {}
        if output_dir:
            kwargs['output_directory'] = output_dir
        if full_index:
            kwargs['full_index'] = True

        # TODO these logs can be replaced with: https://gitpython.readthedocs.io/en/stable/tutorial.html#git-command-debugging-and-customization
        LOG.info("Running git format-patch with arguments, args: %s, kwargs: %s", args, kwargs)
        return self.repo.git.format_patch(*args, **kwargs)


class ProgressPrinter(RemoteProgress):
    def __init__(self, operation):
        super(ProgressPrinter, self).__init__()
        self.operation = operation

    def update(self, op_code, cur_count, max_count=None, message=''):
        percentage = cur_count / (max_count or 100.0) * 100
        LOG.debug("Progress of git %s: %s%% (speed: %s)", self.operation, percentage, message or "-")
