import logging
import os
from enum import Enum
from typing import Dict, List, Tuple, Set
from git import Commit
from pythoncommons.date_utils import DateUtils
from pythoncommons.file_utils import FileUtils
from pythoncommons.string_utils import StringUtils
from yarndevfunc.command_runner import CommandRunner
from yarndevfunc.commands.upstream_jira_umbrella_fetcher import CommitData
from yarndevfunc.constants import ANY_JIRA_ID_PATTERN
from yarndevfunc.git_wrapper import GitWrapper
from yarndevfunc.utils import (
    ResultPrinter,
    BoolConversionConfig,
    ColorizeConfig,
    ColorDescriptor,
    MatchType,
    Color,
    EvaluationMethod,
    StringUtils2,
)


LOG = logging.getLogger(__name__)


class BranchType(Enum):
    FEATURE = "feature branch"
    MASTER = "master branch"


class BranchData:
    def __init__(self, type: BranchType, branch_name: str):
        self.type: BranchType = type
        self.name: str = branch_name
        self.shortname = branch_name.split("/")[1] if "/" in branch_name else branch_name

        # Set later
        self.gitlog_results: List[str] = []
        # Commit objects in reverse order (from oldest to newest)
        # Commits stored in a list, in order from last to first commit (descending)
        self.commit_objs: List[CommitData] = []
        self.commits_before_merge_base: List[CommitData] = []
        self.commits_after_merge_base: List[CommitData] = []
        self.hash_to_index: Dict[str, int] = {}  # Dict: commit hash to commit index
        self.jira_id_to_commit: Dict[str, CommitData] = {}  # Dict: Jira ID (e.g. YARN-1234) to CommitData object
        self.unique_commits: List[CommitData] = []
        self.merge_base_idx: int = -1

    @property
    def number_of_commits(self):
        return len(self.gitlog_results)

    def set_merge_base(self, merge_base: CommitData):
        merge_base_hash = merge_base.hash
        if merge_base_hash not in self.hash_to_index:
            raise ValueError("Merge base cannot be found among commits. Merge base hash: " + merge_base_hash)
        self.merge_base_idx = self.hash_to_index[merge_base_hash]

        if len(self.commit_objs) == 0:
            raise ValueError("set_merge_base is invoked while commit list was empty!")
        self.commits_before_merge_base = self.commit_objs[: self.merge_base_idx]
        self.commits_after_merge_base = self.commit_objs[self.merge_base_idx :]


class SummaryData:
    def __init__(self, output_dir: str, branch_data: Dict[BranchType, BranchData]):
        self.output_dir: str = output_dir
        self.branch_data: Dict[BranchType, BranchData] = branch_data
        self.merge_base: CommitData = None

        # Dict-based data structures, key: BranchType
        self.branch_names: Dict[BranchType, str] = {br_type: br_data.name for br_type, br_data in branch_data.items()}
        self.number_of_commits: Dict[BranchType, int] = {}
        self.all_commits_with_missing_jira_id: Dict[BranchType, List[CommitData]] = {}
        self.commits_with_missing_jira_id: Dict[BranchType, List[CommitData]] = {}
        self.commits_with_missing_jira_id_filtered: Dict[BranchType, Dict] = {}
        self.unique_commits: Dict[BranchType, List[CommitData]] = {}

        # List-based data structures
        self.common_commits_before_merge_base: List[CommitData] = []
        self.common_commits_after_merge_base: List[Tuple[CommitData, CommitData]] = []

        # Commits matched by message with missing Jira ID
        self.common_commits_matched_by_message: List[Tuple[CommitData, CommitData]] = []

        # Commits matched by Jira ID but not by message
        self.common_commits_matched_by_jira_id: List[Tuple[CommitData, CommitData]] = []

        # Commits matched by Jira ID and by message as well
        self.common_commits_matched_both: List[Tuple[CommitData, CommitData]] = []

        self.unique_jira_ids_legacy_script: Dict[BranchType, List[str]] = {}

    @property
    def common_commits(self):
        return [c[0] for c in self.common_commits_after_merge_base]

    @property
    def all_commits(self):
        all_commits: List[CommitData] = (
            [] + self.unique_commits[BranchType.MASTER] + self.unique_commits[BranchType.FEATURE] + self.common_commits
        )
        all_commits.sort(key=lambda c: c.date, reverse=True)
        return all_commits

    @property
    def all_commits_presence_matrix(self) -> List[List]:
        rows: List[List] = []
        for commit in self.all_commits:
            jira_id = commit.jira_id
            row = [jira_id, commit.message, commit.date]

            presence = []
            if self.is_jira_id_present_on_branch(jira_id, BranchType.MASTER) and self.is_jira_id_present_on_branch(
                jira_id, BranchType.FEATURE
            ):
                presence = [True, True]
            elif self.is_jira_id_present_on_branch(jira_id, BranchType.MASTER):
                presence = [True, False]
            elif self.is_jira_id_present_on_branch(jira_id, BranchType.FEATURE):
                presence = [False, True]
            row.extend(presence)
            rows.append(row)
        return rows

    def get_branch_names(self):
        return [bd.name for bd in self.branch_data.values()]

    def get_branch(self, br_type: BranchType):
        return self.branch_data[br_type]

    def is_jira_id_present_on_branch(self, jira_id: str, br_type: BranchType):
        br: BranchData = self.get_branch(br_type)
        return jira_id in br.jira_id_to_commit

    def __str__(self):
        res = ""
        res += f"Output dir: {self.output_dir}\n"

        res += "\n\n=====Stats: BRANCHES=====\n"
        for br_type, br_name in self.branch_names.items():
            res += f"Number of commits on {br_type.value} '{br_name}': {self.number_of_commits[br_type]}\n"

        res += "\n\n=====Stats: UNIQUE COMMITS=====\n"
        for br_type, br_name in self.branch_names.items():
            res += f"Number of unique commits on {br_type.value} '{br_name}': {len(self.unique_commits[br_type])}\n"

        res += "\n\n=====Stats: UNIQUE COMMITS [LEGACY SCRIPT]=====\n"
        for br_type, br_name in self.branch_names.items():
            res += f"Number of unique commits on {br_type.value} '{br_name}': {len(self.unique_jira_ids_legacy_script[br_type])}\n"

        res += "\n\n=====Stats: COMMON=====\n"
        res += f"Merge-base commit: {self.merge_base.hash} {self.merge_base.message} {self.merge_base.date}\n"
        res += f"Number of common commits before merge-base: {len(self.common_commits_before_merge_base)}\n"
        res += f"Number of common commits after merge-base: {len(self.common_commits_after_merge_base)}\n"

        for br_type, br_name in self.branch_names.items():
            res += f"\n\n=====Stats: COMMITS WITH MISSING JIRA ID ON BRANCH: {br_name}=====\n"
            res += (
                f"Number of all commits with missing Jira ID: {len(self.all_commits_with_missing_jira_id[br_type])}\n"
            )
            res += (
                f"Number of commits with missing Jira ID after merge-base: "
                f"{len(self.commits_with_missing_jira_id[br_type])}\n"
            )
            res += (
                f"Number of commits with missing Jira ID after merge-base, filtered by author exceptions: "
                f"{len(self.commits_with_missing_jira_id_filtered[br_type])}\n"
            )

        res += "\n\n=====Stats: COMMON COMMITS ACROSS BRANCHES=====\n"
        res += (
            f"Number of common commits with missing Jira ID, matched by commit message: "
            f"{len(self.common_commits_matched_by_message)}\n"
        )
        res += (
            f"Number of common commits with matching Jira ID but different commit message: "
            f"{len(self.common_commits_matched_by_jira_id)}\n"
        )
        res += (
            f"Number of common commits with matching Jira ID and commit message: "
            f"{len(self.common_commits_matched_both)}\n"
        )
        return res


class BranchComparatorConfig:
    def __init__(self, output_dir: str, args):
        self.output_dir = FileUtils.ensure_dir_created(
            FileUtils.join_path(output_dir, f"session-{DateUtils.now_formatted('%Y%m%d_%H%M%S')}")
        )
        self.commit_author_exceptions = args.commit_author_exceptions
        self.console_mode = True if "console_mode" in args and args.console_mode else False
        self.fail_on_missing_jira_id = False

        workplace_specific_dir = FileUtils.find_repo_root_dir(__file__, "workplace-specific")
        cloudera_dir = FileUtils.join_path(workplace_specific_dir, "cloudera")
        self.git_compare_script = BranchComparatorConfig.find_git_compare_script(cloudera_dir)

    @staticmethod
    def find_git_compare_script(parent_dir):
        script = FileUtils.search_files(parent_dir, "git_compare.sh")
        if not script:
            raise ValueError(f"Expected to find file: {script}")
        return script[0]


class Branches:
    def __init__(self, conf: BranchComparatorConfig, repo: GitWrapper, branch_dict: Dict[BranchType, str]):
        self.conf = conf
        self.repo = repo
        self.branch_data: Dict[BranchType, BranchData] = {}
        for br_type in BranchType:
            branch_name = branch_dict[br_type]
            self.branch_data[br_type] = BranchData(br_type, branch_name)
        self.fail_on_missing_jira_id = conf.fail_on_missing_jira_id

        # Set later
        self.merge_base: CommitData = None
        self.summary: SummaryData = SummaryData(self.conf.output_dir, self.branch_data)

    def get_branch(self, br_type: BranchType) -> BranchData:
        return self.branch_data[br_type]

    @staticmethod
    def _generate_filename(basedir, prefix, branch_name="") -> str:
        return FileUtils.join_path(basedir, f"{prefix}{StringUtils.replace_special_chars(branch_name)}")

    def validate(self, br_type: BranchType):
        br_data = self.branch_data[br_type]
        branch_exist = self.repo.is_branch_exist(br_data.name)
        if not branch_exist:
            LOG.error(f"{br_data.type.name} does not exist with name '{br_data.name}'")
        return branch_exist

    def execute_git_log(self, print_stats=True, save_to_file=True):
        for br_type in BranchType:
            branch: BranchData = self.branch_data[br_type]
            branch.gitlog_results = self.repo.log(branch.name, oneline_with_date_and_author=True)
            # Store commit objects in reverse order (ascending by date)
            branch.commit_objs = list(
                reversed(
                    [
                        CommitData.from_git_log_str(
                            commit_str,
                            format="oneline_with_date_and_author",
                            pattern=ANY_JIRA_ID_PATTERN,
                            allow_unmatched_jira_id=True,
                        )
                        for commit_str in branch.gitlog_results
                    ]
                )
            )
            self.summary.all_commits_with_missing_jira_id[br_type] = list(
                filter(lambda c: not c.jira_id, branch.commit_objs)
            )
            LOG.info(f"Found {len(self.summary.all_commits_with_missing_jira_id[br_type])} commits with empty Jira ID")

            LOG.debug(
                f"Found commits with empty Jira ID: {StringUtils.dict_to_multiline_string(self.summary.all_commits_with_missing_jira_id)}"
            )
            if self.fail_on_missing_jira_id:
                raise ValueError(
                    f"Found {len(self.summary.all_commits_with_missing_jira_id)} commits with empty Jira ID!"
                )

            for idx, commit in enumerate(branch.commit_objs):
                branch.hash_to_index[commit.hash] = idx
                branch.jira_id_to_commit[commit.jira_id] = commit
        # This must be executed after branch.hash_to_index is set
        self.get_merge_base()

        self._record_stats_to_summary()
        if print_stats:
            self._print_stats()
        if save_to_file:
            self._write_git_log_to_file()

    def _record_stats_to_summary(self):
        for br_type in BranchType:
            branch: BranchData = self.branch_data[br_type]
            self.summary.number_of_commits[br_type] = branch.number_of_commits

    def _print_stats(self):
        for br_type in BranchType:
            branch: BranchData = self.branch_data[br_type]
            LOG.info(f"Found {branch.number_of_commits} commits on {br_type.value}: {branch.name}")

    def _write_git_log_to_file(self):
        for br_type in BranchType:
            branch: BranchData = self.branch_data[br_type]
            # We would like to maintain descending order of commits in printouts
            self.write_to_file_or_console("git log output", branch, list(reversed(branch.commit_objs)))

    def _save_commits_before_after_merge_base_to_file(self):
        for br_type in BranchType:
            branch: BranchData = self.branch_data[br_type]
            self.write_to_file_or_console("before mergebase commits", branch, branch.commits_before_merge_base)
            self.write_to_file_or_console("after mergebase commits", branch, branch.commits_after_merge_base)

    def get_merge_base(self):
        merge_base: List[Commit] = self.repo.merge_base(
            self.branch_data[BranchType.FEATURE].name, self.branch_data[BranchType.MASTER].name
        )
        if len(merge_base) > 1:
            raise ValueError(f"Ambiguous merge base: {merge_base}.")
        elif len(merge_base) == 0:
            raise ValueError("Merge base not found between branches!")
        self.merge_base = CommitData.from_git_log_str(
            self.repo.log(
                merge_base[0].hexsha,
                oneline_with_date=True,
            )[0],
            allow_unmatched_jira_id=True,
        )
        self.summary.merge_base = self.merge_base
        LOG.info(f"Merge base of branches: {self.merge_base}")
        for br_type in BranchType:
            branch: BranchData = self.branch_data[br_type]
            branch.set_merge_base(self.merge_base)

    def compare(self, commit_author_exceptions):
        self._save_commits_before_after_merge_base_to_file()
        feature_br: BranchData = self.branch_data[BranchType.FEATURE]
        master_br: BranchData = self.branch_data[BranchType.MASTER]

        self._sanity_check_commits_before_merge_base(feature_br, master_br)
        self._check_after_merge_base_commits(feature_br, master_br, commit_author_exceptions)

    def _sanity_check_commits_before_merge_base(self, feature_br: BranchData, master_br: BranchData):
        if len(master_br.commits_before_merge_base) != len(feature_br.commits_before_merge_base):
            raise ValueError(
                "Number of commits before merge_base does not match. "
                f"Feature branch has: {len(feature_br.commits_before_merge_base)} commits, "
                f"Master branch has: {len(master_br.commits_before_merge_base)} commits"
            )
        # Commit hashes up to the merge-base commit should be the same for both branches
        for idx, commit1 in enumerate(master_br.commits_before_merge_base):
            commit2 = feature_br.commits_before_merge_base[idx]
            if commit1.hash != commit2.hash:
                raise ValueError(
                    f"Commit hash mismatch below merge-base commit.\n"
                    f"Index: {idx}\n"
                    f"Hash of commit on {feature_br.name}: {commit2.hash}\n"
                    f"Hash of commit on {master_br.name}: {commit1.hash}"
                )
        self.summary.common_commits_before_merge_base = master_br.commits_before_merge_base
        LOG.info(
            f"Detected {len(self.summary.common_commits_before_merge_base)} common commits before merge-base between "
            f"'{feature_br.name}' and '{master_br.name}'"
        )

    def _check_after_merge_base_commits(
        self, feature_br: BranchData, master_br: BranchData, commit_author_exceptions: List[str]
    ):
        branches = [feature_br, master_br]
        self._handle_commits_with_missing_jira_id(branches)
        self._handle_commits_with_missing_jira_id_filter_author(branches, commit_author_exceptions)

        common_jira_ids: Set[str] = set()
        common_commit_msgs: Set[str] = set()
        # List of tuples. First item: Master branch commit obj, second item: feature branch commit obj
        for master_commit in master_br.commits_after_merge_base:
            master_commit_msg = master_commit.message
            if not master_commit.jira_id:
                # If this commit is without jira id and author was not an element of exceptional authors,
                # then try to match commits across branches by commit message.
                if master_commit_msg in self.summary.commits_with_missing_jira_id_filtered[BranchType.MASTER]:
                    LOG.debug(
                        "Trying to match commit by commit message as Jira ID is missing. Details: \n"
                        f"Branch: master branch\n"
                        f"Commit message: ${master_commit_msg}\n"
                    )
                    # Master commit message found in missing jira id list of the feature branch, record match
                    if master_commit_msg in self.summary.commits_with_missing_jira_id_filtered[BranchType.FEATURE]:
                        LOG.warning(
                            "Found matching commit by commit message. Details: \n"
                            f"Branch: master branch\n"
                            f"Commit message: ${master_commit_msg}\n"
                        )
                        common_commit_msgs.add(master_commit_msg)
                        commit_tuple: Tuple[CommitData, CommitData] = (
                            master_commit,
                            self.summary.commits_with_missing_jira_id_filtered[BranchType.FEATURE][master_commit_msg],
                        )
                        self.summary.common_commits_after_merge_base.append(commit_tuple)
                        self.summary.common_commits_matched_by_message.append(commit_tuple)

            elif master_commit.jira_id in feature_br.jira_id_to_commit:
                # Normal path: Try to match commits across branches by Jira ID
                feature_commit = feature_br.jira_id_to_commit[master_commit.jira_id]
                LOG.debug(
                    "Found same commit on both branches (by Jira ID):\n"
                    f"Master branch commit: {master_commit.as_oneline_string()}\n"
                    f"Feature branch commit: {feature_commit.as_oneline_string()}"
                )

                commit_tuple: Tuple[CommitData, CommitData] = (master_commit, feature_commit)
                if master_commit_msg == feature_commit.message:
                    self.summary.common_commits_matched_both.append(commit_tuple)
                else:
                    LOG.warning(
                        "Jira ID is the same for commits, but commit message differs: \n"
                        f"Master branch commit: {master_commit.as_oneline_string()}\n"
                        f"Feature branch commit: {feature_commit.as_oneline_string()}"
                    )
                    self.summary.common_commits_matched_by_jira_id.append(commit_tuple)

                # Either if commit message matched or not, count this as a common commit as Jira ID matched
                self.summary.common_commits_after_merge_base.append(commit_tuple)
                common_jira_ids.add(master_commit.jira_id)

        self.write_commit_list_to_file_or_console(
            "commit message differs",
            [item for tup in self.summary.common_commits_matched_by_jira_id for item in tup],
            add_sep_to_end=False,
        )

        self.write_commit_list_to_file_or_console(
            "commits matched by message",
            [t[0] for t in self.summary.common_commits_matched_by_message],
            add_sep_to_end=False,
        )

        master_br.unique_commits = self._filter_relevant_unique_commits(
            master_br.commits_after_merge_base,
            self.summary.commits_with_missing_jira_id_filtered[BranchType.MASTER],
            common_jira_ids,
            common_commit_msgs,
        )
        feature_br.unique_commits = self._filter_relevant_unique_commits(
            feature_br.commits_after_merge_base,
            self.summary.commits_with_missing_jira_id_filtered[BranchType.FEATURE],
            common_jira_ids,
            common_commit_msgs,
        )
        LOG.info(f"Identified {len(master_br.unique_commits)} unique commits on branch: {master_br.name}")
        LOG.info(f"Identified {len(feature_br.unique_commits)} unique commits on branch: {feature_br.name}")
        self.summary.unique_commits[BranchType.MASTER] = master_br.unique_commits
        self.summary.unique_commits[BranchType.FEATURE] = feature_br.unique_commits
        self.write_to_file_or_console("unique commits", master_br, master_br.unique_commits)
        self.write_to_file_or_console("unique commits", feature_br, feature_br.unique_commits)

    def _handle_commits_with_missing_jira_id_filter_author(self, branches: List[BranchData], commit_author_exceptions):
        # Create a dict of (commit message, CommitData),
        # filtering all the commits that has author from the exceptional authors.
        # Assumption: Commit message is unique for all commits
        for br_data in branches:
            self.summary.commits_with_missing_jira_id_filtered[br_data.type] = dict(
                [
                    (c.message, c)
                    for c in filter(
                        lambda c: c.author not in commit_author_exceptions,
                        self.summary.commits_with_missing_jira_id[br_data.type],
                    )
                ]
            )
            LOG.warning(
                f"Found {br_data.type.value} commits after merge-base with empty Jira ID "
                f"(after applied author filter: {commit_author_exceptions}): "
                f"{len(self.summary.commits_with_missing_jira_id_filtered[br_data.type])} "
            )
            LOG.debug(
                f"Found {br_data.type.value} commits after merge-base with empty Jira ID "
                f"(after applied author filter: {commit_author_exceptions}): "
                f"{StringUtils2.list_to_multiline_string(self.summary.commits_with_missing_jira_id_filtered[br_data.type])}"
            )
        for br_data in branches:
            self.write_to_file_or_console(
                "commits missing jira id filtered", br_data, self.summary.commits_with_missing_jira_id[br_data.type]
            )

    def _handle_commits_with_missing_jira_id(self, branches: List[BranchData]):
        # TODO write these to file
        for br_data in branches:
            self.summary.commits_with_missing_jira_id[br_data.type]: List[CommitData] = list(
                filter(lambda c: not c.jira_id, br_data.commits_after_merge_base)
            )

            LOG.warning(
                f"Found {br_data.type.value} "
                f"commits after merge-base with empty Jira ID: "
                f"{len(self.summary.commits_with_missing_jira_id[br_data.type])}"
            )
            LOG.debug(
                f"Found {br_data.type.value} "
                f"commits after merge-base with empty Jira ID: "
                f"{StringUtils2.list_to_multiline_string(self.summary.commits_with_missing_jira_id[br_data.type])}"
            )
        for br_data in branches:
            self.write_to_file_or_console(
                "commits missing jira id", br_data, self.summary.commits_with_missing_jira_id[br_data.type]
            )

    @staticmethod
    def _filter_relevant_unique_commits(
        commits: List[CommitData], commits_without_jira_id_filtered, common_jira_ids, common_commit_msgs
    ) -> List[CommitData]:
        result = []
        # 1. Values of commit list can contain commits without Jira ID
        # and we don't want to count them as unique commits unless the commit is a
        # special authored commit and it's not a common commit by its message
        # 2. If Jira ID is in common_jira_ids, it's not a unique commit, either.
        for commit in commits:
            special_unique_commit = (
                not commit.jira_id
                and commit.message in commits_without_jira_id_filtered
                and commit.message not in common_commit_msgs
            )
            normal_unique_commit = commit.jira_id is not None and commit.jira_id not in common_jira_ids
            if special_unique_commit or normal_unique_commit:
                result.append(commit)
        return result

    def write_to_file_or_console(self, output_type: str, branch: BranchData, commits: List[CommitData]):
        contents = StringUtils2.list_to_multiline_string([c.as_oneline_string() for c in commits])
        if self.conf.console_mode:
            LOG.info(f"Printing {output_type} for branch {branch.type.name}: {contents}")
        else:
            fn_prefix = Branches._convert_output_type_str_to_file_prefix(output_type)
            f = self._generate_filename(self.conf.output_dir, fn_prefix, branch.shortname)
            LOG.info(f"Saving {output_type} for branch {branch.type.name} to file: {f}")
            FileUtils.save_to_file(f, contents)

    def write_commit_list_to_file_or_console(self, output_type: str, commits: List[CommitData], add_sep_to_end=True):
        contents = StringUtils2.list_to_multiline_string([c.as_oneline_string() for c in commits])
        if self.conf.console_mode:
            LOG.info(f"Printing {output_type}: {contents}")
        else:
            fn_prefix = Branches._convert_output_type_str_to_file_prefix(output_type, add_sep_to_end=add_sep_to_end)
            f = self._generate_filename(self.conf.output_dir, fn_prefix)
            LOG.info(f"Saving {output_type} to file: {f}")
            FileUtils.save_to_file(f, contents)

    @staticmethod
    def _convert_output_type_str_to_file_prefix(output_type, add_sep_to_end=True):
        file_prefix: str = output_type.replace(" ", "-")
        if add_sep_to_end:
            file_prefix += "-"
        return file_prefix


class TableWithHeader:
    def __init__(self, header_title, table: str):
        self.header = (
            StringUtils.generate_header_line(
                header_title, char="═", length=len(StringUtils.get_first_line_of_multiline_str(table))
            )
            + "\n"
        )
        self.table = table

    def __str__(self):
        return self.header + self.table


# LATER TODOS
# TODO Handle multiple jira ids?? example: "CDPD-10052. HADOOP-16932"
# TODO Consider revert commits?
# TODO Add documentation
# TODO Check in logs: all results for "Jira ID is the same for commits, but commit message differs"


class BranchComparator:
    """"""

    def __init__(self, args, downstream_repo, output_dir: str):
        self.repo = downstream_repo
        self.config = BranchComparatorConfig(output_dir, args)
        self.branches: Branches = Branches(
            self.config, self.repo, {BranchType.FEATURE: args.feature_branch, BranchType.MASTER: args.master_branch}
        )

    def run(self):
        LOG.info(
            "Starting Branch comparator... \n "
            f"Output dir: {self.config.output_dir}\n"
            f"Master branch: {self.branches.get_branch(BranchType.MASTER).name}\n "
            f"Feature branch: {self.branches.get_branch(BranchType.FEATURE).name}\n "
            f"Commit author exceptions: {self.config.commit_author_exceptions}\n "
            f"Console mode: {self.config.console_mode}\n "
        )
        self.validate_branches()
        # TODO DO NOT FETCH FOR NOW, Uncomment if finished with testing
        # self.repo.fetch(all=True)
        print_stats = self.config.console_mode
        save_to_file = not self.config.console_mode
        self.compare(print_stats=print_stats, save_to_file=save_to_file)
        self._run_legacy_git_compare_script()
        # Finally, print summary
        self.print_and_save_summary()

    def _run_legacy_git_compare_script(self):
        script_results: Dict[BranchType, Tuple[str, str]] = self.execute_git_compare_script(
            self.config.git_compare_script
        )
        unique_jira_ids_per_branch: Dict[BranchType, List[str]] = {}
        for br_type in BranchType:
            unique_jira_ids_per_branch[br_type] = self._get_compare_script_unique_jira_ids_for_branch(
                script_results, self.branches.get_branch(br_type)
            )
            self.branches.summary.unique_jira_ids_legacy_script[br_type] = unique_jira_ids_per_branch[br_type]
            LOG.debug(
                f"[LEGACY SCRIPT] Unique commit results for {br_type.value}: {unique_jira_ids_per_branch[br_type]}"
            )
        # Cross check unique jira ids with previous results
        for br_type in BranchType:
            branch_data = self.branches.get_branch(br_type)
            unique_jira_ids = [c.jira_id for c in self.branches.summary.unique_commits[br_type]]
            LOG.info(f"[CURRENT SCRIPT] Found {len(unique_jira_ids)} unique commits on {br_type} '{branch_data.name}'")
            LOG.debug(f"[CURRENT SCRIPT] Found unique commits on {br_type} '{branch_data.name}': {unique_jira_ids} ")

    @staticmethod
    def _get_compare_script_unique_jira_ids_for_branch(
        script_results: Dict[BranchType, Tuple[str, str]], branch_data: BranchData
    ):
        branch_type = branch_data.type
        res_tuple = script_results[branch_type]
        LOG.info(f"CLI Command for {branch_type} was: {res_tuple[0]}")
        LOG.info(f"Output of command for {branch_type} was: {res_tuple[1]}")
        lines = res_tuple[1].splitlines()
        unique_jira_ids = [line.split(" ")[0] for line in lines]
        LOG.info(f"[LEGACY SCRIPT] Found {len(unique_jira_ids)} unique commits on {branch_type} '{branch_data.name}'")
        LOG.debug(f"[LEGACY SCRIPT] Found unique commits on {branch_type} '{branch_data.name}': {unique_jira_ids}")
        return unique_jira_ids

    def validate_branches(self):
        both_exist = self.branches.validate(BranchType.FEATURE)
        both_exist &= self.branches.validate(BranchType.MASTER)
        if not both_exist:
            raise ValueError("Both feature and master branch should be an existing branch. Exiting...")

    def compare(self, print_stats=True, save_to_file=True):
        self.branches.execute_git_log(print_stats=print_stats, save_to_file=save_to_file)
        self.branches.compare(self.config.commit_author_exceptions)

    def print_and_save_summary(self):
        printable_summary_str, writable_summary_str = BranchComparator.render_summary_string(self.branches.summary)
        LOG.info(printable_summary_str)
        filename = FileUtils.join_path(self.config.output_dir, "summary.txt")
        LOG.info(f"Saving summary to file: {filename}")
        FileUtils.save_to_file(filename, writable_summary_str)

    @staticmethod
    def render_summary_string(summary_data: SummaryData):
        # Generate tables first, in order to know the length of the header rows
        result_files_table = TableWithHeader(
            "RESULT FILES",
            ResultPrinter.print_table(
                sorted(FileUtils.find_files(summary_data.output_dir, regex=".*", full_path_result=True)),
                lambda file: (file, len(FileUtils.read_file(file).splitlines())),
                header=["Row", "File", "# of lines"],
                print_result=False,
                max_width=200,
                max_width_separator=os.sep,
            ),
        )

        unique_commit_tables = []
        for br_type, br_data in summary_data.branch_data.items():
            unique_commit_tables.append(
                TableWithHeader(
                    f"UNIQUE ON BRANCH {br_data.name}",
                    ResultPrinter.print_table(
                        summary_data.unique_commits[br_type],
                        lambda commit: (commit.jira_id, commit.message, commit.date),
                        header=["Row", "Jira ID", "Commit message", "Commit date"],
                        print_result=False,
                        max_width=80,
                        max_width_separator=" ",
                    ),
                )
            )

        common_commits_table = TableWithHeader(
            "COMMON COMMITS SINCE BRANCHES DIVERGED",
            ResultPrinter.print_table(
                summary_data.common_commits,
                lambda commit: (commit.jira_id, commit.message, commit.date),
                header=["Row", "Jira ID", "Commit message", "Commit date"],
                print_result=False,
                max_width=80,
                max_width_separator=" ",
            ),
        )

        header = ["Row", "Jira ID", "Commit message", "Commit date"]
        header.extend(summary_data.get_branch_names())
        colorized_table, normal_table = BranchComparator.create_all_commits_tables(
            header, summary_data.all_commits_presence_matrix
        )

        # Generate summary string
        summary_str_common = "\n\n" + (
            StringUtils.generate_header_line(
                "SUMMARY", char="═", length=len(StringUtils.get_first_line_of_multiline_str(common_commits_table.table))
            )
            + "\n"
        )
        summary_str_common += str(summary_data)
        summary_str_common += "\n\n"

        printable_tables = [result_files_table] + unique_commit_tables + [common_commits_table, colorized_table]
        writable_tables = [result_files_table] + unique_commit_tables + [common_commits_table, normal_table]
        return BranchComparator.generate_summary_msgs(printable_tables, writable_tables, summary_str_common)

    @staticmethod
    def generate_summary_msgs(
        printable_tables: List[TableWithHeader], writable_tables: List[TableWithHeader], summary_str_common: str
    ):
        printable_summary_str: str = summary_str_common
        writable_summary_str: str = summary_str_common
        for table in printable_tables:
            printable_summary_str += str(table)
            printable_summary_str += "\n\n"

        for table in writable_tables:
            writable_summary_str += str(table)
            writable_summary_str += "\n\n"
        return printable_summary_str, writable_summary_str

    @staticmethod
    def create_all_commits_tables(header, all_commits: List[List]):
        # Adding 1 because row id will be added as first column
        row_len = len(all_commits[0]) + 1
        color_conf = ColorizeConfig(
            [
                ColorDescriptor(bool, True, Color.GREEN, MatchType.ALL, (0, row_len), (0, row_len)),
                ColorDescriptor(bool, False, Color.RED, MatchType.ANY, (0, row_len), (0, row_len)),
            ],
            eval_method=EvaluationMethod.ALL,
        )
        colorized_table = BranchComparator._create_all_comits_table(header, all_commits, colorize_config=color_conf)
        normal_table = BranchComparator._create_all_comits_table(header, all_commits, colorize_config=False)
        return colorized_table, normal_table

    @staticmethod
    def _create_all_comits_table(header, all_commits, colorize_config=None):
        table = TableWithHeader(
            "ALL COMMITS (MERGED LIST)",
            ResultPrinter.print_table(
                all_commits,
                lambda row: row,
                header=header,
                print_result=False,
                max_width=100,
                max_width_separator=" ",
                bool_conversion_config=BoolConversionConfig(),
                colorize_config=colorize_config,
            ),
        )
        return table

    def execute_git_compare_script(self, script) -> Dict[BranchType, Tuple[str, str]]:
        working_dir = self.repo.repo_path
        master_br_name = self.branches.get_branch(BranchType.MASTER).shortname
        feature_br_name = self.branches.get_branch(BranchType.FEATURE).shortname
        output_dir = FileUtils.join_path(self.config.output_dir, "git_compare_script_output")
        FileUtils.ensure_dir_created(output_dir)

        results: Dict[BranchType, Tuple[str, str]] = {}
        args1 = f"{feature_br_name} {master_br_name}"
        output_file1 = FileUtils.join_path(output_dir, f"only-on-{master_br_name}")
        cli_cmd, cli_output = CommandRunner.execute_script(
            script, args=args1, working_dir=working_dir, output_file=output_file1, use_tee=True
        )
        results[BranchType.MASTER] = (cli_cmd, cli_output)

        args2 = f"{master_br_name} {feature_br_name}"
        output_file2 = FileUtils.join_path(output_dir, f"only-on-{feature_br_name}")
        cli_cmd, cli_output = CommandRunner.execute_script(
            script, args=args2, working_dir=working_dir, output_file=output_file2, use_tee=True
        )
        results[BranchType.FEATURE] = (cli_cmd, cli_output)
        return results
