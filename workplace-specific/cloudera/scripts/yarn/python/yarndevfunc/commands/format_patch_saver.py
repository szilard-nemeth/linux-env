import logging
from os.path import expanduser

from git import InvalidGitRepositoryError

from yarndevfunc.git_wrapper import GitWrapper
from yarndevfunc.utils import FileUtils

LOG = logging.getLogger(__name__)


class FormatPatchSaver:
    def __init__(self, args, working_dir, date_suffix):
        self.working_dir = working_dir
        self.base_refspec = args.base_refspec
        self.other_refspec = args.other_refspec
        self.dest_basedir = args.dest_basedir
        self.dest_dir_prefix = args.dest_dir_prefix
        self.date_suffix = date_suffix

    def run(self):
        # TODO check if git is clean (no modified, unstaged files, etc)
        try:
            repo = GitWrapper(self.working_dir)
        except InvalidGitRepositoryError as e:
            raise ValueError("Current working directory is not a git repo: {}".format(self.working_dir))

        if self.base_refspec == self.other_refspec:
            raise ValueError("Specified base refspec '{}' is the same as other refspec '{}'"
                             .format(self.base_refspec, self.other_refspec))

        exists = repo.is_branch_exist(self.base_refspec)
        if not exists:
            raise ValueError("Specified base refspec is not valid: {}".format(self.base_refspec))

        exists = repo.is_branch_exist(self.other_refspec)
        if not exists:
            raise ValueError("Specified other refspec is not valid: {}".format(self.base_refspec))

        # Check if dest_basedir exists
        dest_basedir = expanduser(self.dest_basedir)
        patch_file_dest_path = FileUtils.join_path(dest_basedir, self.dest_dir_prefix, self.date_suffix)
        FileUtils.ensure_dir_created(patch_file_dest_path)

        refspec = '{}..{}'.format(self.base_refspec, self.other_refspec)
        LOG.info("Saving git patches based on refspec '%s', to directory: %s", refspec, patch_file_dest_path)
        repo.format_patch(refspec, output_dir=patch_file_dest_path, full_index=True)
