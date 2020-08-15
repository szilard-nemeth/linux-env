import errno
import logging
import os
import re

import humanize

REVIEW_BRANCH_SEP = '-'

LOG = logging.getLogger(__name__)


def auto_str(cls):
    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )

    cls.__str__ = __str__
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
    def ensure_file_exists(cls, path):
        if not os.path.exists(path):
            raise ValueError("No such file or directory: {}".format(path))

    @classmethod
    def verify_if_dir_is_created(cls, path, raise_ex=True):
        if not os.path.exists(path) or not os.path.isdir(path):
            if raise_ex:
                raise ValueError("Directory is not created under path: " + path)
            return False
        return True

    @classmethod
    def find_files(cls, basedir, regex=None, single_level=False):
        regex = re.compile(regex)

        res_files = []
        for root, dirs, files in os.walk(basedir):
            for file in files:
                if regex.match(file):
                    res_files.append(file)
            if single_level:
                return res_files

        return res_files

    @classmethod
    def save_to_file(cls ,file_path, contents):
        file = open(file_path, 'w')
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

class DateTimeUtils:
    @staticmethod
    def get_current_datetime(format='%Y%m%d_%H%M%S'):
        from datetime import datetime
        now = datetime.now()
        return now.strftime(format)
