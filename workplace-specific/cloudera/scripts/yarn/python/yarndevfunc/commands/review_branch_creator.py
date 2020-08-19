import logging

from yarndevfunc.constants import YARN_PATCH_FILENAME_REGEX, TRUNK, ORIGIN, ORIGIN_TRUNK
from yarndevfunc.utils import StringUtils, FileUtils, PatchUtils

BRANCH_PREFIX = "review-"

LOG = logging.getLogger(__name__)


class ReviewBranchCreator:
    def __init__(self, args, upstream_repo):
        self.args = args
        self.upstream_repo = upstream_repo

    def run(self):
        patch_file = self.args.patch_file

        FileUtils.ensure_file_exists(patch_file, create=False)
        patch_file_name = FileUtils.path_basename(patch_file)
        matches = StringUtils.ensure_matches_pattern(patch_file_name, YARN_PATCH_FILENAME_REGEX)
        if not matches:
            raise ValueError(
                "Filename '{}' (full path: {}) does not match usual patch file pattern: '{}'!".format(
                    patch_file_name, patch_file, YARN_PATCH_FILENAME_REGEX
                )
            )

        orig_branch = self.upstream_repo.get_current_branch_name()
        LOG.info("Current branch: %s", orig_branch)

        target_branch = BRANCH_PREFIX + StringUtils.get_matched_group(patch_file, YARN_PATCH_FILENAME_REGEX, 1)
        LOG.info("Target branch: %s", target_branch)

        clean = self.upstream_repo.is_working_directory_clean()
        if not clean:
            raise ValueError("git working directory is not clean, please stash or drop your changes")

        self.upstream_repo.checkout_branch(TRUNK)
        self.upstream_repo.pull(ORIGIN)
        diff = self.upstream_repo.diff_between_refs(ORIGIN_TRUNK, TRUNK)
        if diff:
            raise ValueError(
                "There is a diff between local {} and {}! Run 'git reset {} --hard' and re-run the script!".format(
                    TRUNK, ORIGIN_TRUNK, ORIGIN_TRUNK
                )
            )

        apply_result = self.upstream_repo.apply_check(patch_file, raise_exception=False)
        if not apply_result:
            self.upstream_repo.checkout_previous_branch()
            cmd = "git apply " + patch_file
            raise ValueError(
                "Patch does not apply to {}, please resolve the conflicts manually. "
                "Run this command to apply the patch again: {}".format(TRUNK, cmd)
            )

        LOG.info("Patch %s applies cleanly to %s", patch_file, TRUNK)
        branch_exists = self.upstream_repo.is_branch_exist(target_branch)
        base_ref = TRUNK
        if not branch_exists:
            success = self.upstream_repo.checkout_new_branch(target_branch, base_ref)
            if not success:
                raise ValueError("Cannot checkout new branch {} based on ref {}".format(target_branch, base_ref))
            LOG.info("Checked out branch %s based on ref %s", target_branch, base_ref)
        else:
            branch_pattern = target_branch + "*"
            branches = self.upstream_repo.list_branches(branch_pattern)
            LOG.info("Found existing review branches for this patch: %s", branches)
            target_branch = PatchUtils.get_next_review_branch_name(branches)
            LOG.info("Creating new version of review branch as: %s", target_branch)
            success = self.upstream_repo.checkout_new_branch(target_branch, base_ref)
            if not success:
                raise ValueError("Cannot checkout new branch {} based on ref {}".format(target_branch, base_ref))

        self.upstream_repo.apply_patch(patch_file, include_check=False)
        LOG.info("Successfully applied patch: %s", patch_file)
        commit_msg = "patch file: {}".format(patch_file)
        self.upstream_repo.add_all_and_commit(commit_msg)
        LOG.info("Committed changes of patch: %s with message: %s", patch_file, commit_msg)
