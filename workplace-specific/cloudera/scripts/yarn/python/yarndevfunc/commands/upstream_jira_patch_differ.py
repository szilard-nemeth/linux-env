import logging

from pythoncommons.file_utils import FileUtils
from pythoncommons.patch_utils import PatchUtils
from pythoncommons.string_utils import auto_str

from yarndevfunc.git_wrapper import GitWrapper

LOG = logging.getLogger(__name__)


@auto_str
class BranchResults:
    def __init__(self, branch_name, exists, commits, commit_hashes):
        self.branch_name = branch_name
        self.exists = exists
        self.commits = commits
        self.commit_hashes = commit_hashes
        self.git_diff = None

    @property
    def number_of_commits(self):
        return len(self.commits)

    @property
    def single_commit_hash(self):
        if len(self.commit_hashes) > 1:
            raise ValueError(
                "This object has multiple commit hashes. "
                "The intended use of this method is when there's only one single commit hash!"
            )
        return self.commit_hashes[0]


class UpstreamJiraPatchDiffer:
    def __init__(self, args, upstream_repo, basedir):
        self.jira_id = args.jira_id
        self.branches = args.branches
        self.upstream_repo = upstream_repo
        self.basedir = basedir

    def run(self):
        FileUtils.ensure_dir_created(self.basedir)

        branch_results = {}
        for branch in self.branches:
            LOG.info("Processing branch: %s", branch)

            exists = self.upstream_repo.is_branch_exist(branch)
            commits = self.upstream_repo.log(branch, grep=self.jira_id, oneline=True)
            commit_hashes = GitWrapper.extract_commit_hash_from_gitlog_results(commits)
            branch_result = BranchResults(branch, exists, commits, commit_hashes)
            branch_results[branch] = branch_result

            # Only store diff if number of matched commits for this branch is 1
            if branch_result.number_of_commits == 1:
                commit_hash = branch_result.single_commit_hash
                # TODO create diff_with_parent helper method to GitWrapper
                diff = self.upstream_repo.diff_between_refs(commit_hash + "^", commit_hash)
                branch_result.git_diff = diff

                diff_filename = f"{self.jira_id}-{branch}.diff"
                PatchUtils.save_diff_to_patch_file(diff, FileUtils.join_path(self.basedir, diff_filename))

        # Validate results
        branch_does_not_exist = [b_res.branch_name for br, b_res in branch_results.items() if not b_res.exists]
        zero_commit = [b_res.branch_name for br, b_res in branch_results.items() if b_res.number_of_commits == 0]
        multiple_commits = [b_res.branch_name for br, b_res in branch_results.items() if b_res.number_of_commits > 1]

        LOG.debug("Branch result objects: %s", branch_results)
        if branch_does_not_exist:
            raise ValueError("The following branches are not existing for Jira ID '{}': {}", branch_does_not_exist)

        if zero_commit:
            raise ValueError(
                "The following branches do not contain commit for Jira ID '{}': {}", self.jira_id, zero_commit
            )

        if multiple_commits:
            raise ValueError(
                "The following branches contain multiple commits for Jira ID '{}': {}", self.jira_id, multiple_commits
            )

        LOG.info("Generated diff files: ")
        diff_files = FileUtils.find_files(self.basedir, self.jira_id + "-.*", single_level=True, full_path_result=True)
        for f in diff_files:
            LOG.info("%s: %s", f, FileUtils.get_file_size(f))
