#!/bin/bash

# Script: git-commit-size-diff.sh
# Purpose: List files CHANGED (added, modified, renamed) in a commit and their size
#          in the repository at that commit.

VERBOSE=0
ARGS=()
for arg in "$@"; do
  case "$arg" in
    --verbose|-v)
      VERBOSE=1
      ;;
    *)
      ARGS+=("$arg")
      ;;
  esac
done

if [ ${#ARGS[@]} -ne 1 ]; then
  echo "Usage: $0 [--verbose] <commit hash>" 1>&2
  exit 1
fi

HASH=${ARGS[0]}

verbose_log() {
  if [ "$VERBOSE" -eq 1 ]; then
    echo "[verbose] $*" 1>&2
  fi
}

verbose_log "Commit: $HASH"
verbose_log "Running: git diff-tree -r --name-only --no-commit-id $HASH"

# Get a list of files that were actually modified/added/deleted in the commit.
# -r: recurse into subtrees
# --name-only: show only the names of files
# --no-commit-id: suppresses the commit ID from the output
# The output will be a list of filenames.
CHANGED_FILES=$(git diff-tree -r --name-only --no-commit-id "$HASH")

FILE_COUNT=0
if [ -n "$CHANGED_FILES" ]; then
  FILE_COUNT=$(printf '%s\n' "$CHANGED_FILES" | grep -cve '^$' || true)
fi
verbose_log "Found $FILE_COUNT changed file(s) to size-check"

# Loop through each changed file
INDEX=0
echo "$CHANGED_FILES" | while IFS= read -r FILE; do
    # Skip if the file is empty (e.g., if the commit was only a deletion)
    if [[ -z "$FILE" ]]; then
        continue
    fi

    INDEX=$((INDEX + 1))

    # Check if the file exists as a blob in the commit tree.
    # It might not exist if it was deleted in this commit.
    BLOB_INFO=$(git ls-tree "$HASH" -- "$FILE" 2>/dev/null)

    # Check if BLOB_INFO is not empty and the type is 'blob' (i.e., a file exists)
    # The format is: <mode> <type> <object> <file>
    if [[ -n "$BLOB_INFO" ]] && echo "$BLOB_INFO" | grep -q ' blob '; then
        # Extract the BLOB_HASH from the ls-tree output
        BLOB_HASH=$(echo "$BLOB_INFO" | awk '{print $3}')

        # Double check the blob hash is valid and a blob (should be)
        if git cat-file -t "$BLOB_HASH" 2>/dev/null | grep -q 'blob'; then
            # Get the size of the blob in bytes
            SIZE_IN_BYTES=$(git cat-file -s "$BLOB_HASH")

            # Convert the size to a human-readable format
            # Use numfmt for consistent padding and alignment.
            HUMAN_READABLE_SIZE=$(numfmt --to=iec --suffix=B --padding=7 "$SIZE_IN_BYTES" 2>/dev/null)

            # Fallback if numfmt isn't available
            if [ $? -ne 0 ]; then
                HUMAN_READABLE_SIZE="$SIZE_IN_BYTES B" # Simple fallback
            fi

            if [ "$VERBOSE" -eq 1 ]; then
              # 10485760 bytes = 10 MiB (10 * 1024 * 1024); always log large blobs in verbose mode
              if [ "$INDEX" -eq 1 ] || [ $((INDEX % 25)) -eq 0 ] || [ "$INDEX" -eq "$FILE_COUNT" ] || [ "$SIZE_IN_BYTES" -gt 10485760 ]; then
                verbose_log "[$INDEX/$FILE_COUNT] $HUMAN_READABLE_SIZE  $FILE"
              fi
            fi

            # Print the human-readable size and the filename
            printf "%-10s %s\n" "$HUMAN_READABLE_SIZE" "$FILE"
        elif [ "$VERBOSE" -eq 1 ] && [ $((INDEX % 100)) -eq 0 ]; then
            verbose_log "[$INDEX/$FILE_COUNT] skip (invalid blob): $FILE"
        fi
    elif [ "$VERBOSE" -eq 1 ] && [ $((INDEX % 100)) -eq 0 ]; then
        verbose_log "[$INDEX/$FILE_COUNT] skip (deleted or not a file in commit): $FILE"
    fi
done

verbose_log "Finished sizing commit files"

exit 0