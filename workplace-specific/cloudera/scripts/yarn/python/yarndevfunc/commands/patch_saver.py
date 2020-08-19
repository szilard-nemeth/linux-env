import logging

from yarndevfunc.constants import TRUNK, ORIGIN
from yarndevfunc.utils import FileUtils, PatchUtils

LOG = logging.getLogger(__name__)


class PatchSaver:
    def __init__(self, args, repo, patch_dir):
        self.args = args
        self.repo = repo
        self.patch_dir = patch_dir

    def run(self):
        # TODO add force mode: ignore whitespace issues and make backup of patch!
        # TODO add another mode: Create patch based on changes in staged area, not commits
        curr_branch = self.repo.get_current_branch_name()
        LOG.info("Current branch: %s", curr_branch)

        if curr_branch == TRUNK:
            raise ValueError("Cannot make patch, current branch is {}. Please use a different branch!".format(TRUNK))
        patch_branch = curr_branch

        # TODO if there's no commit between trunk..branch, don't move forward and exit
        # TODO check if git is clean (no modified, unstaged files, etc)
        self.repo.checkout_branch(TRUNK)
        self.repo.pull(ORIGIN)
        self.repo.checkout_previous_branch()
        rebase_result = self.repo.rebase(TRUNK)
        if not rebase_result:
            raise ValueError("Rebase was not successful, see previous error messages")

        self.repo.diff_check()

        patch_dir = FileUtils.join_path(self.patch_dir, patch_branch)
        FileUtils.ensure_dir_created(patch_dir)
        found_patches = FileUtils.find_files(patch_dir, regex=patch_branch + "\\.\\d.*\\.patch$", single_level=True)
        new_patch_filename, new_patch_num = PatchUtils.get_next_filename(patch_dir, found_patches)

        # Double-check new filename vs. putting it altogether manually
        new_patch_filename_sanity = FileUtils.join_path(
            self.patch_dir, patch_branch, patch_branch + "." + str(new_patch_num) + ".patch"
        )

        # If this is a new patch, use the appended name,
        # Otherwise, use the generated filename
        if new_patch_num == "001":
            new_patch_filename = new_patch_filename_sanity
        if new_patch_filename != new_patch_filename_sanity:
            raise ValueError(
                "File paths do not match. Calculated: {}, Concatenated: {}".format(
                    new_patch_filename, new_patch_filename_sanity
                )
            )

        diff = self.repo.diff(TRUNK)
        result = PatchUtils.save_diff_to_patch_file(diff, new_patch_filename)
        if not result:
            raise ValueError("Failed to save patch. See previous error messages for details.")

        LOG.info("Created patch file: %s [size: %s]", new_patch_filename, FileUtils.get_file_size(new_patch_filename))

        # Sanity check: try to apply patch
        self.repo.checkout_branch(TRUNK)

        LOG.info("Trying to apply patch %s", new_patch_filename)
        result = self.repo.apply_check(new_patch_filename)
        if not result:
            raise ValueError("Patch does not apply to {}! Patch file: {}".format(TRUNK, new_patch_filename))
        else:
            LOG.info("Patch file applies cleanly to %s. Patch file: %s", TRUNK, new_patch_filename)

        # Checkout old branch
        self.repo.checkout_previous_branch()

        return new_patch_filename
