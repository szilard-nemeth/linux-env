import errno
import logging
import os
import tempfile
import zipfile
from enum import Enum
from typing import Tuple, List

from colr import color
from pythoncommons.file_utils import FileUtils
from pythoncommons.string_utils import StringUtils, auto_str
from tabulate import tabulate

LOG = logging.getLogger(__name__)

# TODO Move all of these classes to python-commons lib


# TODO move to python-commons / file utils
class FileUtils2:
    @staticmethod
    def create_symlink(link_name, linked_path, dest_dir, remove_if_exists=True):
        link_src = linked_path
        link_dest = FileUtils.join_path(dest_dir, link_name)
        if remove_if_exists and os.path.exists(link_dest):
            os.remove(link_dest)

        LOG.info("Creating symlink: %s -> %s", link_dest, link_src)
        # os.symlink(src, dest)
        # src: Already existing path to create the link pointing to
        # dest: Link name
        try:
            os.symlink(link_src, link_dest)
        except OSError as e:
            if e.errno == errno.EEXIST:
                LOG.warning("Symlink does exist, ignoring. Details: %s", str(e))

    @staticmethod
    def create_zip_as_tmp_file(src_files: List[str], filename: str):
        filename, suffix = FileUtils2._validate_zip_file_name(filename)
        tmp_file = tempfile.NamedTemporaryFile(prefix=filename, suffix=suffix, delete=False)
        return FileUtils2._create_zip_file(src_files, tmp_file)

    @staticmethod
    def create_zip_file(src_files: List[str], filename: str):
        return FileUtils2._create_zip_file(src_files, open(filename, mode="wb"))

    @staticmethod
    def extract_zip_file(file: str, path: str):
        # Apparently, ZipFile does not resolve symlinks so let's do it manually
        if os.path.islink(file):
            file = os.path.realpath(file)
        FileUtils.ensure_file_exists(file)
        zip_file = zipfile.ZipFile(file, "r")
        zip_file.extractall(path)

    @staticmethod
    def _validate_zip_file_name(filename):
        if "." in filename:
            filename_and_ext = filename.split(".")
            if len(filename_and_ext) != 2:
                raise ValueError("Invalid filename: " + filename)
            filename = filename_and_ext[0]
            suffix = "." + filename_and_ext[1]
        else:
            filename = filename
            suffix = ".zip"
        return filename, suffix

    @staticmethod
    def _create_zip_file(src_files, file):
        zip_file = zipfile.ZipFile(file, "w")
        LOG.info(f"Creating zip file. Target file: {zip_file.filename}, Input files: {src_files}")
        for src_file in src_files:
            if FileUtils.is_dir(src_file):
                FileUtils2._add_dir_to_zip(src_file, zip_file)
            else:
                LOG.debug(f"Adding file '{src_file}' to zip file '${zip_file.filename}'")
                zip_file.write(src_file, FileUtils.basename(src_file))
        zip_file.close()
        file.seek(0)
        return file

    @staticmethod
    def _add_dir_to_zip(src_dir, zip_file):
        # Iterate over all the files in directory
        LOG.debug(f"Adding directory '{src_dir}' to zip file '${zip_file.filename}'")
        for folderName, subfolders, filenames in os.walk(src_dir):
            for filename in filenames:
                # create complete filepath of file in directory
                file_path = os.path.join(folderName, filename)
                # Add file to zip
                zip_file.write(file_path, FileUtils.basename(file_path))


class StringUtils2:

    # TODO copied from python-commons, remove later
    @staticmethod
    def list_to_multiline_string(list):
        return "\n".join(str(x) for x in list)

    # TODO copied from python-commons, remove later
    @staticmethod
    def dict_to_multiline_string(dict):
        return "\n".join([f"{k}: {v}" for k, v in dict.items()])


class Color(Enum):
    GREEN = "green"
    RED = "red"


class ColorType(Enum):
    FOREGROUND = "fore"
    BACKROUND = "back"


class MatchType(Enum):
    ALL = "all"
    ANY = "any"


class EvaluationMethod(Enum):
    ALL = 0
    FIRST_TRUTHY = 1


@auto_str
class ColorDescriptor:
    def __init__(
        self,
        type,
        value,
        color: Color,
        match_type: MatchType,
        scan_range: Tuple[int, int],
        colorize_range: Tuple[int, int],
        color_type: ColorType = ColorType.FOREGROUND,
    ):
        self.type = type
        self.value = value
        self.color: Color = color
        self.match_type: MatchType = match_type
        self.scan_range: Tuple[int, int] = scan_range
        self.colorize_range: Tuple[int, int] = colorize_range
        self.color_type = color_type


@auto_str
class ConversionResult:
    def __init__(self, src_data, result_data):
        self.src_data = src_data
        self.dst_data = result_data


@auto_str
class ColorizeConfig:
    def __init__(
        self, descriptors: List[ColorDescriptor], eval_method: EvaluationMethod = EvaluationMethod.FIRST_TRUTHY
    ):
        self.descriptors = descriptors
        self.eval_method = eval_method


@auto_str
class BoolConversionConfig:
    def __init__(self, convert_true_to="X", convert_false_to="-"):
        self.convert_true_to = convert_true_to
        self.convert_false_to = convert_false_to


@auto_str
class ConversionConfig:
    def __init__(
        self,
        join_lists_by_comma: bool = True,
        add_row_numbers: bool = True,
        max_width: int = None,
        max_width_separator: str = " ",
        bool_conversion_config: BoolConversionConfig = None,
        colorize_config: ColorizeConfig = None,
    ):
        self.join_lists_by_comma = join_lists_by_comma
        self.add_row_numbers = add_row_numbers
        self.max_width = max_width
        self.max_width_separator = max_width_separator
        self.bool_conversion_config = bool_conversion_config
        self.colorize_config = colorize_config


class ResultPrinter:
    # TODO Signature can be modified later if all usages migrated to use ConversionConfig object as input
    @staticmethod
    def print_table(
        data,
        row_callback,
        header,
        print_result=True,
        max_width: int = None,
        max_width_separator: str = " ",
        bool_conversion_config: BoolConversionConfig = None,
        colorize_config: ColorizeConfig = None,
    ):
        conversion_config = ConversionConfig(
            max_width=max_width,
            max_width_separator=max_width_separator,
            bool_conversion_config=bool_conversion_config,
            colorize_config=colorize_config,
        )
        conversion_result = ResultPrinter.convert_list_data(data, row_callback, conversion_config)
        # LOG.debug(f"Conversion result: {conversion_result}")
        tabulated = tabulate(conversion_result.dst_data, header, tablefmt="fancy_grid")
        if print_result:
            print(tabulated)
        return tabulated

    @staticmethod
    def print_table_html(data, row_callback, header, print_result=True, max_width=None, max_width_separator=" "):
        converted_data = ResultPrinter.convert_list_data(
            data, row_callback, max_width=max_width, max_width_separator=max_width_separator
        )
        tabulated = tabulate(converted_data, header, tablefmt="html")
        if print_result:
            print(tabulated)
        else:
            return tabulated

    @staticmethod
    def convert_list_data(src_data, row_callback, conf: ConversionConfig):
        result = []
        for idx, src_row in enumerate(src_data):
            row = row_callback(src_row)
            converted_row = []
            if conf.add_row_numbers:
                converted_row.append(idx + 1)
            for cell in row:
                if conf.join_lists_by_comma and isinstance(cell, list):
                    cell = ", ".join(cell)

                bcc = conf.bool_conversion_config
                if bcc and isinstance(cell, bool):
                    cell = bcc.convert_true_to if cell else bcc.convert_false_to
                if conf.max_width and isinstance(cell, str):
                    cell = StringUtils.convert_string_to_multiline(
                        cell, max_line_length=conf.max_width, separator=conf.max_width_separator
                    )
                converted_row.append(cell)

            if conf.colorize_config:
                ResultPrinter._colorize_row(conf.colorize_config, converted_row, row)
            result.append(converted_row)

        return ConversionResult(src_data, result)

    @staticmethod
    def _colorize_row(conf: ColorizeConfig, converted_row, row):
        row_as_list = list(row)
        truthy = []
        for cd in conf.descriptors:
            filtered_type_values = list(
                filter(lambda x: type(x) == cd.type, row_as_list[cd.scan_range[0] : cd.scan_range[1]])
            )
            match_count = 0
            for idx, val in enumerate(filtered_type_values):
                if val == cd.value:
                    match_count += 1
            if cd.match_type == MatchType.ANY and match_count > 0:
                truthy.append(cd)
            elif cd.match_type == MatchType.ALL and match_count == len(filtered_type_values):
                truthy.append(cd)

        for cd in truthy:
            color_args = {cd.color_type.value: cd.color.value}
            for i in range(*cd.colorize_range):
                # Color multiline strings line by line
                if "\n" in str(converted_row[i]):
                    lines = converted_row[i].splitlines()
                    colored = []
                    for idx, line in enumerate(lines):
                        colored.append(color(line, **color_args))
                    converted_row[i] = "\n".join(colored)
                else:
                    converted_row[i] = color(converted_row[i], **color_args)
            if conf.eval_method == EvaluationMethod.FIRST_TRUTHY:
                break
