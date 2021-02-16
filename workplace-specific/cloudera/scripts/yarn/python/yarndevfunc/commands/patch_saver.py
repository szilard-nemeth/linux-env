import logging

from pythoncommons.file_utils import FileUtils
from pythoncommons.patch_utils import PatchUtils

from yarndevfunc.constants import ORIGIN, PATCH_FILE_REGEX, PATCH_EXTENSION, FIRST_PATCH_NUMBER

LOG = logging.getLogger(__name__)


class PatchSaver:
    """
    A class used to save a patch file based on the current branch and the specified base branch.

    Attributes
    ----------
    args : object
        Command line arguments passed to this command.
    repo : GitWrapper
        A GitWrapper object, representing the repository.
    patch_basedir : str
        Base directory of the generated patches.
    base_branch : str
        The refspec to use as base branch for git diff comparison

    patch_branch : str
        The current branch. This is an attribute dynamically set upon validation of current git branch.
    new_patch_filename : str
        The filename of the generated patch.
    Methods
    -------
    run()
        Executes this command.
        The steps are roughly are:
        1. Validate current branch: Current branch should different than base branch.
        2. Sync branch with upstream changes: Rebase branch to origin/<base_branch>.
        3. Run git diff --check
        4. Determine filename of the new patch.
        5. Save patch file to disk.
        6. Try to apply the created patch file on top of the base branch, as sanity check.
        7. Checkout original branch.
    """

    def __init__(self, args, repo, patch_dir, base_branch):
        self.args = args
        self.repo = repo
        self.patch_basedir = patch_dir
        self.base_branch = base_branch

        # Dynamic attributes
        self.patch_branch = None
        self.new_patch_filename = None

    def run(self):
        # TODO add force mode: ignore whitespace issues and make backup of patch!
        # TODO add another mode: Create patch based on changes in staged area, not commits
        self.validate_current_branch()

        # TODO if there's no commit between trunk..branch, don't move forward and exit
        # TODO check if git is clean (no modified, unstaged files, etc)
        self.sync_branch_with_upstream_changes()
        self.repo.diff_check()
        self.determine_new_patch_filename()
        self.save_patch_file()
        # Sanity check: try to apply the created patch
        self.try_to_apply_created_patch_to_base_branch()

        # Checkout original branch
        self.repo.checkout_previous_branch()

        return self.new_patch_filename

    def validate_current_branch(self):
        curr_branch = self.repo.get_current_branch_name()
        LOG.info("Current branch: %s", curr_branch)
        if curr_branch == self.base_branch:
            raise ValueError(
                f"Cannot make patch, current branch is {self.base_branch}. "
                "Please use a different branch than this branch!"
            )
        self.patch_branch = curr_branch

    def sync_branch_with_upstream_changes(self):
        self.repo.checkout_branch(self.base_branch)
        self.repo.pull(ORIGIN)
        self.repo.checkout_previous_branch()
        rebase_result = self.repo.rebase(self.base_branch)
        if not rebase_result:
            raise ValueError("Rebase was not successful, see previous error messages")

    def determine_new_patch_filename(self):
        patch_dir = FileUtils.join_path(self.patch_basedir, self.patch_branch)
        FileUtils.ensure_dir_created(patch_dir)
        found_patches = FileUtils.find_files(patch_dir, regex=self.patch_branch + PATCH_FILE_REGEX, single_level=True)
        new_patch_filename, new_patch_num = PatchUtils.get_next_filename(patch_dir, found_patches)

        # Double-check new filename vs. putting it altogether manually
        new_patch_filename_sanity = FileUtils.join_path(
            self.patch_basedir, self.patch_branch, self.patch_branch + "." + str(new_patch_num) + PATCH_EXTENSION
        )

        # If this is a new patch, use the appended name,
        # Otherwise, use the generated filename
        if new_patch_num == FIRST_PATCH_NUMBER:
            new_patch_filename = new_patch_filename_sanity
        if new_patch_filename != new_patch_filename_sanity:
            raise ValueError(
                "File paths do not match. "
                f"Calculated: {new_patch_filename}, Concatenated: {new_patch_filename_sanity}"
            )
        self.new_patch_filename = new_patch_filename

    def save_patch_file(self):
        diff = self.repo.diff(self.base_branch)
        result = PatchUtils.save_diff_to_patch_file(diff, self.new_patch_filename)
        if not result:
            raise ValueError("Failed to save patch file. See previous error messages for details.")
        LOG.info(
            "Created patch file: '%s' [size: %s]",
            self.new_patch_filename,
            FileUtils.get_file_size(self.new_patch_filename),
        )

    def try_to_apply_created_patch_to_base_branch(self):
        self.repo.checkout_branch(self.base_branch)
        LOG.info("Trying to apply patch file '%s'", self.new_patch_filename)
        result = self.repo.apply_check(self.new_patch_filename)
        if not result:
            raise ValueError(f"Patch file '{self.new_patch_filename}' does not apply to {self.base_branch}!")
        else:
            LOG.info("Patch file '%s' applies cleanly to %s.", self.new_patch_filename, self.base_branch)
