#!/bin/bash

function commit-all-unstaged {
    for i in $(git diff --name-only); do
        git add ${i}
    done
    git commit
}

function git-search-branches {
    for sha1 in `git log --oneline --all --grep "$1" | cut -d" " -f1`
    do
        git branch -r --contains ${sha1}
    done
}
function git-search-tags {
    for sha1 in `git log --oneline --all --grep "$1" | cut -d" " -f1`
    do
        git tag --contains ${sha1}
    done
}

function git-precommit {
  .git/hooks/pre-commit
}

function gitconfig-private {
    git config user.email "szilard.nemeth88@gmail.com"
    git config user.name "Szilard Nemeth"
}

function gitconfig-cloudera {
    git config user.email snemeth@cloudera.com
    git config user.name "Szilard Nemeth"
}

function gh-apply-patch {
  if [ $# -ne 1 ]; then
    echo "Usage: $0 <pr_id>" 1>&2
    return 1
  fi

  PR_ID=$1

  echo "Showing PR info..."
  gh pr view $PR_ID | head -n 20

  local pr_patch_file="/tmp/github-pr-$PR_ID.patch"
  gh pr diff $PR_ID > /tmp/github-pr-$PR_ID.patch
  echo "Applying PR diff from file: $pr_patch_file"
  git apply $pr_patch_file
}

function gh-diff-cde-backport {
  if [ $# -ne 2 ]; then
    echo "Usage: $0 <pr id for develop> <pr id for feature branch>" 1>&2
    return 1
  fi
  # TODO: Port this to $OTHER_REPOS_DIR/gandras/hadoop-scripts (alias: yarn-backport-diff-generator-upstream)
  # Example usage: gh-diff-cde-backport 5421 5565
  # Example 
  # PR targeting develop: https://github.infra.cloudera.com/CDH/dex/pull/5421
  # PR targeting CDH:DEX-1.20: https://github.infra.cloudera.com/CDH/dex/pull/5565

  # TODO assert 2 jira ids are the same

  set -x
  PR_ID_MAIN_BR="$1"
  PR_ID_FEAT_BR="$2"

  echo "Showing PR info for main branch..."
  gh pr view $PR_ID_MAIN_BR | head -n 20

  echo "Showing PR info for feature branch..."
  gh pr view $PR_ID_FEAT_BR | head -n 20

  echo "Saving PR diff for develop..."
  gh pr diff $PR_ID_MAIN_BR > /tmp/github-pr-$PR_ID_MAIN_BR.patch

  echo "Saving PR diff for feature branch..."
  gh pr diff $PR_ID_FEAT_BR > /tmp/github-pr-$PR_ID_FEAT_BR.patch

  echo "Making diff of 2 PRs"

  diff /tmp/github-pr-$PR_ID_MAIN_BR.patch /tmp/github-pr-$PR_ID_FEAT_BR.patch > /tmp/github-pr-diff-$PR_ID_MAIN_BR_$PR_ID_FEAT_BR.diff
  echo "Diff saved to file: /tmp/github-pr-diff-$PR_ID_MAIN_BR_$PR_ID_FEAT_BR.diff"

  echo "Showing diff:"
  diff --color /tmp/github-pr-$PR_ID_MAIN_BR.patch /tmp/github-pr-$PR_ID_FEAT_BR.patch
  set +x
}

function gh-checkout-pr {
    if [[ "$#" -ne 1 ]]; then
        echo "Usage: $0 <PR ID>"
        echo "Usage example: $0 12345"
        return 1
    fi

    # https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/checking-out-pull-requests-locally
    PR_ID="$1"
    BRANCHNAME="pr-review-$PR_ID"
    git fetch origin pull/$PR_ID/head:$BRANCHNAME
    git checkout $BRANCHNAME
}

function gh-backport-cde-pr {
    if [[ "$#" -lt 2 || "$#" -gt 3 ]]; then
        echo "Usage: $0 <PR ID> <branch to backport> [<source branch>]"
        echo "Usage example: $0 5669 DEX-1.20.1 develop"
        return 1
    fi

    PR_ID=$1
    TARGET_R_BRANCH="$2"
    SOURCE_BRANCH=${3:-origin/$TARGET_R_BRANCH} # Default to TARGET_R_BRANCH if not provided
    TARGET_L_BRANCH="pr-backport-$PR_ID-$TARGET_R_BRANCH"
    FORK_REMOTE=fork
    FORK_REPO_NAME=snemeth
    STATE_FILE="~/.gh-backport-state"

    #TODO Validate if target branch exists
    #TODO error if gh does not exist

    set -e  # Exit on unhandled error

    STEP=1
    if [[ -f "$STATE_FILE" ]]; then
        STEP=$(cat "$STATE_FILE")
    fi

    if [[ "$STEP" -le 1 ]]; then
        git fetch origin
        git fetch fork

        if ! command -v gh &> /dev/null; then
            echo "'gh' CLI not found. Please install GitHub CLI."
            return 1
        fi

        COMMIT_HASH=$(gh pr view $PR_ID --json mergeCommit | jq -r '.mergeCommit.oid')
        PR_TITLE=$(gh pr view $PR_ID --json title | jq -r '.title')

        if ! git cat-file -t "$COMMIT_HASH" &> /dev/null; then
            echo "Commit with hash $COMMIT_HASH not found"
            return 1
        fi

        echo "Found commit: $COMMIT_HASH"
        git --no-pager log --format=%B -n 1 $COMMIT_HASH

        git checkout -b $TARGET_L_BRANCH $SOURCE_BRANCH || git checkout $TARGET_L_BRANCH
        git branch --unset-upstream || true

        if ! git cherry-pick -x "$COMMIT_HASH"; then
            echo "Cherry-pick failed. Resolve conflicts and commit the changes, then re-run this function."
            echo 1 > "$STATE_FILE"
            return 1
        fi

        echo 2 > "$STATE_FILE"
    fi

    if [[ "$STEP" -le 2 ]]; then
        echo "Pushing to remote..."
        if ! git push $FORK_REMOTE -u $TARGET_L_BRANCH; then
            echo "Error while pushing commit"
            git checkout origin/develop && git branch -D $TARGET_L_BRANCH
            return 1
        fi

        echo 3 > "$STATE_FILE"
    fi

    if [[ "$STEP" -le 3 ]]; then
        echo "Creating draft PR..."
        gh pr create --draft --title "$PR_TITLE" --body "Backport of #$PR_ID" --base "$TARGET_R_BRANCH" --head "$FORK_REPO_NAME:$TARGET_L_BRANCH"
        echo "NOTE: Remember to un-draft your PR"
        rm -f "$STATE_FILE"
    fi
}

function gh-create-pr {
    # echo "TODO INCOMPLETE"
    # return 1

    if [[ "$#" -ne 1 ]]; then
        echo "Usage: $0 <PR title>"
        echo "Usage example: $0 DEX-5669"
        return 1
    fi

    if [[ ! "$PWD" =~ cloudera/cde/dex ]]; then
        echo "Current directory is not DEX repo. Please cd into DEX repo first!"
        return 1
    fi

    set -x
    curr_branch=$(git rev-parse --abbrev-ref HEAD)
    PR_TITLE="$1"
    TARGET_R_BRANCH="develop"
    FORK_REPO_NAME="fork"
    FORK_REMOTE=fork
    TARGET_L_BRANCH="$curr_branch"
    TARGET_R_BRANCH="snemeth-$TARGET_L_BRANCH"


    echo "Pushing (dry-run)"
    git push --dry-run $FORK_REMOTE -u $TARGET_L_BRANCH

    set -x
    if ! git push -u $FORK_REMOTE -u $TARGET_L_BRANCH; then
        echo "Error while pushing commit"
        # TODO Reset to original branch
        # git checkout origin/develop && git branch -D $TARGET_L_BRANCH
        return 2
    fi

    echo "Pushing code to forked repo..."
    git push $FORK_REPO_NAME $TARGET_L_BRANCH:$TARGET_L_BRANCH

    echo "Pushing code to origin..."
    git push -u origin $TARGET_L_BRANCH:"$TARGET_R_BRANCH"


    pr_template_file_path=$(find $HOME_LINUXENV_DIR -iname cde-github-pr-template.txt)
    echo "Git push successful, Creating PR with PR template from file: $pr_template_file_path"



    # NOTE: gh pr create does not seem to work well with a forked repo!
    # Related links: 
    #   https://zakuarbor.github.io/blog/github-app-limitation-not-all-refs-are-readable-error/
    #   https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps
    #   https://stackoverflow.com/questions/67628262/oauth-scope-required-for-creating-github-pull-requests-with-personal-access-toke
    #   https://github.com/cli/cli/issues/2691
    #   https://github.com/cli/cli/issues/575#issuecomment-1163143215
    #   https://graphite.dev/guides/create-pr-from-gh-command-line
    #   https://stackoverflow.com/questions/64853120/how-to-make-a-pull-request-using-the-new-github-cli-to-a-remote-repo-without-pu

    # !! DID NOT WORK !!
    # gh pr create --draft --title DEX-15745 --body 'test body' --base develop --head fork:$TARGET_L_BRANCH
    # gh pr create --draft --fill-first --base develop --head DEX-15714

    # OUTPUT: 
    # +gh-create-pr:60> gh pr create --draft --title DEX-15745 --body 'test body' --base develop --head fork:DEX-15745
    # Creating draft pull request for fork:DEX-15745 into develop in CDH/dex
    # pull request create failed: GraphQL: Head sha can't be blank, Base sha can't be blank, Head user can't be blank, Head repository can't be blank, No commits between CDH:develop and , Head ref must be a branch, not all refs are readable (createPullRequest)
    
    # From same repo it works!
    # https://graphite.dev/guides/create-pr-from-gh-command-line
    gh pr create --draft --title $TARGET_L_BRANCH --body-file $pr_template_file_path  --base develop --head $TARGET_R_BRANCH
    set +x
}

function gh-list-branches {
    git_script=$(find $HOME_LINUXENV_DIR/scripts -iname git.sh)
    # export -f _gh-list-branches
    bash -c "source $git_script; _gh-list-branches"
}

function _gh-list-branches {
    # https://stackoverflow.com/a/77609166
    # https://stackoverflow.com/questions/226976/how-can-i-know-if-a-branch-has-been-already-merged-into-master
    local_branches=$(git branch -l | grep -Ev '(main|master)')

    # Ignore PRs merged from main or master branches
    # Example output: 
    # ➜ gh pr list --state closed | awk -F '\t' '{print $1, $3}' 
    # 17 DEX-15961
    # 16 DEX-15259-ci-fixes
    # 1  master
    # 10 irashid:triage_jira_pivot
    # 9 snemeth:DEX-15259-3
    # 8 snemeth:DEX-15259-2
    IFS=' ' mapfile -t arr < <(gh pr list --state merged | awk -F '\t' '{print $1, $3}' | grep -Ev '(main|master)')
    echo "All array elements: ${arr[@]}"

    rm -rf "/tmp/gh-list-branches"; mkdir "/tmp/gh-list-branches"
    for i in "${arr[@]}"
    do
        readarray -d " " -t pair <<< "$i"
        pr_id=${pair[0]}
        branch=${pair[1]//$'\n'/}
        # If branch looks like "snemeth:DEX-1234", cut the remote and keep 'DEX-1234'
        branch=$(echo $branch | sed -re "s/.*://g")

        pr_data=$(gh pr view $pr_id --json title,author)
        pr_title=$(echo $pr_data | jq '.title' | tr -d "\"")
        pr_author=$(echo $pr_data | jq '.author.login' | tr -d "\"")
        pr_commit=$(git log origin/master --grep "#$pr_id" --oneline)
        pr_c_hash=$(git log origin/master --grep "#$pr_id" --pretty=format:%h)


        echo;echo
        echo "Processing PR #$pr_id: $pr_title (Author: $pr_author), branch: $branch, commit hash: $pr_c_hash"

        # TODO Handle revert commits
        if [[ "$pr_commit" == *$'\n'* ]]; then
            echo "Multiple commits found"
            echo "$pr_commit"
            continue
        fi

        if [ ! `git rev-parse --verify $branch 2>/dev/null` ]; then
            echo "Branch does not exist: $branch, skipping"
            continue
        fi

        if [ -z "${pr_commit}" ] || [ -z "${pr_c_hash}" ]; then
            echo "Empty commit or commit hash. Commit: $pr_commit, hash: $pr_c_hash"
            continue
        fi
        # Diff of merge commit of PR
        diff_merge_commit="/tmp/gh-list-branches/${branch}_pr_diff.diff"
        diff_branch="/tmp/gh-list-branches/$branch.diff"

        git diff $pr_c_hash^! > $diff_merge_commit


        # List all commits of branch
        # set -x
        echo "Commits for branch: $branch"
        branch_commits=$(git --no-pager log $branch --no-merges --pretty=format:%h --not master)
        
        # echo "$branch_commits"
        # Important to echo it surrounded with double quotes to preserve newlines
        last_commit=$(echo "$branch_commits" | head -n 1)
        first_commit=$(echo "$branch_commits" | tail -n 1)

        # Uncomment to print commits
        # for commit in $branch_commits; do
        #     git --no-pager log -n1 --oneline $commit
        # done
        echo "Last commit: $last_commit"
        echo "First commit: $first_commit"

        # diff of all commits on branch
        git diff $first_commit^..$last_commit > $diff_branch

        # Final diff of diffs
        if ! diff $diff_merge_commit $diff_branch > /dev/null; then
            echo "Diff files are different: diff $diff_merge_commit $diff_branch"
        else
            echo "Branch can be safely deleted: $branch"
        fi
    done
    echo "Generated files in directory: /tmp/gh-list-branches"
    ls -la "/tmp/gh-list-branches"
}

# TODO Move all cde aliases to a separate git.sh script
function git-sync-cde-develop {
    set -x
    orig_branch=$(git rev-parse --abbrev-ref HEAD)
    git fetch origin
    git checkout develop
    git merge origin/develop
    git status
    git checkout $orig_branch
    set +x
}

function git-sync-cde-featurebranch {
    set -x
    orig_branch=$(git rev-parse --abbrev-ref HEAD)
    git fetch origin
    git checkout develop
    git rebase origin/develop
    git status
    git checkout $orig_branch
    git merge develop
    git --no-pager log -1 --oneline
    set +x
}

function git-format-patch {
    #alias git-save-all-commits="git format-patch $(git rev-list --max-parents=0 HEAD)..HEAD -o /tmp/patches"
    if [ $# -ne 2 ]; then
        echo "Usage: $0 <base branch> <destination dir>" 1>&2
        return 1
    fi
    local base_branch=$1
    local dest_dir=$2

    git format-patch $base_branch..HEAD -o $dest_dir
}

function git-backup-patch-develop-formatpatch {
    #cd $DEX_DEV_ROOT
    local branch=$(git rev-parse --abbrev-ref HEAD)
    local output_dir="$CLOUDERA_TASKS_CDE_DIR/$branch/backup-patches/$(date-formatted)"
    echo "Output dir: $output_dir"
    mkdir -p $output_dir

    git-format-patch origin/develop $output_dir
}

function git-backup-patch-develop-simple {
    set -x
    local branch=$(git rev-parse --abbrev-ref HEAD)
    local output_dir="$CLOUDERA_TASKS_CDE_DIR/$branch/backup-patches-single/"
    mkdir -p $output_dir
    local output_file="$output_dir/backup-$branch-$(date-formatted).patch"
    echo "Creating patch based on develop to: $output_file"
    git diff origin/develop..HEAD > $output_file
    set +x
}

function git-backup-patch-from-branch-simple {
    if [ $# -ne 1 ]; then
        echo "Usage: $0 <base branch>" 1>&2
        return 1
    fi

    local base_branch=$1
    local branch=$(git rev-parse --abbrev-ref HEAD)
    # local output_dir=$(mktemp -d)
    local output_dir="$CLOUDERA_TASKS_CDE_DIR/$branch/backup-patches-single/"
    mkdir -p $output_dir
    local output_file="$output_dir/backup-$branch-$(date-formatted).patch"
    echo "Creating patch based on $base_branch to: $output_file"
    git diff origin/$base_branch..HEAD > $output_file
}

function git-squash-all-based-on-develop {
    # git checkout yourBranch
    COMMIT_MSG="$(git branch --show-current) squashed"
    git reset $(git merge-base develop $(git branch --show-current))
    git add -A
    git commit -m "$COMMIT_MSG"
}

function git-dex-commits-on-feature-branch {
    git rev-list --no-merges --count HEAD ^develop
}


function git-diff-file-list-across-commits {
    # example call: git-diff-file-list-across-commits 5b459b0 fork/DEX-13223

    c1=$(git rev-parse $1)
    c2=$(git rev-parse $2)

    echo "Commit 1 ref: $1"
    echo "Commit 1 hash: $c1"
    echo "Commit 2 ref: $2"
    echo "Commit 1 hash: $c2"


    echo "Commit 1 message: $(git log --oneline $c1 -1)"
    echo "Commit 2 message: $(git log --oneline $c2 -1)"
    echo "Commit 1 # of files: $(git diff --name-only $c1 $c1^ | wc -l)"
    echo "Commit 2 # of files: $(git diff --name-only $c2 $c2^ | wc -l)"

    rm -rf /tmp/commitfilelist/; mkdir -p /tmp/commitfilelist/
    c1_files="/tmp/commitfilelist/c1-file-list-$c1.txt"
    c2_files="/tmp/commitfilelist/c2-file-list-$c2.txt"
    
    echo "Commit 1 file list: $c1_files"
    echo "Commit 2 file list: $c2_files"


    git diff --name-only $c1 $c1^ > $c1_files
    git diff --name-only $c2 $c2^ > $c2_files
    
    cat $c1_files | sort | uniq > /tmp/commitfilelist/c1-files-sort-uniq-$c1.txt
    cat $c2_files | sort | uniq > /tmp/commitfilelist/c2-files-sort-uniq-$c2.txt


    diff_result=/tmp/commitfilelist/diff-c1-vs-c2.txt
    diff /tmp/commitfilelist/c1-files-sort-uniq-$c1.txt /tmp/commitfilelist/c2-files-sort-uniq-$c2.txt > $diff_result

    echo "Diff result file: $diff_result"

    echo "complete"
}

function git-find-removed-line-simple {
    # EXAMPLE: git --no-pager log -G "ENABLE_LOGGER_HANDLER_SANITY_CHECK" --oneline
    git --no-pager log -G "$1" --oneline
}

function git-find-removed-line-grep {
    # EXAMPLE: git --no-pager log -G "ENABLE_LOGGER_HANDLER_SANITY_CHECK" --oneline

    local IFS=$'\n' 
    commits=($(git --no-pager log -G "$1" --oneline))
    # declare -p commits

    # echo "Found commits: "
    printf '%s\n' "${commits[@]}"


    main_dir="/tmp/git-find-removed-line-$(date +%s)/"
    mkdir -p "$main_dir"

    echo "Grepping for individual commits..."
    for commit in "${commits[@]}"
    do
        # https://stackoverflow.com/a/35614403
        # echo -e 'abc\ndef\nghi\nklm' | sed 's/[adgk]/1/g; s/[behl]/2/g; s/[cfim]/3/g'
        commit_dir=$(echo $commit | sed 's/[ _:.></]/-/g;')
        commit_hash=$(echo $commit | cut -d " " -f1)
        grep_result_file="$main_dir/grep-$commit_dir.txt"
        diff_result_file="$main_dir/diff-$commit_dir.txt"
        echo "Processing: $commit_hash --> $grep_result_file"
        
        git show $commit_hash | grep "$1" > $grep_result_file
        git show $commit_hash > $diff_result_file
    done
}