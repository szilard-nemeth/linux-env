## Commands to run

1. `git-commit-size-detailed.sh`: Checks the specified commit hash for modified/added/deleted files and prints human-readable file sizes.
2. `git_commit_size_analyzer.py`: Sorts the result of `git-commit-size-detailed.sh` by size (bytes) and shows top N results.
3. `git_large_file_mover.py`: Moves large files above a certain threshold to Google Drive (offload). Input is the output of `git_commit_size_analyzer.py`.

```bash
COMMIT=6619c839

# Scripts
GIT_SCRIPT_COMMIT_SIZE_SH="$HOME/development/my-repos/linux-env/scripts/git/git-commit-size-detailed.sh"
GIT_SCRIPT_COMMIT_SIZE_ANALYZER="$HOME/development/my-repos/linux-env/scripts/git/git_commit_size_analyzer.py"
GIT_SCRIPT_LARGE_FILE_MOVER="$HOME/development/my-repos/linux-env/scripts/git/git_large_file_mover.py"

# Output files
BASEDIR="$HOME/Downloads/git-cleanup-kb-private-20251022/part2/"
GIT_DETAILS_OUT="$BASEDIR/git-details-kb-private-hash-$COMMIT.txt"
GIT_SIZE_ANALYZER_OUT="$BASEDIR/git-commit-size-analyzer-out-$COMMIT.txt"
GIT_LARGE_FILE_MOVER_OUT="$BASEDIR/git-large-file-mover-out-$COMMIT.txt"

# Launch scripts
$GIT_SCRIPT_COMMIT_SIZE_SH $COMMIT > $GIT_DETAILS_OUT
python3 $GIT_SCRIPT_COMMIT_SIZE_ANALYZER $GIT_DETAILS_OUT > $GIT_SIZE_ANALYZER_OUT

GIT_SIZE_ANALYZER_ALL_RESULTS_OUT=$(grep "Temporary file with all results ordered created at.*" $GIT_SIZE_ANALYZER_OUT | cut -d ':' -f2 | sed 's/^[[:space:]]*//')
echo "git_commit_size_analyzer.py all results file: $GIT_SIZE_ANALYZER_ALL_RESULTS_OUT"
cp $GIT_SIZE_ANALYZER_ALL_RESULTS_OUT $BASEDIR/git-commit-analyzer-all-results-sorted.txt

# !! Make sure to enable dry run first !!
python3 $GIT_SCRIPT_LARGE_FILE_MOVER $GIT_SIZE_ANALYZER_OUT 20 > $GIT_LARGE_FILE_MOVER_OUT
```

## Verification, checking results

1. git rm all removed files:
```bash
git ls-files --deleted -z | xargs -0 git rm
```

2. git add files matching pattern, untracked
```bash
find . -name '*MOVED*' -not -name "*REMOVED*" -print0 | xargs -0 git add
```

3. Check all added/remove files
```bash
git st | grep "deleted\|new file" > /tmp/results
```

4. Verify contents of MOVED files
```bash
git diff --name-only --cached | grep ".*MOVED.*" | xargs -n 1 -I {} /bin/bash -c "echo 'Processing file: {}'; cat {}"
```

or if the above does not work:
```bash
git diff --name-only --cached | grep ".*MOVED.*" | while read -r filename; do
    echo "Processing file: $filename"
    cat "$filename"
done > ~/Downloads/git-cleanup-kb-private-20251022/contents-MOVED-files.txt
```

## Script output
