import logging
import os
from enum import Enum
from typing import Dict, List, Tuple
from colr import color
from pythoncommons.file_utils import FileUtils
from commands.upstream_jira_umbrella_fetcher import CommitData
from constants import ANY_JIRA_ID_PATTERN
from git_wrapper import GitWrapper
from yarndevfunc.utils import StringUtils, ResultPrinter

LOG = logging.getLogger(__name__)


class BranchType(Enum):
    FEATURE = "feature branch"
    MASTER = "master branch"


class BranchData:
    def __init__(self, type: BranchType, branch_name: str):
        self.type: BranchType = type
        self.name: str = branch_name

        # Set later
        self.gitlog_results: List[str] = []
        # Commit objects in reverse order (from oldest to newest)
        self.commit_objs: List[
            CommitData
        ] = []  # commits stored in a list, in order from last to first commit (descending)
        self.hash_to_index: Dict[str, int] = {}  # Dict: commit hash to commit index
        self.hash_to_commit: Dict[str, str] = {}  # Dict: commit hash to CommitData object
        self.jira_id_to_commit: Dict[str, CommitData] = {}  # Dict: Jira ID (e.g. YARN-1234) to CommitData object
        self.unique_commits: List[CommitData] = []
        self.merge_base_idx: int = -1

    @property
    def number_of_commits(self):
        return len(self.gitlog_results)

    @property
    def commits_before_merge_base(self) -> List[CommitData]:
        return self.commit_objs[: self.merge_base_idx]

    @property
    def commits_after_merge_base(self) -> List[CommitData]:
        return self.commit_objs[self.merge_base_idx :]

    def set_merge_base(self, merge_base_hash: str):
        # TODO if hash not found throw exception
        self.merge_base_idx = self.hash_to_index[merge_base_hash]


# TODO
class SummaryData(object):
    pass


class Branches:
    def __init__(self, basedir: str, repo: GitWrapper, branch_dict: dict):
        self.basedir = basedir
        self.branch_data: Dict[BranchType, BranchData] = {}
        self.repo = repo
        for br_type in BranchType:
            branch_name = branch_dict[br_type]
            self.branch_data[br_type] = BranchData(br_type, branch_name)

        # Set later
        self.merge_base: str = ""
        self.summary_data = SummaryData()
        self.common_commits: List[CommitData] = []

    def get_branch(self, br_type: BranchType) -> BranchData:
        return self.branch_data[br_type]

    @staticmethod
    def _generate_filename(basedir, prefix, branch_name) -> str:
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
            branch.gitlog_results = self.repo.log(branch.name, oneline_with_date=True)
            # Store commit objects in reverse order (ascending by date)
            branch.commit_objs = list(
                reversed(
                    [
                        CommitData.from_git_log_str(
                            commit_str, pattern=ANY_JIRA_ID_PATTERN, allow_unmatched_jira_id=True
                        )
                        for commit_str in branch.gitlog_results
                    ]
                )
            )

            for idx, commit in enumerate(branch.commit_objs):
                branch.hash_to_commit[commit.hash] = commit
                branch.hash_to_index[commit.hash] = idx
                branch.jira_id_to_commit[commit.jira_id] = commit
        # This must be executed after branch.hash_to_index is set
        self.get_merge_base()

        if print_stats:
            self._print_stats()
        if save_to_file:
            self._save_git_log_to_file()

    def _print_stats(self):
        for br_type in BranchType:
            branch: BranchData = self.branch_data[br_type]
            LOG.info(f"Found {branch.number_of_commits} commits on feature branch: {branch.name}")

    def _save_git_log_to_file(self):
        for br_type in BranchType:
            branch: BranchData = self.branch_data[br_type]
            # We would like to maintain descending order of commits in printouts
            self.write_to_file("git log output", branch, list(reversed(branch.commit_objs)))

    def _save_commits_before_after_merge_base_to_file(self):
        for br_type in BranchType:
            branch: BranchData = self.branch_data[br_type]
            self.write_to_file("before merge base commits", branch, branch.commits_before_merge_base)
            self.write_to_file("before after base commits", branch, branch.commits_after_merge_base)

    def get_merge_base(self):
        merge_base = self.repo.merge_base(
            self.branch_data[BranchType.FEATURE].name, self.branch_data[BranchType.MASTER].name
        )
        if len(merge_base) > 1:
            raise ValueError(f"Ambiguous merge base: {merge_base}.")
        self.merge_base = merge_base[0]
        LOG.info(f"Merge base of branches: {self.merge_base}")
        for br_type in BranchType:
            branch: BranchData = self.branch_data[br_type]
            branch.set_merge_base(self.merge_base.hexsha)

    def compare(self):
        self._save_commits_before_after_merge_base_to_file()
        feature_br: BranchData = self.branch_data[BranchType.FEATURE]
        master_br: BranchData = self.branch_data[BranchType.MASTER]

        self._sanity_check_commits_before_merge_base(feature_br, master_br)
        self._check_after_merge_base_commits(feature_br, master_br)

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
        LOG.info(
            f"Detected {len(master_br.commits_before_merge_base)} common commits between "
            f"'{feature_br.name}' and '{master_br.name}'"
        )

    def _check_after_merge_base_commits(self, feature_br: BranchData, master_br: BranchData):
        # List of tuples. First item: Master branch commit obj, second item: feature branch commit obj
        self.common_commits: List[Tuple[CommitData, CommitData]] = []
        common_but_commit_msg_differs: List[Tuple[CommitData, CommitData]] = []

        for master_commit in master_br.commits_after_merge_base:
            if master_commit.jira_id in feature_br.jira_id_to_commit:
                feature_commit = feature_br.jira_id_to_commit[master_commit.jira_id]
                LOG.debug(
                    "Found same commit on both branches (by Jira ID)."
                    f"Master branch commit: {master_commit.as_oneline_string()}"
                    f"Feature branch commit: {feature_commit.as_oneline_string()}"
                )

                if master_commit.message != feature_commit.message:
                    # TODO Write these interesting commits to separate file
                    LOG.warning(
                        "Jira ID is the same for commits, but commit message differs: "
                        f"Master branch commit: {master_commit.as_oneline_string()}"
                        f"Feature branch commit: {feature_commit.as_oneline_string()}"
                    )
                    common_but_commit_msg_differs.append((master_commit, feature_commit))

                # In each case, count it as common commit if Jira ID matches
                self.common_commits.append((master_commit, feature_commit))

        common_jira_ids = set([cc[0].jira_id for cc in self.common_commits])
        master_br.unique_commits = list(
            filter(lambda x: x.jira_id not in common_jira_ids, master_br.commits_after_merge_base)
        )
        feature_br.unique_commits = list(
            filter(lambda x: x.jira_id not in common_jira_ids, feature_br.commits_after_merge_base)
        )
        LOG.info(f"Identified {len(master_br.unique_commits)} unique commits on branch: {master_br.name}")
        LOG.info(f"Identified {len(feature_br.unique_commits)} unique commits on branch: {feature_br.name}")
        self.write_to_file("unique commits", master_br, master_br.unique_commits)
        self.write_to_file("unique commits", feature_br, feature_br.unique_commits)

    def write_to_file(self, output_type: str, branch: BranchData, commits: List[CommitData]):
        file_prefix: str = output_type.replace(" ", "-") + "-"
        f = self._generate_filename(self.basedir, file_prefix, branch.name)
        LOG.info(f"Saving {output_type} for branch {branch.type.name} to file: {f}")
        FileUtils.save_to_file(f, StringUtils.list_to_multiline_string([c.as_oneline_string() for c in commits]))


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


class BranchComparator:
    # TODO Add documentation
    """"""

    def __init__(self, args, downstream_repo, output_dir):
        self.repo = downstream_repo
        self.branches: Branches = Branches(
            output_dir, self.repo, {BranchType.FEATURE: args.feature_branch, BranchType.MASTER: args.master_branch}
        )
        self.output_dir = output_dir

    def run(self, args):
        LOG.info(
            "Starting Branch comparator... \n "
            f"Output dir: {self.output_dir}\n"
            f"Master branch: {args.master_branch}\n "
            f"Feature branch: {args.feature_branch}\n "
        )
        self.validate_branches()
        # TODO DO NOT FETCH FOR NOW, Uncomment if finished with testing
        # self.repo.fetch(all=True)
        self.compare()

    def validate_branches(self):
        both_exist = self.branches.validate(BranchType.FEATURE)
        both_exist &= self.branches.validate(BranchType.MASTER)
        if not both_exist:
            raise ValueError("Both feature and master branch should be an existing branch. Exiting...")

    def compare(self):
        self.branches.execute_git_log(print_stats=True, save_to_file=True)
        self.branches.compare()

        # Print and save summary
        summary_string = self.render_summary_string()
        LOG.info(summary_string)
        filename = FileUtils.join_path(self.output_dir, "summary.txt")
        LOG.info(f"Saving summary to file: {filename}")
        FileUtils.save_to_file(filename, summary_string)

        # TODO 1. Write fancy table to console with unique commits (DO NOT INCLUDE COMMON COMMITS)
        # TODO 2. Stdout mode: Instead of writing to individual files, write everything to console --> Useful for CDSW runs!
        # TODO 3. Run git_compare.sh and store results + diff git_compare.sh results with my script result, report if different!
        # TODO 4. Handle revert commits?

    def render_summary_string(self):
        # Generate tables first, in order to know the length of the header rows

        result_files_table = TableWithHeader(
            "RESULT FILES",
            ResultPrinter.print_table(
                FileUtils.find_files(self.output_dir, regex=".*", full_path_result=True),
                lambda file: (file,),
                header=["Row", "File"],
                print_result=False,
                max_width=80,
                max_width_separator=os.sep,
            ),
        )

        master_br = self.branches.get_branch(BranchType.MASTER)
        feature_br = self.branches.get_branch(BranchType.FEATURE)
        uniq_master_commits_table = TableWithHeader(
            f"UNIQUE ON BRANCH {master_br.name}",
            ResultPrinter.print_table(
                master_br.unique_commits,
                lambda commit: (commit.jira_id, commit.message, commit.date),
                header=["Row", "Jira ID", "Commit message", "Commit date"],
                print_result=False,
                max_width=80,
                max_width_separator=" ",
            ),
        )
        uniq_feature_commits_table = TableWithHeader(
            f"UNIQUE ON BRANCH {feature_br.name}",
            ResultPrinter.print_table(
                feature_br.unique_commits,
                lambda commit: (commit.jira_id, commit.message, commit.date),
                header=["Row", "Jira ID", "Commit message", "Commit date"],
                print_result=False,
                max_width=80,
                max_width_separator=" ",
            ),
        )

        common_commits = [c[0] for c in self.branches.common_commits]
        common_commits_table = TableWithHeader(
            "COMMON COMMITS SINCE BRANCHES DIVERGED",
            ResultPrinter.print_table(
                common_commits,
                lambda commit: (commit.jira_id, commit.message, commit.date),
                header=["Row", "Jira ID", "Commit message", "Commit date"],
                print_result=False,
                max_width=80,
                max_width_separator=" ",
            ),
        )
        all_commits_list: List[CommitData] = [] + master_br.unique_commits + feature_br.unique_commits + common_commits
        all_commits_list.sort(key=lambda c: c.date, reverse=True)

        all_commits_rows = []
        for commit in all_commits_list:
            jira_id = commit.jira_id
            present_on_branches = []
            if jira_id in master_br.jira_id_to_commit and jira_id in feature_br.jira_id_to_commit:
                present_on_branches = [True, True]
            elif jira_id in master_br.jira_id_to_commit:
                present_on_branches = [True, False]
            elif jira_id in feature_br.jira_id_to_commit:
                present_on_branches = [False, True]

            curr_row = [jira_id, commit.message]
            curr_row.extend(present_on_branches)
            curr_row = self.colorize_row(curr_row, convert_bools=True)
            all_commits_rows.append(curr_row)

        header = ["Row", "Jira ID", "Commit message"]
        header.extend([master_br.name, feature_br.name])
        all_commits_table = TableWithHeader(
            "ALL COMMITS (MERGED LIST)",
            ResultPrinter.print_table(
                all_commits_rows,
                lambda row: row,
                header=header,
                print_result=False,
                max_width=50,
                max_width_separator=" ",
            ),
        )

        # Generate summary string
        summary_str = (
            StringUtils.generate_header_line(
                "SUMMARY", char="═", length=len(StringUtils.get_first_line_of_multiline_str(common_commits_table.table))
            )
            + "\n"
        )

        # TODO print self.summary_data
        # summary_str += f"Number of jiras: {self.no_of_jiras}\n"
        # summary_str += f"Number of commits: {self.no_of_commits}\n"
        # summary_str += f"Number of files changed: {self.no_of_files}\n"
        summary_str += result_files_table
        summary_str += "\n\n"
        summary_str += uniq_feature_commits_table
        summary_str += "\n\n"
        summary_str += uniq_master_commits_table
        summary_str += "\n\n"
        summary_str += common_commits_table
        summary_str += "\n\n"
        summary_str += all_commits_table
        summary_str += "\n\n"
        return summary_str

    # TODO code is duplicated - Copied from upstream_jira_umbrella_fetcher.py
    @staticmethod
    def colorize_row(curr_row, convert_bools=False):
        res = []
        missing_backport = False
        if not all(curr_row[1:]):
            missing_backport = True

        # Mark first cell with red if any of the backports are missing
        # Mark first cell with green if all backports are present
        # Mark any bool cell with green if True, red if False
        for idx, cell in enumerate(curr_row):
            if (isinstance(cell, bool) and cell) or not missing_backport:
                if convert_bools and isinstance(cell, bool):
                    cell = "X" if cell else "-"
                res.append(color(cell, fore="green"))
            else:
                if convert_bools and isinstance(cell, bool):
                    cell = "X" if cell else "-"
                res.append(color(cell, fore="red"))
        return res
