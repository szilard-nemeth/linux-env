import logging
import os

from yarndevfunc.command_runner import CommandRunner
from yarndevfunc.constants import TRUNK, HEAD
from yarndevfunc.utils import auto_str, FileUtils, JiraUtils, PickleUtils, ResultPrinter, StringUtils

LOG = logging.getLogger(__name__)
PICKLED_DATA_FILENAME = "pickled_umbrella_data.obj"


@auto_str
class JiraUmbrellaData:
    def __init__(self):
        self.subjira_ids = []
        self.jira_html = None
        self.piped_jira_ids = None
        self.matched_commit_list = None
        self.matched_commit_hashes = None
        self.list_of_changed_files = None
        self.commit_data_list = None

    @property
    def no_of_matched_commits(self):
        return len(self.matched_commit_list)

    @property
    def no_of_jiras(self):
        return len(self.subjira_ids)

    @property
    def no_of_commits(self):
        return len(self.matched_commit_hashes)

    @property
    def no_of_files(self):
        return len(self.list_of_changed_files)

    def render_summary_string(self, result_basedir):
        # Generate tables first, in order to know the length of the header rows
        commit_list_table = ResultPrinter.print_table(self.commit_data_list,
                                                      lambda commit: (commit.message, commit.date),
                                                      header=["Row", "Commit message", "Commit date"],
                                                      print_result=False, max_width=80, max_width_separator=' ')

        files = FileUtils.find_files(result_basedir, regex=".*", full_path_result=True)
        file_list_table = ResultPrinter.print_table(files,
                                                    lambda file: (file,),
                                                    header=["Row", "File"],
                                                    print_result=False, max_width=80, max_width_separator=os.sep)

        commits_header_line = StringUtils.generate_header_line("COMMITS", char='═',
                                                               length=len(commit_list_table.split('\n')[0])) + "\n"
        result_files_header_line = StringUtils.generate_header_line("RESULT FILES", char='═',
                                                                    length=len(file_list_table.split('\n')[0])) + "\n"

        # Generate summary string
        summary_str = StringUtils.generate_header_line("SUMMARY", char='═',
                                                       length=len(commit_list_table.split('\n')[0])) + "\n"
        summary_str += "Number of jiras: {}\n".format(self.no_of_jiras)
        summary_str += "Number of commits: {}\n".format(self.no_of_commits)
        summary_str += "Number of files changed: {}\n".format(self.no_of_files)
        summary_str += commits_header_line
        summary_str += commit_list_table
        summary_str += "\n\n"
        summary_str += result_files_header_line
        summary_str += file_list_table
        return summary_str


@auto_str
class CommitData:
    def __init__(self, c_hash, jira_id, message, date):
        self.hash = c_hash
        self.jira_id = jira_id
        self.message = message
        self.date = date


class UpstreamJiraUmbrellaFetcher:
    def __init__(self, args, upstream_repo, basedir):
        self.jira_id = args.jira_id
        self.upstream_repo = upstream_repo
        self.basedir = basedir
        self.force_mode = True if args.force_mode else False
        # These fields will be assigned when data is fetched
        self.data = None
        self.result_basedir = None
        self.jira_html_file = None
        self.jira_list_file = None
        self.commits_file = None
        self.changed_files_file = None
        self.summary_file = None
        self.intermediate_results_file = None
        self.pickled_data_file = None

    def run(self):
        self.log_current_branch()
        self.set_file_fields()

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
        self.find_commits_and_save_to_file()
        self.save_changed_files_to_file()
        self.write_summary_file()
        self.write_all_changes_files()
        self.print_summary()
        self.pickle_umbrella_data()

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
        if curr_branch != TRUNK:
            raise ValueError("Current branch is not {}. Exiting!".format(TRUNK))

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
        self.data.jira_html = JiraUtils.download_jira_html(self.jira_id, self.jira_html_file)
        self.data.subjira_ids = JiraUtils.parse_subjiras_from_umbrella_html(self.data.jira_html, self.jira_list_file,
                                                                            filter_ids=[self.jira_id])
        if not self.data.subjira_ids:
            raise ValueError("Cannot find subjiras for jira with id: {}".format(self.jira_id))
        LOG.info("Found subjiras: %s", self.data.subjira_ids)
        self.data.piped_jira_ids = '|'.join(self.data.subjira_ids)

    def find_commits_and_save_to_file(self):
        # It's quite complex to grep for multiple jira IDs with gitpython, so let's rather call an external command
        # TODO query commit date with git log, so subsequent git show call can be eliminated
        git_log_result = self.upstream_repo.log(HEAD, oneline_with_date=True)
        output = CommandRunner.egrep_with_cli(git_log_result, self.intermediate_results_file, self.data.piped_jira_ids)
        self.data.matched_commit_list = output.split("\n")
        if not self.data.matched_commit_list:
            raise ValueError("Cannot find any commits for jira: {}".format(self.jira_id))

        LOG.info("Number of matched commits: %s", self.data.no_of_matched_commits)
        LOG.debug("Matched commits: \n%s", '\n'.join(self.data.matched_commit_list))

        # Commits in reverse order (oldest first)
        self.data.matched_commit_list.reverse()
        self.convert_to_commit_data_objects()
        FileUtils.save_to_file(self.commits_file, '\n'.join(self.data.matched_commit_hashes))

    def convert_to_commit_data_objects(self):
        """
        Iterate over commit hashes, print the following to summary_file for each commit hash:
        <hash> <YARN-id> <commit date>
        :return:
        """
        self.data.commit_data_list = []
        for commit_str in self.data.matched_commit_list:
            comps = commit_str.split(' ')
            # 1. Commit hash: It is in the first column.
            # 2. Jira ID: Expecting the Jira ID to be the first segment of commit message, so this is the second column.
            # 3. Commit message: From first to (last - 1) th index
            # 4. Authored date (commit date): The very last segment is the commit date.
            commit_hash = comps[0]
            jira_id = comps[1]
            commit_msg = ' '.join(comps[1:-1])
            commit_date = comps[-1]
            # Alternatively, this info may be requested with git show,
            # but this requires more CLI calls, so it's not preferred.
            # commit_date = self.upstream_repo.show(commit_hash, no_patch=True, no_notes=True, pretty='%cI')
            self.data.commit_data_list.append(
                CommitData(c_hash=commit_hash, jira_id=jira_id, message=commit_msg, date=commit_date))
        self.data.matched_commit_hashes = [commit_obj.hash for commit_obj in self.data.commit_data_list]

    def save_changed_files_to_file(self):
        list_of_changed_files = []
        for c_hash in self.data.matched_commit_hashes:
            changed_files = self.upstream_repo.diff_tree(c_hash, no_commit_id=True, name_only=True, recursive=True)
            list_of_changed_files.append(changed_files)
            LOG.debug("List of changed files for commit hash '%s': %s", c_hash, changed_files)
        LOG.info("Got %d changed files", len(list_of_changed_files))

        # Filter dupes, flatten list of lists
        list_of_changed_files = [y for x in list_of_changed_files for y in x]
        self.data.list_of_changed_files = list(set(list_of_changed_files))
        LOG.info("Got %d unique changed files", len(self.data.list_of_changed_files))
        FileUtils.save_to_file(self.changed_files_file, '\n'.join(self.data.list_of_changed_files))

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
            target_file = FileUtils.join_path(self.result_basedir, 'changes', os.path.basename(changed_file))
            FileUtils.ensure_file_exists(target_file, create=True)

            # NOTE: It seems impossible to call the following command with gitpython:
            # git log --follow --oneline -- <file>
            # Use a simple CLI command instead
            cli_command = "cd {repo_path} && git log --follow --oneline -- {changed_file} | egrep \"{jira_list}\"".format(
                repo_path=self.upstream_repo.repo_path,
                changed_file=changed_file,
                jira_list=self.data.piped_jira_ids)
            LOG.info("[%d / %d] CLI command: %s", idx + 1, len(self.data.list_of_changed_files), cli_command)
            output = CommandRunner.run_cli_command(cli_command, fail_on_empty_output=False, print_command=False)
            LOG.info("Saving changes result to file: %s", target_file)
            FileUtils.save_to_file(target_file, output)

    def print_summary(self):
        LOG.info(self.data.render_summary_string(self.result_basedir))

    def pickle_umbrella_data(self):
        LOG.debug("Final umbrella data object: %s", self.data)
        LOG.info("Dumping %s object to file %s", JiraUmbrellaData.__name__, self.pickled_data_file)
        PickleUtils.dump(self.data, self.pickled_data_file)
