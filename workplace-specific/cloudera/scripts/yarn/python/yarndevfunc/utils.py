from pythoncommons.string_utils import StringUtils
from tabulate import tabulate


class ResultPrinter:
    @staticmethod
    def print_table(data, row_callback, header, print_result=True, max_width=None, max_width_separator=" "):
        converted_data = ResultPrinter.convert_list_data(
            data, row_callback, max_width=max_width, max_width_separator=max_width_separator
        )
        tabulated = tabulate(converted_data, header, tablefmt="fancy_grid")
        if print_result:
            print(tabulated)
        else:
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
    def convert_list_data(src_data, row_callback, max_width=None, max_width_separator=" "):
        dest_data = []
        for idx, data_row in enumerate(src_data):
            tup = row_callback(data_row)
            converted_row = [idx + 1]
            for t in tup:
                if isinstance(t, list):
                    t = ", ".join(t)
                elif isinstance(t, bool):
                    t = "X" if t else "-"
                if max_width and isinstance(t, str):
                    t = StringUtils.convert_string_to_multiline(t, max_line_length=80, separator=max_width_separator)
                converted_row.append(t)
            dest_data.append(converted_row)

        return dest_data
