import logging
from typing import List
from pythoncommons.file_utils import FileUtils
from yarndevfunc.constants import LATEST_SESSION, LATEST_LOG, LATEST_DATA_ZIP
from yarndevfunc.utils import FileUtils2

LOG = logging.getLogger(__name__)


class Config:
    def __init__(self, args, input_files: List[str], project_basedir):
        self.input_files = input_files
        self.output_dir = args.dest_dir if "dest_dir" in args else None
        self.dest_filename = args.dest_filename
        self.project_out_root = project_basedir


class ZipLatestCommandData:
    def __init__(self, args, project_basedir: str):
        self.zip_these_files = [LATEST_LOG, LATEST_SESSION]
        self.input_files = self._validate(self.zip_these_files, project_basedir)
        self.config = Config(args, self.input_files, project_basedir)

    def _validate(self, input_files: List[str], project_basedir: str):
        return self._check_input_files(input_files, project_basedir)

    @staticmethod
    def _check_input_files(input_files: List[str], project_basedir: str):
        resolved_files = [FileUtils.join_path(project_basedir, f) for f in input_files]
        not_found_files = []

        # Sanity check
        for f in resolved_files:
            exists = FileUtils.does_file_exist(f)
            if not exists:
                not_found_files.append(f)
        if len(not_found_files) > 0:
            raise ValueError(f"The following files could not be found: {not_found_files}")
        return resolved_files

    def run(self):
        LOG.info(
            "Starting zipping latest command data... \n "
            f"PLEASE NOTE THAT ACTUAL OUTPUT DIR AND DESTINATION FILES CAN CHANGE, IF NOT SPECIFIED\n"
            f"Output dir: {self.config.output_dir}\n"
            f"Input files: {self.config.input_files}\n "
            f"Destination filename: {self.config.dest_filename}\n "
        )
        if self.config.output_dir:
            dest_filepath = FileUtils.join_path(self.config.output_dir, self.config.dest_filename)
            zip_file = FileUtils2.create_zip_file(self.config.input_files, dest_filepath)
        else:
            zip_file = FileUtils2.create_zip_as_tmp_file(self.config.input_files, self.config.dest_filename)
        LOG.info(f"Finished writing command data to zip file: {zip_file.name}")
        FileUtils2.create_symlink(LATEST_DATA_ZIP, zip_file.name, self.config.project_out_root)
