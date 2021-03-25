import logging
from collections import namedtuple
from enum import Enum
from typing import Optional, TypeVar, Any, Union, Tuple, List

from colr import color
from pythoncommons.string_utils import StringUtils, auto_str
from tabulate import tabulate

LOG = logging.getLogger(__name__)

# TODO Move all of these classes to python-commons lib


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
        LOG.debug(f"Conversion result: {conversion_result}")
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
