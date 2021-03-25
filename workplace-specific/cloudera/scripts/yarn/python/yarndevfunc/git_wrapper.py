import logging
import os
from typing import List

from git import Repo, RemoteProgress, GitCommandError, Commit
from yarndevfunc.constants import ORIGIN

from yarndevfunc.constants import HEAD, COMMIT_FIELD_SEPARATOR

FORMAT_CODE_HASH = "%H"
FORMAT_CODE_COMMIT_MSG = "%s"
FORMAT_CODE_DATE_ISO_8601 = "%cI"
FORMAT_CODE_AUTHOR = "%ae"

LOG = logging.getLogger(__name__)


# TODO These all could be moved to python-commons
class GitWrapper:
    def __init__(self, base_path):
        self.repo_path = base_path
        self.repo = Repo(self.repo_path)

    @property
    def is_enabled_git_cmd_logging(self):
        return self.repo.git.GIT_PYTHON_TRACE is not False

    def enable_debug_logging(self, full=False):
        value = "full" if full else "1"
        os.environ["GIT_PYTHON_TRACE"] = value
        # https://github.com/gitpython-developers/GitPython/issues/222#issuecomment-68597780
        type(self.repo.git).GIT_PYTHON_TRACE = value

    def get_current_branch_name(self):
        return self.repo.git.rev_parse("HEAD", symbolic_full_name=True, abbrev_ref=True)

    def checkout_branch(self, branch, track=False):
        prev_branch = self.get_current_branch_name()
        LOG.info("Checking out branch: %s (Previous branch was: %s)", branch, prev_branch)
        self.repo.git.checkout(branch)
        if track:
            LOG.info("Tracking branch '%s' with remote '%s'", branch, ORIGIN)
            self.repo.git.branch("-u", ORIGIN + "/" + branch)
        # self.repo.heads.past_branch.checkout()

    def checkout_new_branch(self, new_branch, base_ref):
        base_exist = self.is_branch_exist(base_ref)
        if not base_exist:
            return False

        prev_branch = self.get_current_branch_name()
        LOG.info(
            "Checking out new branch: %s based on ref: %s (Previous branch was: %s)", new_branch, base_ref, prev_branch
        )
        try:
            self.repo.git.checkout(base_ref, b=new_branch)
        except GitCommandError:
            LOG.exception("Git checkout failed!", exc_info=True)
            return False
        return True

    def pull(self, remote_name):
        progress = ProgressPrinter("pull")
        remote = self.repo.remote(name=remote_name)
        LOG.info("Pulling remote: %s", remote_name)
        result = remote.pull(progress=progress)
        LOG.debug("Result of git pull: %s", result)

    def fetch(self, repo_url=None, remote_name=None, all=False):
        progress = ProgressPrinter("fetch")
        if not repo_url and not remote_name and not all:
            raise ValueError("Please specify remote or use the 'all' switch")

        if repo_url:
            try:
                LOG.info("Fetching from provided repo URL: %s", repo_url)
                self.repo.git.fetch(repo_url, remote_name)
                return True
            except GitCommandError:
                LOG.exception("Git fetch failed.", exc_info=True)
                return False

        if all:
            LOG.info("Fetching all remotes of git repo '%s'...", self.repo_path)
            for remote in self.repo.remotes:
                LOG.info("Fetching remote '%s' of repository: %s", remote, self.repo.git_dir)
                remote.fetch()
        else:
            LOG.info("Fetching remote '%s' of repository: %s", remote_name, self.repo.git_dir)
            remote = self.repo.remote(name=remote_name)
            remote.fetch(progress=progress)

    def checkout_previous_branch(self):
        prev_branch = self.get_current_branch_name()
        self.repo.git.checkout("-")
        LOG.info("Checked out: %s (Previous branch was: %s)", self.get_current_branch_name(), prev_branch)

    def rebase(self, rebase_onto):
        LOG.info("Rebasing onto branch: %s", rebase_onto)

        try:
            self.repo.git.rebase(rebase_onto)
        except GitCommandError:
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

    def diff(self, branch, cached=False):
        kwargs = {}
        if cached:
            kwargs["cached"] = True

        LOG.info("Making diff against %s", branch)
        return self.repo.git.diff(branch, **kwargs)

    def diff_between_refs(self, ref1, ref2):
        LOG.info("Making diff: %s..%s", ref1, ref2)
        return self.repo.git.diff(f"{ref1}..{ref2}")

    def diff_tree(self, ref, no_commit_id=None, name_only=None, recursive=False):
        args = [ref]

        kwargs = {}
        if no_commit_id:
            kwargs["no_commit_id"] = True
        if name_only:
            kwargs["name_only"] = True
        if recursive:
            kwargs["r"] = True

        if not self.is_enabled_git_cmd_logging:
            LOG.info("Running git diff-tree with arguments, args: %s, kwargs: %s", args, kwargs)
        diff_tree_results = self.repo.git.diff_tree(*args, **kwargs).splitlines()
        return diff_tree_results

    def show(self, hash, no_patch=None, no_notes=None, pretty=None, suppress_diff=False, format=None):
        args = [hash]

        kwargs = {}
        if no_patch:
            kwargs["no_patch"] = True
        if no_notes:
            kwargs["no_notes"] = True
        if pretty:
            kwargs["pretty"] = pretty
        if suppress_diff:
            kwargs["s"] = True
        if format:
            kwargs["format"] = format

        if not self.is_enabled_git_cmd_logging:
            LOG.info("Running git show with arguments, args: %s, kwargs: %s", args, kwargs)
        result = self.repo.git.show(*args, **kwargs).splitlines()
        return result

    def get_author_by_hash(self, hash):
        return self.show(hash, suppress_diff=True, format="%ae")

    def is_working_directory_clean(self):
        status = self.repo.git.status(porcelain=True)
        LOG.debug("Git status: %s", status)
        return False if len(status) > 0 else True

    def is_branch_exist(self, branch: str, exc_info=True):
        try:
            self.repo.git.rev_parse("--verify", branch)
            return True
        except GitCommandError:
            LOG.exception("Branch does not exist", exc_info=exc_info)
            return False

    def list_branches(self, name):
        try:
            branches = self.repo.git.branch("--list", name)
            branches = branches.split("\n")
            return [b.replace(" ", "") for b in branches]
        except GitCommandError:
            LOG.exception(f"Branch does not exist with name: {name}", exc_info=True)
            return []

    def add_all_and_commit(self, commit_msg, raise_exception=False):
        try:
            self.repo.git.add("-A")
            self.repo.index.commit(commit_msg)
            return True
        except GitCommandError:
            LOG.exception("Failed to commit changes from index", exc_info=True)
            return False

    def commit(self, amend=False, message=None):
        kwargs = {}

        if amend:
            kwargs["amend"] = amend
        if message:
            kwargs["m"] = message
        LOG.info("Running git commit with arguments: %s", kwargs)
        self.repo.git.commit(**kwargs)

    def log(
        self,
        revision_range,
        oneline=False,
        oneline_with_date=False,
        oneline_with_date_and_author=False,
        grep=None,
        format=None,
        n=None,
        return_hashes=False,
        return_messages=False,
        as_string_message=False,
        follow=False,
        all=False,
    ):
        if oneline and oneline_with_date:
            raise ValueError("oneline and oneline_with_date should be exclusive!")

        if as_string_message and n != 1:
            raise ValueError("as_string_message only works with option n=1")

        args = []
        if revision_range:
            args.append(revision_range)

        kwargs = {}
        if oneline:
            kwargs["oneline"] = True

        # https://git-scm.com/docs/pretty-formats
        # Oneline format: <hash> <title line>
        # Oneline + date format: <hash> <title line> <author date>
        if oneline_with_date:
            kwargs["format"] = f"{FORMAT_CODE_HASH} {FORMAT_CODE_COMMIT_MSG} {FORMAT_CODE_DATE_ISO_8601}"
        if oneline_with_date_and_author:
            kwargs[
                "format"
            ] = f"{FORMAT_CODE_HASH} {FORMAT_CODE_COMMIT_MSG} {FORMAT_CODE_DATE_ISO_8601} {FORMAT_CODE_AUTHOR}"
        if format:
            kwargs["format"] = format
        if grep:
            kwargs["grep"] = grep
        if n:
            kwargs["n"] = n
        if follow:
            kwargs["follow"] = True
        if all:
            kwargs["all"] = True

        if not self.is_enabled_git_cmd_logging:
            LOG.info("Running git log with arguments, args: %s, kwargs: %s", args, kwargs)
        log_result = self.repo.git.log(*args, **kwargs).splitlines()

        if return_hashes:
            return [result.split(COMMIT_FIELD_SEPARATOR)[0] for result in log_result]
        if return_messages:
            # Remove commit hash and rejoin parts of commit message into one string
            # TODO Below command only works for --oneline option
            return [COMMIT_FIELD_SEPARATOR.join(result.split(COMMIT_FIELD_SEPARATOR)[1:]) for result in log_result]

        if as_string_message:
            return "\n".join(log_result)
        return log_result

    def branch(self, refspec, recursive=False, contains=None):
        args = []
        if refspec:
            args.append(refspec)

        kwargs = {}
        if recursive:
            kwargs["r"] = True
        if contains:
            kwargs["contains"] = contains

        lines = self.repo.git.branch(refspec, *args, **kwargs).splitlines()
        for idx, line in enumerate(lines):
            # Replace all whitespace with empty string
            lines[idx] = "".join(line.split())
        return lines

    def cherry_pick(self, ref, x=False):
        kwargs = {}
        if x:
            kwargs["x"] = x
        try:
            self.repo.git.cherry_pick(ref, **kwargs)
            return True
        except GitCommandError:
            LOG.exception("Failed to cherry-pick commit: " + ref, exc_info=True)
            return False

    def format_patch(self, revision_range, output_dir=None, full_index=None):
        # git format-patch ${GIT_BASE_BRANCH} --output-directory ${GIT_FORMAT_PATCH_OUTPUT_DIR} --full-index
        args = []
        if revision_range:
            args.append(revision_range)

        kwargs = {}
        if output_dir:
            kwargs["output_directory"] = output_dir
        if full_index:
            kwargs["full_index"] = True

        if not self.is_enabled_git_cmd_logging:
            LOG.info("Running git format-patch with arguments, args: %s, kwargs: %s", args, kwargs)
        return self.repo.git.format_patch(*args, **kwargs)

    def rewrite_head_commit_message(self, prefix=None, postfix=None):
        if not prefix and not postfix:
            raise ValueError("You must provide either prefix or postfix!")
        old_commit_msg = self.get_head_commit_message()
        # Add downstream (CDH jira) number as a prefix.
        # Since it triggers a commit, it will also add gerrit Change-Id to the commit.
        self.repo.git.commit(amend=True, message=f"{prefix}{old_commit_msg}")

    def merge_base(self, feature_br: str, master_br: str) -> List[Commit]:
        return self.repo.merge_base(feature_br, master_br)

    def get_head_commit_message(self):
        return self.log(HEAD, format="%B", n=1, as_string_message=True)

    @staticmethod
    def extract_commit_hash_from_gitlog_results(results):
        return [res.split(COMMIT_FIELD_SEPARATOR)[0] for res in results]

    @staticmethod
    def extract_commit_hash_from_gitlog_result(result):
        return result.split(COMMIT_FIELD_SEPARATOR)[0]


class ProgressPrinter(RemoteProgress):
    def __init__(self, operation):
        super(ProgressPrinter, self).__init__()
        self.operation = operation

    def update(self, op_code, cur_count, max_count=None, message=""):
        percentage = cur_count / (max_count or 100.0) * 100
        LOG.info("Progress of git %s: %s%% (speed: %s)", self.operation, percentage, message or "-")
