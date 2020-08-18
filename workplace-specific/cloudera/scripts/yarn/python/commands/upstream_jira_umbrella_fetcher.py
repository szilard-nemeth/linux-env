import logging
import os

from command_runner import CommandRunner
from constants import TRUNK, HEAD
from utils import auto_str, FileUtils, JiraUtils

LOG = logging.getLogger(__name__)


@auto_str
class CommitData:
    def __init__(self, c_hash, jira_id, message, date):
        self.hash = c_hash
        self.jira_id = jira_id
        self.message = message
        self.date = date


@auto_str
class JiraUmbrellaSummary:
    def __init__(self, jira_ids, matched_commit_hashes, list_of_changed_files, commit_data_list):
        self.no_of_jiras = len(jira_ids)
        self.no_of_commits = len(matched_commit_hashes)
        self.no_of_files = len(list_of_changed_files)
        self.commit_data_list = commit_data_list

    def to_summary_file_str(self):
        summary_str = "Number of jiras: {}\n".format(self.no_of_jiras)
        summary_str += "Number of commits: {}\n".format(self.no_of_commits)
        summary_str += "Number of files changed: {}\n".format(self.no_of_files)

        summary_str += "COMMITS: \n"
        for c_data in self.commit_data_list:
            summary_str += "{} {}\n".format(c_data.message, c_data.date)

        return summary_str


class UpstreamJiraUmbrellaFetcher:
    def __init__(self, args, upstream_repo, basedir):
        self.jira_id = args.jira_id
        self.upstream_repo = upstream_repo
        self.basedir = basedir

    def run(self):
        curr_branch = self.upstream_repo.get_current_branch_name()
        LOG.info("Current branch: %s", curr_branch)

        if curr_branch != TRUNK:
            raise ValueError("Current branch is not {}. Exiting!".format(TRUNK))

        self.create_files()
        jira_ids, piped_jira_ids = self.fetch_jira_ids()
        matched_commit_list = self.find_commits_based_on_jira_ids(piped_jira_ids)
        matched_commit_hashes = self.save_matched_commits_to_file(matched_commit_list)
        list_of_changed_files = self.save_changed_files_to_file(matched_commit_hashes)
        summary = self.write_summary_file(jira_ids, list_of_changed_files, matched_commit_hashes, matched_commit_list)
        self.write_all_changes_files(list_of_changed_files, piped_jira_ids)
        self.print_summary(self.result_basedir, summary)

    def create_files(self):
        self.result_basedir = FileUtils.join_path(self.basedir, self.jira_id)
        self.jira_html_file = FileUtils.join_path(self.result_basedir, "jira.html")
        self.jira_list_file = FileUtils.join_path(self.result_basedir, "jira-list.txt")
        self.commits_file = FileUtils.join_path(self.result_basedir, "commit-hashes.txt")
        self.changed_files_file = FileUtils.join_path(self.result_basedir, "changed-files.txt")
        self.summary_file = FileUtils.join_path(self.result_basedir, "summary.txt")
        self.intermediate_results_file = FileUtils.join_path(self.result_basedir, "intermediate-results.txt")
        FileUtils.create_files(self.jira_html_file, self.jira_list_file, self.commits_file, self.changed_files_file, self.summary_file,
                               self.intermediate_results_file)

    def fetch_jira_ids(self):
        LOG.info("Fetching HTML of jira: %s", self.jira_id)
        jira_html = JiraUtils.download_jira_html(self.jira_id, self.jira_html_file)
        jira_ids = JiraUtils.parse_subjiras_from_umbrella_html(jira_html, self.jira_list_file,
                                                               filter_ids=[self.jira_id])
        if not jira_ids:
            raise ValueError("Cannot find subjiras for jira with id: {}".format(self.jira_id))
        LOG.info("Found subjiras: %s", jira_ids)
        piped_jira_ids = '|'.join(jira_ids)
        return jira_ids, piped_jira_ids

    def find_commits_based_on_jira_ids(self, piped_jira_ids):
        # It's quite complex to grep for multiple jira IDs with gitpython, so let's rather call an external command
        git_log_result = self.upstream_repo.log(HEAD, oneline=True)
        output = CommandRunner.egrep_with_cli(git_log_result, self.intermediate_results_file, piped_jira_ids)
        matched_commit_list = output.split("\n")
        LOG.info("Number of matched commits: %s", len(matched_commit_list))
        LOG.debug("Matched commits: \n%s", '\n'.join(matched_commit_list))
        if not matched_commit_list:
            raise ValueError("Cannot find any commits for jira: {}".format(self.jira_id))
        return matched_commit_list

    def save_matched_commits_to_file(self, matched_commit_list):
        # Commits in reverse order (oldest first)
        matched_commit_list.reverse()
        matched_commit_hashes = [c.split(' ')[0] for c in matched_commit_list]
        FileUtils.save_to_file(self.commits_file, '\n'.join(matched_commit_hashes))
        return matched_commit_hashes

    def save_changed_files_to_file(self, matched_commit_hashes):
        list_of_changed_files = []
        for c_hash in matched_commit_hashes:
            changed_files = self.upstream_repo.diff_tree(c_hash, no_commit_id=True, name_only=True, recursive=True)
            list_of_changed_files.append(changed_files)
            LOG.debug("List of changed files for commit hash '%s': %s", c_hash, changed_files)
        LOG.info("Got %d changed files", len(list_of_changed_files))
        # Filter dupes, flatten list of lists
        list_of_changed_files = [y for x in list_of_changed_files for y in x]
        list_of_changed_files = list(set(list_of_changed_files))
        LOG.info("Got %d unique changed files", len(list_of_changed_files))
        FileUtils.save_to_file(self.changed_files_file, '\n'.join(list_of_changed_files))
        return list_of_changed_files

    def write_summary_file(self, jira_ids, list_of_changed_files, matched_commit_hashes, matched_commit_list):
        """
        Iterate over commit hashes, print the following to summary_file for each commit hash:
        <hash> <YARN-id> <commit date>
        :param jira_ids:
        :param list_of_changed_files:
        :param matched_commit_hashes:
        :param matched_commit_list:
        :return:
        """
        commit_data_list = []
        for commit_str in matched_commit_list:
            comps = commit_str.split(' ')
            c_hash = comps[0]
            commit_date = self.upstream_repo.show(c_hash, no_patch=True, no_notes=True, pretty='%cI')
            commit_data_list.append(
                CommitData(c_hash=c_hash, jira_id=comps[1], message=' '.join(comps[2:]), date=commit_date))
        summary = JiraUmbrellaSummary(jira_ids, matched_commit_hashes, list_of_changed_files, commit_data_list)
        FileUtils.save_to_file(self.summary_file, summary.to_summary_file_str())
        return summary

    def write_all_changes_files(self, list_of_changed_files, piped_jira_ids):
        """
        Iterate over changed files, print all matching changes to the particular file
        Create changes file for each touched file
        :param list_of_changed_files:
        :param piped_jira_ids:
        :return:
        """
        LOG.info("Recording changes of individual files...")
        for idx, changed_file in enumerate(list_of_changed_files):
            target_file = FileUtils.join_path(self.result_basedir, 'changes', os.path.basename(changed_file))
            FileUtils.ensure_file_exists(target_file, create=True)

            # NOTE: It seems impossible to call the following command with gitpython:
            # git log --follow --oneline -- <file>
            # Use a simple CLI command instead
            cli_command = "cd {repo_path} && git log --follow --oneline -- {changed_file} | egrep \"{jira_list}\"".format(
                repo_path=self.upstream_repo.repo_path,
                changed_file=changed_file,
                jira_list=piped_jira_ids)
            LOG.info("[%d / %d] CLI command: %s", idx + 1, len(list_of_changed_files), cli_command)
            output = CommandRunner.run_cli_command(cli_command, fail_on_empty_output=False, print_command=False)
            LOG.info("Saving changes result to file: %s", target_file)
            FileUtils.save_to_file(target_file, output)

    @staticmethod
    def print_summary(result_basedir, summary):
        LOG.info("=================SUMMARY=================")
        LOG.info(summary.to_summary_file_str())
        LOG.info("=========================================")
        files = FileUtils.find_files(result_basedir, regex=".*", full_path_result=True)
        LOG.info("All result files: \n%s", '\n'.join(files))
