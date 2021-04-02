import logging
import os
import sys

from pythoncommons.file_utils import FileUtils
from pythoncommons.jira_utils import JiraUtils
from pythoncommons.pickle_utils import PickleUtils
from pythoncommons.string_utils import StringUtils, auto_str

from yarndevfunc.command_runner import CommandRunner
from yarndevfunc.constants import (
    HEAD,
    COMMIT_FIELD_SEPARATOR,
    REVERT,
    SHORT_SHA_LENGTH,
    ORIGIN,
    ORIGIN_TRUNK,
    YARN_JIRA_ID_PATTERN,
)
from yarndevfunc.utils import ResultPrinter
from enum import Enum
from colr import color

LOG = logging.getLogger(__name__)
PICKLED_DATA_FILENAME = "pickled_umbrella_data.obj"


class ExecutionMode(Enum):
    AUTO_BRANCH_MODE = "auto_branch_mode"
    MANUAL_BRANCH_MODE = "manual_branch_mode"


@auto_str
class JiraUmbrellaData:
    def __init__(self):
        self.subjira_ids = []
        self.jira_ids_and_titles = {}
        self.jira_html = None
        self.piped_jira_ids = None
        self.matched_upstream_commit_list = None
        self.matched_upstream_commit_hashes = None
        self.list_of_changed_files = None
        self.upstream_commit_data_list = None
        self.execution_mode = None
        self.downstream_branches = None
        self.backported_jiras = dict()

    @property
    def no_of_matched_commits(self):
        return len(self.matched_upstream_commit_list)

    @property
    def no_of_jiras(self):
        return len(self.subjira_ids)

    @property
    def no_of_commits(self):
        return len(self.matched_upstream_commit_hashes)

    @property
    def no_of_files(self):
        return len(self.list_of_changed_files)

    # TODO Separate this representation code from data logic
    # TODO Figure out a way to decrease code duplication in this method
    def render_summary_string(self, result_basedir, extended_backport_table=False, backport_remote_filter=ORIGIN):
        # Generate tables first, in order to know the length of the header rows
        commit_list_table = ResultPrinter.print_table(
            self.upstream_commit_data_list,
            lambda commit: (commit.jira_id, commit.message, commit.date),
            header=["Row", "Jira ID", "Commit message", "Commit date"],
            print_result=False,
            max_width=80,
            max_width_separator=" ",
        )

        files = FileUtils.find_files(result_basedir, regex=".*", full_path_result=True)
        file_list_table = ResultPrinter.print_table(
            files,
            lambda file: (file,),
            header=["Row", "File"],
            print_result=False,
            max_width=80,
            max_width_separator=os.sep,
        )

        if extended_backport_table:
            backports_list = []
            for bjira in self.backported_jiras.values():
                for commit in bjira.commits:
                    backports_list.append(
                        [
                            bjira.jira_id,
                            commit.commit_obj.hash[:SHORT_SHA_LENGTH],
                            commit.commit_obj.message,
                            self.filter_branches(backport_remote_filter, commit.branches),
                            commit.commit_obj.date,
                        ]
                    )
            backport_table = ResultPrinter.print_table(
                backports_list,
                lambda row: row,
                header=["Row", "Jira ID", "Hash", "Commit message", "Branches", "Date"],
                print_result=False,
                max_width=50,
                max_width_separator=" ",
            )
        else:
            if self.execution_mode == ExecutionMode.AUTO_BRANCH_MODE:
                backports_list = []
                for bjira in self.backported_jiras.values():
                    all_branches = []
                    for commit in bjira.commits:
                        if commit.commit_obj.reverted:
                            continue
                        branches = self.filter_branches(backport_remote_filter, commit.branches)
                        if branches:
                            all_branches.extend(branches)
                    backports_list.append([bjira.jira_id, list(set(all_branches))])
                backport_table = ResultPrinter.print_table(
                    backports_list,
                    lambda row: row,
                    header=["Row", "Jira ID", "Branches"],
                    print_result=False,
                    max_width=50,
                    max_width_separator=" ",
                )
            elif self.execution_mode == ExecutionMode.MANUAL_BRANCH_MODE:
                backports_list = []
                for bjira in self.backported_jiras.values():
                    all_branches = set([br for c in bjira.commits for br in c.branches])
                    for commit in bjira.commits:
                        if commit.commit_obj.reverted:
                            continue
                    backport_present_list = []
                    for branch in self.downstream_branches:
                        backport_present_list.append(branch in all_branches)
                    curr_row = [bjira.jira_id]
                    curr_row.extend(backport_present_list)
                    curr_row = self.colorize_row(curr_row, convert_bools=True)
                    backports_list.append(curr_row)

                header = ["Row", "Jira ID"]
                header.extend(self.downstream_branches)
                backport_table = ResultPrinter.print_table(
                    backports_list,
                    lambda row: row,
                    header=header,
                    print_result=False,
                    max_width=50,
                    max_width_separator=" ",
                )

        # Create headers
        commits_header_line = (
            StringUtils.generate_header_line(
                "COMMITS", char="═", length=len(StringUtils.get_first_line_of_multiline_str(commit_list_table))
            )
            + "\n"
        )

        result_files_header_line = (
            StringUtils.generate_header_line(
                "RESULT FILES", char="═", length=len(StringUtils.get_first_line_of_multiline_str(file_list_table))
            )
            + "\n"
        )

        backport_header_line = (
            StringUtils.generate_header_line(
                "BACKPORTED JIRAS", char="═", length=len(StringUtils.get_first_line_of_multiline_str(backport_table))
            )
            + "\n"
        )

        # Generate summary string
        summary_str = (
            StringUtils.generate_header_line(
                "SUMMARY", char="═", length=len(StringUtils.get_first_line_of_multiline_str(commit_list_table))
            )
            + "\n"
        )
        summary_str += f"Number of jiras: {self.no_of_jiras}\n"
        summary_str += f"Number of commits: {self.no_of_commits}\n"
        summary_str += f"Number of files changed: {self.no_of_files}\n"
        summary_str += commits_header_line
        summary_str += commit_list_table
        summary_str += "\n\n"
        summary_str += result_files_header_line
        summary_str += file_list_table
        summary_str += "\n\n"
        summary_str += backport_header_line
        summary_str += backport_table
        return summary_str

    # TODO X / - characters should be parameters
    def colorize_row(self, curr_row, convert_bools=False):
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

    @staticmethod
    def filter_branches(backport_remote_filter, branches):
        if backport_remote_filter and any(backport_remote_filter in br for br in branches):
            res_branches = list(filter(lambda br: backport_remote_filter in br, branches))
        else:
            res_branches = branches
        return res_branches


# TODO move this to common module as it is used by BranchCompataror as well
@auto_str
class CommitData:
    def __init__(self, c_hash, jira_id, message, date, branches=None, reverted=False, author=None):
        self.hash = c_hash
        self.jira_id = jira_id
        self.message = message
        self.date = date
        self.branches = branches
        self.reverted = reverted
        self.author = author

    @staticmethod
    def from_git_log_str(
        git_log_str, format: str = None, pattern=YARN_JIRA_ID_PATTERN, allow_unmatched_jira_id=False, author=None
    ):
        """
        1. Commit hash: It is in the first column.
        2. Jira ID: Expecting the Jira ID to be the first segment of commit message, so this is the second column.
        3. Commit message: From first to (last - 1) th index
        4. Authored date (commit date): The very last segment is the commit date.
        :param git_log_str:
        :return:
        """
        # TODO Make an enum for format strings: 'format'
        if not format:
            format = "oneline_with_date"
        comps = git_log_str.split(COMMIT_FIELD_SEPARATOR)
        match = pattern.search(git_log_str)

        jira_id = None
        if not match:
            if not allow_unmatched_jira_id:
                raise ValueError(
                    f"Cannot find YARN jira id in git log string: {git_log_str}. "
                    f"Pattern was: {CommitData.JIRA_ID_PATTERN.pattern}"
                )
        else:
            jira_id = match.group(1)

        revert_count = git_log_str.upper().count(REVERT.upper())
        reverted = False
        if revert_count % 2 == 1:
            reverted = True

        # Alternatively, commit date and author may be gathered with git show,
        # but this requires more CLI calls, so it's not the preferred way.
        # commit_date = self.upstream_repo.show(commit_hash, no_patch=True, no_notes=True, pretty='%cI')
        # commit_author = self.upstream_repo.show(commit_hash, suppress_diff=True, format="%ae"))

        c_hash = comps[0]
        if format == "oneline_with_date":
            # Example: 'ceab00b0db84455da145e0545fe9be63b270b315 COMPX-3264. Fix QueueMetrics#containerAskToCount map synchronization issues 2021-03-22T02:18:52-07:00'
            message = COMMIT_FIELD_SEPARATOR.join(comps[1:-1])
            date = comps[-1]
        elif format == "oneline_with_date_and_author":
            # Example: 'ceab00b0db84455da145e0545fe9be63b270b315 COMPX-3264. Fix QueueMetrics#containerAskToCount map synchronization issues 2021-03-22T02:18:52-07:00 snemeth@cloudera.com'
            message = COMMIT_FIELD_SEPARATOR.join(comps[1:-2])
            date = comps[-2]
            author = comps[-1]
        else:
            raise ValueError(f"Unrecognized format string: {format}")
        return CommitData(c_hash=c_hash, jira_id=jira_id, message=message, date=date, reverted=reverted, author=author)

    def as_oneline_string(self) -> str:
        return f"{self.hash} {self.message}"


@auto_str
class BackportedJira:
    def __init__(self, jira_id, commits):
        self.jira_id = jira_id
        self.commits = commits


@auto_str
class BackportedCommit:
    def __init__(self, commit_obj, branches):
        self.commit_obj = commit_obj
        self.branches = branches


# TODO Add documentation
class UpstreamJiraUmbrellaFetcher:
    def __init__(self, args, upstream_repo, downstream_repo, basedir, upstream_base_branch):
        self.execution_mode = (
            ExecutionMode.MANUAL_BRANCH_MODE
            if hasattr(args, "branches") and args.branches
            else ExecutionMode.AUTO_BRANCH_MODE
        )
        self.downstream_branches = args.branches if hasattr(args, "branches") else []
        self.jira_id = args.jira_id
        self.upstream_repo = upstream_repo
        self.downstream_repo = downstream_repo
        self.basedir = basedir
        self.upstream_base_branch = upstream_base_branch
        self.force_mode = True if args.force_mode else False
        # These fields will be assigned when data is fetched
        self.data: JiraUmbrellaData = None
        self.result_basedir = None
        self.jira_html_file = None
        self.jira_list_file = None
        self.commits_file = None
        self.changed_files_file = None
        self.summary_file = None
        self.intermediate_results_file = None
        self.pickled_data_file = None

    def run(self):
        LOG.info(
            "Starting umbrella jira fetcher... \n "
            "Upstream Jira: %s\n "
            "Upstream repo: %s\n "
            "Downstream repo: %s\n "
            "Execution mode: %s\n"
            "Downstream branches to check: %s",
            self.jira_id,
            self.upstream_repo.repo_path,
            self.downstream_repo.repo_path,
            self.execution_mode.name,
            ", ".join(self.downstream_branches),
        )

        if self.execution_mode == ExecutionMode.MANUAL_BRANCH_MODE:
            if not self.downstream_branches:
                raise ValueError("Execution mode is 'manual-branch' but no branch was provided. Exiting...")

            LOG.info("Manual branch execution mode, validating provided branches..")
            for branch in self.downstream_branches:
                if not self.downstream_repo.is_branch_exist(branch):
                    raise ValueError(
                        "Cannot find branch called '{}' in downstream repository {}. "
                        "Please verify the provided branch names!"
                    )

        self.log_current_branch()
        self.set_file_fields()
        self.upstream_repo.fetch(all=True)
        self.downstream_repo.fetch(all=True)
        if self.force_mode:
            LOG.info("FORCE MODE is on")
            self.do_fetch()
        else:
            loaded = self.load_pickled_umbrella_data()
            if not loaded:
                self.do_fetch()
            else:
                LOG.info("Loaded pickled data from: %s", self.pickled_data_file)
                self.print_summary()

    def do_fetch(self):
        LOG.info("Fetching jira umbrella data...")
        self.data = JiraUmbrellaData()
        self.fetch_jira_ids()
        self.find_upstream_commits_and_save_to_file()
        if self.execution_mode == ExecutionMode.AUTO_BRANCH_MODE:
            self.find_downstream_commits_auto_mode()
        elif self.execution_mode == ExecutionMode.MANUAL_BRANCH_MODE:
            self.find_downstream_commits_manual_mode()
        self.data.execution_mode = self.execution_mode
        self.data.downstream_branches = self.downstream_branches
        self.save_changed_files_to_file()
        # TODO Only render summary once, store and print later (print_summary)
        self.write_summary_file()
        self.write_all_changes_files()
        self.pickle_umbrella_data()
        self.print_summary()

    def load_pickled_umbrella_data(self):
        LOG.info("Trying to load pickled data from file: %s", self.pickled_data_file)
        if FileUtils.does_file_exist(self.pickled_data_file):
            self.data = PickleUtils.load(self.pickled_data_file)
            return True
        else:
            LOG.info("Pickled umbrella data file not found under path: %s", self.pickled_data_file)
            return False

    def log_current_branch(self):
        curr_branch = self.upstream_repo.get_current_branch_name()
        LOG.info("Current branch: %s", curr_branch)
        if curr_branch != self.upstream_base_branch:
            raise ValueError(f"Current branch is not {self.upstream_base_branch}. Exiting!")

    def set_file_fields(self):
        self.result_basedir = FileUtils.join_path(self.basedir, self.jira_id)
        self.jira_html_file = FileUtils.join_path(self.result_basedir, "jira.html")
        self.jira_list_file = FileUtils.join_path(self.result_basedir, "jira-list.txt")
        self.commits_file = FileUtils.join_path(self.result_basedir, "commit-hashes.txt")
        self.changed_files_file = FileUtils.join_path(self.result_basedir, "changed-files.txt")
        self.summary_file = FileUtils.join_path(self.result_basedir, "summary.txt")
        self.intermediate_results_file = FileUtils.join_path(self.result_basedir, "intermediate-results.txt")
        self.pickled_data_file = FileUtils.join_path(self.result_basedir, PICKLED_DATA_FILENAME)

    def fetch_jira_ids(self):
        LOG.info("Fetching HTML of jira: %s", self.jira_id)
        self.data.jira_html = JiraUtils.download_jira_html(
            "https://issues.apache.org/jira/browse/", self.jira_id, self.jira_html_file
        )
        self.data.jira_ids_and_titles = JiraUtils.parse_subjiras_and_jira_titles_from_umbrella_html(
            self.data.jira_html, self.jira_list_file, filter_ids=[self.jira_id]
        )
        self.data.subjira_ids = list(self.data.jira_ids_and_titles.keys())
        if not self.data.subjira_ids:
            raise ValueError(f"Cannot find subjiras for jira with id: {self.jira_id}")
        LOG.info("Found %d subjiras: %s", len(self.data.subjira_ids), self.data.subjira_ids)
        self.data.piped_jira_ids = "|".join(self.data.subjira_ids)

    def find_upstream_commits_and_save_to_file(self):
        # It's quite complex to grep for multiple jira IDs with gitpython, so let's rather call an external command
        git_log_result = self.upstream_repo.log(ORIGIN_TRUNK, oneline_with_date=True)
        output = CommandRunner.egrep_with_cli(git_log_result, self.intermediate_results_file, self.data.piped_jira_ids)
        normal_commit_lines = output.split("\n")
        modified_log_lines = self._find_missing_upstream_commits_by_message(git_log_result, normal_commit_lines)
        self.data.matched_upstream_commit_list = normal_commit_lines + modified_log_lines
        if not self.data.matched_upstream_commit_list:
            raise ValueError(f"Cannot find any commits for jira: {self.jira_id}")

        LOG.info("Number of matched commits: %s", self.data.no_of_matched_commits)
        LOG.debug("Matched commits: \n%s", StringUtils.list_to_multiline_string(self.data.matched_upstream_commit_list))

        # Commits in reverse order (oldest first)
        self.data.matched_upstream_commit_list.reverse()
        self.convert_to_commit_data_objects_upstream()
        FileUtils.save_to_file(
            self.commits_file, StringUtils.list_to_multiline_string(self.data.matched_upstream_commit_hashes)
        )

    def _find_missing_upstream_commits_by_message(self, git_log_result, normal_commit_lines):
        # Example line:
        # 'bad6038a4879be7b93eb52cfb54ddfd4ce7111cd YARN-10622. Fix preemption policy to exclude childless ParentQueues.
        # Contributed by Andras Gyori 2021-02-15T14:48:42+01:00'
        found_jira_ids = set(map(lambda x: x.split(COMMIT_FIELD_SEPARATOR)[1][:-1], normal_commit_lines))
        not_found_jira_ids = set(self.data.subjira_ids).difference(found_jira_ids)
        not_found_jira_titles = [
            jira_title for jira_id, jira_title in self.data.jira_ids_and_titles.items() if jira_id in not_found_jira_ids
        ]
        LOG.debug("Found jira ids in git log: %s", found_jira_ids)
        LOG.debug("Not found jira ids in git log: %s", not_found_jira_ids)
        LOG.debug("Trying to find commits by jira titles from git log: %s", not_found_jira_titles)
        output = CommandRunner.egrep_with_cli(
            git_log_result, self.intermediate_results_file, "|".join(not_found_jira_titles)
        )
        output_lines2 = output.split("\n")
        # For these special commits, prepend Jira ID to commit message if it was there
        # Create reverse-dict
        temp_dict = {v: k for k, v in self.data.jira_ids_and_titles.items()}
        modified_log_lines = []
        for log_line in output_lines2:
            # Just a 'smart' heuristic :)
            # Reconstruct commit message by using a merged form of all words until "Contributed".
            commit_msg = ""
            split_line = log_line.split(COMMIT_FIELD_SEPARATOR)
            commit_hash = split_line[0]
            words = split_line[1:]
            for w in words:
                if "Contributed" in w:
                    break
                commit_msg += " " + w
            commit_msg = commit_msg.lstrip()
            if commit_msg not in temp_dict:
                LOG.error("Cannot find Jira ID for commit by its commit message. Git log line: %s", log_line)
            else:
                jira_id = temp_dict[commit_msg]
                words.insert(0, jira_id + ".")
                modified_log_line = commit_hash + " " + COMMIT_FIELD_SEPARATOR.join(words)
                LOG.debug("Adding modified log line. Original: %s, Modified: %s", log_line, modified_log_line)
                modified_log_lines.append(modified_log_line)
        return modified_log_lines

    def find_downstream_commits_auto_mode(self):
        jira_ids = [commit_obj.jira_id for commit_obj in self.data.upstream_commit_data_list]
        for idx, jira_id in enumerate(jira_ids):
            progress = f"[{idx + 1} / {len(jira_ids)}] "
            LOG.info("%s Checking if %s is backported to downstream repo", progress, jira_id)
            downstream_commits_for_jira = self.downstream_repo.log(HEAD, oneline_with_date=True, all=True, grep=jira_id)
            LOG.info("%s Downstream git log result for %s: %s", progress, jira_id, downstream_commits_for_jira)

            if downstream_commits_for_jira:
                backported_commits = [
                    BackportedCommit(CommitData.from_git_log_str(commit_str, format="oneline_with_date"), [])
                    for commit_str in downstream_commits_for_jira
                ]
                LOG.info(
                    "Identified %d backported commits for %s:\n%s",
                    len(backported_commits),
                    jira_id,
                    "\n".join([f"{bc.commit_obj.hash} {bc.commit_obj.message}" for bc in backported_commits]),
                )

                backported_jira = BackportedJira(jira_id, backported_commits)

                for backported_commit in backported_jira.commits:
                    commit_hash = backported_commit.commit_obj.hash
                    LOG.info(
                        "%s Looking for remote branches of backported commit: %s (hash: %s)",
                        progress,
                        jira_id,
                        commit_hash,
                    )
                    backported_commit.branches = self.downstream_repo.branch(None, recursive=True, contains=commit_hash)
                self.data.backported_jiras[jira_id] = backported_jira
                LOG.info("%s Finished checking downstream backport for jira: %s", progress, jira_id)

    def find_downstream_commits_manual_mode(self):
        for branch in self.downstream_branches:
            git_log_result = self.downstream_repo.log(branch, oneline_with_date=True)
            # It's quite complex to grep for multiple jira IDs with gitpython, so let's rather call an external command
            output = CommandRunner.egrep_with_cli(
                git_log_result, self.intermediate_results_file, self.data.piped_jira_ids
            )
            matched_downstream_commit_list = output.split("\n")
            if matched_downstream_commit_list:
                backported_commits = [
                    BackportedCommit(CommitData.from_git_log_str(commit_str, format="oneline_with_date"), [branch])
                    for commit_str in matched_downstream_commit_list
                ]
                LOG.info(
                    "Identified %d backported commits on branch %s:\n%s",
                    len(backported_commits),
                    branch,
                    "\n".join([f"{bc.commit_obj.as_oneline_string()}" for bc in backported_commits]),
                )

                for backported_commit in backported_commits:
                    jira_id = backported_commit.commit_obj.jira_id
                    if jira_id not in self.data.backported_jiras:
                        self.data.backported_jiras[jira_id] = BackportedJira(jira_id, [backported_commit])
                    else:
                        self.data.backported_jiras[jira_id].commits.append(backported_commit)

        # Make sure that missing backports are added as CommitData objects
        for commit_data in self.data.upstream_commit_data_list:
            jira_id = commit_data.jira_id
            if jira_id not in self.data.backported_jiras:
                LOG.debug("%s is not backported to any of the provided branches", jira_id)
                self.data.backported_jiras[jira_id] = BackportedJira(jira_id, [])

    def convert_to_commit_data_objects_upstream(self):
        """
        Iterate over commit hashes, print the following to summary_file for each commit hash:
        <hash> <YARN-id> <commit date>
        :return:
        """
        self.data.upstream_commit_data_list = [
            CommitData.from_git_log_str(commit_str, format="oneline_with_date")
            for commit_str in self.data.matched_upstream_commit_list
        ]
        self.data.matched_upstream_commit_hashes = [
            commit_obj.hash for commit_obj in self.data.upstream_commit_data_list
        ]

    def save_changed_files_to_file(self):
        list_of_changed_files = []
        for c_hash in self.data.matched_upstream_commit_hashes:
            changed_files = self.upstream_repo.diff_tree(c_hash, no_commit_id=True, name_only=True, recursive=True)
            list_of_changed_files.append(changed_files)
            LOG.debug("List of changed files for commit hash '%s': %s", c_hash, changed_files)
        # Filter dupes, flatten list of lists
        list_of_changed_files = [y for x in list_of_changed_files for y in x]
        self.data.list_of_changed_files = list(set(list_of_changed_files))
        LOG.info("Got %d unique changed files", len(self.data.list_of_changed_files))
        FileUtils.save_to_file(
            self.changed_files_file, StringUtils.list_to_multiline_string(self.data.list_of_changed_files)
        )

    def write_summary_file(self):
        FileUtils.save_to_file(self.summary_file, self.data.render_summary_string(self.result_basedir))

    def write_all_changes_files(self):
        """
        Iterate over changed files, print all matching changes to the particular file
        Create changes file for each touched file
        :return:
        """
        LOG.info("Recording changes of individual files...")
        for idx, changed_file in enumerate(self.data.list_of_changed_files):
            target_file = FileUtils.join_path(self.result_basedir, "changes", os.path.basename(changed_file))
            FileUtils.ensure_file_exists(target_file, create=True)

            # NOTE: It seems impossible to call the following command with gitpython:
            # git log --follow --oneline -- <file>
            # Use a simple CLI command instead
            cli_command = (
                f"cd {self.upstream_repo.repo_path} && "
                f"git log {ORIGIN_TRUNK} --follow --oneline -- {changed_file} | "
                f'egrep "{self.data.piped_jira_ids}"'
            )
            LOG.info("[%d / %d] CLI command: %s", idx + 1, len(self.data.list_of_changed_files), cli_command)
            output = CommandRunner.run_cli_command(
                cli_command, fail_on_empty_output=False, print_command=False, fail_on_error=False
            )

            if output:
                LOG.info("Saving changes result to file: %s", target_file)
                FileUtils.save_to_file(target_file, output)
            else:
                LOG.error(
                    f"Failed to detect changes of file: {changed_file}. CLI command was: {cli_command}. "
                    f"This seems to be a programming error. Exiting..."
                )
                FileUtils.save_to_file(target_file, "")
                sys.exit(1)

    def print_summary(self):
        LOG.info(self.data.render_summary_string(self.result_basedir))

    def pickle_umbrella_data(self):
        LOG.debug("Final umbrella data object: %s", self.data)
        LOG.info("Dumping %s object to file %s", JiraUmbrellaData.__name__, self.pickled_data_file)
        PickleUtils.dump(self.data, self.pickled_data_file)
