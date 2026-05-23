#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

COMMIT=""
REPO=""
OUT_DIR=""
THRESHOLD_MB=20
EXECUTE=false
STAGE=false
DRIVE_ROOT=""
PATH_PREFIX=""

usage() {
  cat <<EOF
Usage: $(basename "$0") --commit HASH --repo PATH [options]

Analyze a commit for large files, optionally offload them, and optionally stage git changes.

Required:
  --commit HASH          Commit hash to analyze
  --repo PATH            Local git repository root

Options:
  --out-dir PATH         Directory for intermediate output files
                         (default: ~/Downloads/git-large-files-<commit>)
  --threshold-mb N       Minimum file size in MB to move (default: 20)
  --dry-run              Preview moves without changing files (default)
  --execute              Actually move files to offloaded storage
  --stage                After moving, run git rm/add for deleted files and MOVED placeholders
  --drive-root PATH      Offload destination (passed to git_large_file_mover.py)
  --path-prefix PREFIX   Repository path prefix to strip before offload
  -h, --help             Show this help

Examples:
  $(basename "$0") --commit 6619c839 --repo ~/development/my-repos/knowledge-base-private --dry-run
  $(basename "$0") --commit 6619c839 --repo ~/development/my-repos/knowledge-base-private --execute --stage
EOF
}

msg() {
  echo "$@"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --commit)
      COMMIT="$2"
      shift 2
      ;;
    --repo)
      REPO="$2"
      shift 2
      ;;
    --out-dir)
      OUT_DIR="$2"
      shift 2
      ;;
    --threshold-mb)
      THRESHOLD_MB="$2"
      shift 2
      ;;
    --dry-run)
      EXECUTE=false
      shift
      ;;
    --execute)
      EXECUTE=true
      shift
      ;;
    --stage)
      STAGE=true
      shift
      ;;
    --drive-root)
      DRIVE_ROOT="$2"
      shift 2
      ;;
    --path-prefix)
      PATH_PREFIX="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$COMMIT" || -z "$REPO" ]]; then
  echo "Error: --commit and --repo are required." >&2
  usage >&2
  exit 1
fi

REPO="$(cd "$REPO" && pwd)"

if [[ -z "$OUT_DIR" ]]; then
  OUT_DIR="$HOME/Downloads/git-large-files-${COMMIT}"
fi
OUT_DIR="$(mkdir -p "$OUT_DIR" && cd "$OUT_DIR" && pwd)"

if ! git -C "$REPO" rev-parse --verify "${COMMIT}^{commit}" >/dev/null 2>&1; then
  echo "Error: commit '$COMMIT' not found in repository '$REPO'." >&2
  exit 1
fi

GIT_DETAILS_OUT="$OUT_DIR/git-details-hash-${COMMIT}.txt"
GIT_SIZE_ANALYZER_OUT="$OUT_DIR/git-commit-size-analyzer-out-${COMMIT}.txt"
GIT_ALL_SORTED_OUT="$OUT_DIR/git-commit-analyzer-all-results-sorted.txt"
GIT_MOVER_OUT="$OUT_DIR/git-large-file-mover-out-${COMMIT}.txt"
GIT_STAGE_SUMMARY_OUT="$OUT_DIR/git-stage-summary.txt"
GIT_MOVED_CONTENTS_OUT="$OUT_DIR/contents-MOVED-files.txt"

msg "Repository: $REPO"
msg "Commit: $COMMIT"
msg "Output directory: $OUT_DIR"
msg "Threshold: ${THRESHOLD_MB}MB"
if $EXECUTE; then
  msg "Mode: EXECUTE (files will be moved)"
else
  msg "Mode: DRY RUN (preview only)"
fi
msg ""

msg "Step 1/3: Collecting file sizes from commit..."
(
  cd "$REPO"
  "$SCRIPT_DIR/git-commit-size-detailed.sh" "$COMMIT"
) > "$GIT_DETAILS_OUT"
msg "  Wrote $GIT_DETAILS_OUT"

msg "Step 2/3: Sorting files by size..."
python3 "$SCRIPT_DIR/git_commit_size_analyzer.py" \
  "$GIT_DETAILS_OUT" \
  --all-sorted-out "$GIT_ALL_SORTED_OUT" \
  > "$GIT_SIZE_ANALYZER_OUT"
msg "  Wrote $GIT_SIZE_ANALYZER_OUT"
msg "  Wrote $GIT_ALL_SORTED_OUT"

msg "Step 3/3: Processing large files..."
MOVER_ARGS=(
  python3 "$SCRIPT_DIR/git_large_file_mover.py"
  "$GIT_ALL_SORTED_OUT"
  "$THRESHOLD_MB"
  --repo "$REPO"
)
if $EXECUTE; then
  MOVER_ARGS+=(--execute)
fi
if [[ -n "$DRIVE_ROOT" ]]; then
  MOVER_ARGS+=(--drive-root "$DRIVE_ROOT")
fi
if [[ -n "$PATH_PREFIX" ]]; then
  MOVER_ARGS+=(--path-prefix-to-strip "$PATH_PREFIX")
fi

"${MOVER_ARGS[@]}" > "$GIT_MOVER_OUT"
msg "  Wrote $GIT_MOVER_OUT"

if $STAGE; then
  if ! $EXECUTE; then
    echo "Error: --stage requires --execute (nothing to stage after a dry run)." >&2
    exit 1
  fi

  msg ""
  msg "Staging git changes..."
  (
    cd "$REPO"

    if git ls-files --deleted | grep -q .; then
      git ls-files --deleted -z | xargs -0 git rm
    fi

    while IFS= read -r -d '' moved_file; do
      git add "$moved_file"
    done < <(find . -name '*MOVED*' -not -name '*REMOVED*' -print0)

    git status --short | grep -E 'deleted|^\?\?|^A ' > "$GIT_STAGE_SUMMARY_OUT" || true

    {
      while IFS= read -r filename; do
        echo "Processing file: $filename"
        cat "$filename"
        echo
      done < <(git diff --name-only --cached | grep 'MOVED' || true)
    } > "$GIT_MOVED_CONTENTS_OUT"
  )

  msg "  Wrote $GIT_STAGE_SUMMARY_OUT"
  msg "  Wrote $GIT_MOVED_CONTENTS_OUT"
  msg ""
  msg "Review staged changes in $REPO, then commit when ready:"
  msg "  cd $REPO && git status"
fi

msg ""
if $EXECUTE; then
  msg "Done. Files were moved."
else
  msg "Dry run complete. Review $GIT_MOVER_OUT, then re-run with --execute."
fi
