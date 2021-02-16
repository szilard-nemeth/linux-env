import logging

from pythoncommons.file_utils import FileUtils
from pythoncommons.patch_utils import PatchUtils
from pythoncommons.string_utils import RegexUtils

from yarndevfunc.constants import YARN_PATCH_FILENAME_REGEX, ORIGIN

BRANCH_PREFIX = "review-"

LOG = logging.getLogger(__name__)


class ReviewBranchCreator:
    def __init__(self, args, upstream_repo, base_branch, remote_base_branch):
        self.args = args
        self.upstream_repo = upstream_repo
        self.base_branch = base_branch
        self.remote_base_branch = remote_base_branch

    def run(self):
        patch_file = self.args.patch_file

        FileUtils.ensure_file_exists(patch_file, create=False)
        patch_file_name = FileUtils.path_basename(patch_file)
        matches = RegexUtils.ensure_matches_pattern(patch_file_name, YARN_PATCH_FILENAME_REGEX)
        if not matches:
            raise ValueError(
                f"Filename '{patch_file_name}' (full path: {patch_file}) "
                f"does not match usual patch file pattern: '{YARN_PATCH_FILENAME_REGEX}'!"
            )

        orig_branch = self.upstream_repo.get_current_branch_name()
        LOG.info("Current branch: %s", orig_branch)

        target_branch = BRANCH_PREFIX + RegexUtils.get_matched_group(patch_file, YARN_PATCH_FILENAME_REGEX, 1)
        LOG.info("Target branch: %s", target_branch)

        clean = self.upstream_repo.is_working_directory_clean()
        if not clean:
            raise ValueError("git working directory is not clean, please stash or drop your changes")

        self.upstream_repo.checkout_branch(self.base_branch)
        self.upstream_repo.pull(ORIGIN)
        diff = self.upstream_repo.diff_between_refs(self.remote_base_branch, self.base_branch)
        if diff:
            raise ValueError(
                f"There is a diff between local {self.base_branch} and {self.remote_base_branch}! "
                f"Run 'git reset {self.remote_base_branch} --hard' and re-run the script!"
            )

        apply_result = self.upstream_repo.apply_check(patch_file, raise_exception=False)
        if not apply_result:
            self.upstream_repo.checkout_previous_branch()
            cmd = "git apply " + patch_file
            raise ValueError(
                f"Patch does not apply to {self.base_branch}, please resolve the conflicts manually. "
                f"Run this command to apply the patch again: {cmd}"
            )

        LOG.info("Patch %s applies cleanly to %s", patch_file, self.base_branch)
        branch_exists = self.upstream_repo.is_branch_exist(target_branch)
        base_ref = self.base_branch
        if not branch_exists:
            success = self.upstream_repo.checkout_new_branch(target_branch, base_ref)
            if not success:
                raise ValueError(f"Cannot checkout new branch {target_branch} based on ref {base_ref}")
            LOG.info("Checked out branch %s based on ref %s", target_branch, base_ref)
        else:
            branch_pattern = target_branch + "*"
            branches = self.upstream_repo.list_branches(branch_pattern)
            LOG.info("Found existing review branches for this patch: %s", branches)
            target_branch = PatchUtils.get_next_review_branch_name(branches)
            LOG.info("Creating new version of review branch as: %s", target_branch)
            success = self.upstream_repo.checkout_new_branch(target_branch, base_ref)
            if not success:
                raise ValueError(f"Cannot checkout new branch {target_branch} based on ref {base_ref}")

        self.upstream_repo.apply_patch(patch_file, include_check=False)
        LOG.info("Successfully applied patch: %s", patch_file)
        commit_msg = f"patch file: {patch_file}"
        self.upstream_repo.add_all_and_commit(commit_msg)
        LOG.info("Committed changes of patch: %s with message: %s", patch_file, commit_msg)
