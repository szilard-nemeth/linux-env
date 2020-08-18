import errno
import logging
import os
import re
import math
import humanize
import requests
from bs4 import BeautifulSoup
import pickle

from tabulate import tabulate

REVIEW_BRANCH_SEP = '-'

LOG = logging.getLogger(__name__)


def auto_str(cls, with_repr=True):
    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )

    def __repr__(self):
        return __str__(self)

    cls.__str__ = __str__

    if with_repr:
        cls.__repr__ = __repr__
    return cls


def auto_repr(cls):
    def __repr__(self):
        return self.__str__()

    cls.__repr__ = __repr__
    return cls


class StringUtils:
    @staticmethod
    def filter_list_by_regex(list, regex):
        import re
        p = re.compile(regex)
        return [s for s in list if p.match(s)]

    @staticmethod
    def extract_patch_number_from_filename_as_int(filename):
        # Assuming filename like: '/somedir/YARN-10277-test.0003.patch'
        return int(filename.split('.')[-2])

    @staticmethod
    def extract_patch_number_from_filename_as_str(filename):
        # Assuming filename like: '/somedir/YARN-10277-test.0003.patch'
        return filename.split('.')[-2]

    @staticmethod
    def count_leading_zeros(s):
        count = 0
        for i in range(len(s)):
            if s[i] != '0':
                return count
            count += 1

    @staticmethod
    def increase_numerical_str(string):
        num_zeros = StringUtils.count_leading_zeros(string)
        format_str = '%0' + str(num_zeros + 1) + 'd'
        return format_str % (int(string) + 1)

    @staticmethod
    def get_next_patch_filename(filename):
        split = filename.split('.')
        increased_str = StringUtils.increase_numerical_str(split[-2])
        split[-2] = increased_str
        return '.'.join(split)

    @staticmethod
    def ensure_matches_pattern(string, regex, raise_exception=False):
        import re
        regex_obj = re.compile(regex)
        result = regex_obj.match(string)
        if raise_exception and not result:
            raise ValueError("String '{}' does not math regex pattern: {}".format(string, regex))
        return result

    @staticmethod
    def get_matched_group(str, regex, group):
        match = re.match(regex, str)
        if not match or len(match.groups()) < group:
            raise ValueError("String '{}' does not have match with group number '{}'. Regex: '{}', Match object: '{}'", str, group, regex, match)
        return match.group(group)

    @staticmethod
    def convert_string_to_multiline(string, max_line_length, separator=' '):
        if not len(string) > max_line_length:
            return string

        result = ""
        curr_line_length = 0
        parts = string.split(separator)
        for idx, part in enumerate(parts):
            if curr_line_length + len(part) < max_line_length:
                result += part
                # Add length of part + 1 for space to current line length, if required
                curr_line_length += len(part)
            else:
                result += '\n'
                result += part
                curr_line_length = len(part)

            # If not last one, add separator
            if not idx == len(parts) - 1:
                result += separator
                curr_line_length += 1

        return result

    @staticmethod
    def generate_header_line(string, char='=', length=80):
        result = ""
        fill_length = length - len(string)
        filler = char * (math.floor(fill_length / 2))
        result += filler
        result += string
        result += filler
        return result


class PatchUtils:
    @staticmethod
    def get_next_filename(patch_dir, list_of_prev_patches):
        list_of_prev_patches = sorted(list_of_prev_patches, reverse=True)
        LOG.info("Found patches: %s", list_of_prev_patches)
        if len(list_of_prev_patches) == 0:
            return os.path.join(patch_dir, "001"), "001"
        else:
            latest_patch = list_of_prev_patches[0]
            last_patch_num = StringUtils.extract_patch_number_from_filename_as_str(latest_patch)
            next_patch_filename = StringUtils.get_next_patch_filename(latest_patch)
            return os.path.join(patch_dir, next_patch_filename), StringUtils.increase_numerical_str(last_patch_num)

    @staticmethod
    def get_next_review_branch_name(branches):
        # review-YARN-10277-3
        # review-YARN-10277-2
        # review-YARN-10277
        sorted_branches = sorted(branches, reverse=True)
        if len(sorted_branches) == 0:
            raise ValueError("Expected a list of branches with size 1 at least. List: %s", sorted_branches)

        latest_branch = sorted_branches[0]
        parts = latest_branch.split(REVIEW_BRANCH_SEP)

        if len(parts) < 3:
            raise ValueError("Expected at least 3 components (separated by '-') of branch name: {}, encountered: {}",
                             latest_branch, len(parts))

        # No branch postfix, e.g. review-YARN-10277
        if len(parts) == 3:
            return REVIEW_BRANCH_SEP.join(parts) + REVIEW_BRANCH_SEP + '2'
        elif len(parts) == 4:
            return REVIEW_BRANCH_SEP.join(parts[0:3]) + REVIEW_BRANCH_SEP + StringUtils.increase_numerical_str(parts[3])
        else:
            raise ValueError("Unexpected number of components (separated by '-') of branch name: {}, encountered # of components: {}",
                             latest_branch, len(parts))

    @staticmethod
    def save_diff_to_patch_file(diff, file):
        if not diff or diff == "":
            LOG.error("Diff was empty. Patch file is not created!")
            return False
        else:
            diff += os.linesep
            LOG.info("Saving diff to patch file: %s", file)
            LOG.debug("Diff: %s", diff)
            FileUtils.save_to_file(file, diff)
            return True


class FileUtils:
    @classmethod
    def ensure_dir_created(cls, dirname, log_exception=False):
        """
    Ensure that a named directory exists; if it does not, attempt to create it.
    """
        try:
            os.makedirs(dirname)
        except OSError as e:
            if log_exception:
                LOG.exception("Failed to create dirs", exc_info=True)
            # If Errno is File exists, don't raise Exception
            if e.errno != errno.EEXIST:
                raise
        return dirname

    @classmethod
    def ensure_file_exists(cls, path, create=False):
        if not path:
            raise ValueError("Path parameter should not be None or empty!")

        if not create and not os.path.exists(path):
            raise ValueError("No such file or directory: {}".format(path))

        path_comps = path.split(os.sep)
        dirs = path_comps[:-1]
        dirpath = os.sep.join(dirs)
        if not os.path.exists(dirpath):
            LOG.info("Creating dirs: %s", dirpath)
            FileUtils.ensure_dir_created(dirpath, log_exception=False)

        if not os.path.exists(path):
            # Create empty file: https://stackoverflow.com/a/12654798/1106893
            LOG.info("Creating file: %s", path)
            open(path, 'a').close()

    @classmethod
    def does_file_exist(cls, file):
        return os.path.exists(file)

    @classmethod
    def create_files(cls, *files):
        for file in files:
            FileUtils.ensure_file_exists(file, create=True)

    @classmethod
    def verify_if_dir_is_created(cls, path, raise_ex=True):
        if not os.path.exists(path) or not os.path.isdir(path):
            if raise_ex:
                raise ValueError("Directory is not created under path: " + path)
            return False
        return True

    @classmethod
    def find_files(cls, basedir, regex=None, single_level=False, full_path_result=False):
        regex = re.compile(regex)

        res_files = []
        for root, dirs, files in os.walk(basedir):
            for file in files:
                if regex.match(file):
                    if full_path_result:
                        res_files.append(os.path.join(root, file))
                    else:
                        res_files.append(file)
            if single_level:
                return res_files

        return res_files

    @classmethod
    def save_to_file(cls, file_path, contents):
        FileUtils.ensure_file_exists(file_path, create=True)
        file = open(file_path, 'w')
        file.write(contents)
        file.close()

    @classmethod
    def append_to_file(cls, file_path, contents):
        file = open(file_path, 'a')
        file.write(contents)
        file.close()

    @classmethod
    def get_file_size(cls, file_path, human_readable=True):
        from pathlib import Path
        size = Path(file_path).stat().st_size
        if human_readable:
            return humanize.naturalsize(size, gnu=True)
        else:
            return str(size)

    @classmethod
    def path_basename(cls, path):
        return os.path.basename(path)

    @classmethod
    def join_path(cls, *components):
        return os.path.join(*components)

    @classmethod
    def get_mod_date_of_file(cls, file):
        return os.path.getmtime(file)

    @classmethod
    def get_mod_dates_of_files(cls, basedir, *files):
        result = {}
        for f in files:
            f = FileUtils.join_path(basedir, f)
            if FileUtils.does_file_exist(f):
                result[f] = FileUtils.get_mod_date_of_file(f)
            else:
                result[f] = None
        return result

class DateTimeUtils:
    @staticmethod
    def get_current_datetime(format='%Y%m%d_%H%M%S'):
        from datetime import datetime
        now = datetime.now()
        return now.strftime(format)


class JiraUtils:
    @staticmethod
    def download_jira_html(jira_id, to_file):
        resp = requests.get("https://issues.apache.org/jira/browse/{jira_id}".format(jira_id=jira_id))
        resp.raise_for_status()
        FileUtils.save_to_file(to_file, resp.text)
        return resp.text

    @staticmethod
    def parse_subjiras_from_umbrella_html(html_doc, to_file, filter_ids):
        soup = BeautifulSoup(html_doc, 'html.parser')
        issue_keys = []
        for link in soup.find_all('a', attrs={'class': 'issue-link'}):
            issue_keys.append(link.attrs['data-issue-key'])

        if filter_ids:
            LOG.info("Filtering ids from result list: %s", filter_ids)
            issue_keys = [issue for issue in issue_keys if issue not in filter_ids]

        # Filter dupes
        issue_keys = list(set(issue_keys))
        FileUtils.save_to_file(to_file, '\n'.join(issue_keys))
        return issue_keys


class PickleUtils:
    @staticmethod
    def dump(data, file):
        with open(file, 'wb') as f:
            pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load(file):
        with open(file, 'rb') as f:
            # The protocol version used is detected automatically, so we do not
            # have to specify it.
            return pickle.load(f)


class ResultPrinter:
    @staticmethod
    def print_table(data, row_callback, header, print_result=True, max_width=None, max_width_separator=' '):
        converted_data = ResultPrinter.convert_list_data(data, row_callback, max_width=max_width,
                                                         max_width_separator=max_width_separator)
        tabulated = tabulate(converted_data, header, tablefmt="fancy_grid")
        if print_result:
            print(tabulated)
        else:
            return tabulated

    @staticmethod
    def print_table_html(data, row_callback, header, print_result=True, max_width=None, max_width_separator=' '):
        converted_data = ResultPrinter.convert_list_data(data, row_callback, max_width=max_width,
                                                         max_width_separator=max_width_separator)
        tabulated = tabulate(converted_data, header, tablefmt="html")
        if print_result:
            print(tabulated)
        else:
            return tabulated

    @staticmethod
    def convert_list_data(src_data, row_callback, max_width=None, max_width_separator=' '):
        dest_data = []
        for idx, data_row in enumerate(src_data):
            tup = row_callback(data_row)
            converted_row = [idx + 1]
            for t in tup:
                if max_width and isinstance(t, str):
                    t = StringUtils.convert_string_to_multiline(t, max_line_length=80, separator=max_width_separator)
                converted_row.append(t)
            dest_data.append(converted_row)

        return dest_data

