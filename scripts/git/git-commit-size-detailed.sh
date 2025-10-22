#!/bin/bash

# Script: git-commit-size-diff.sh
# Purpose: List files CHANGED (added, modified, renamed) in a commit and their size
#          in the repository at that commit.

# Check if a commit hash is provided
if [ $# -ne 1 ]; then
  echo "Usage: $0 <commit hash>" 1>&2
  exit 1
fi

HASH=$1

# Get a list of files that were actually modified/added/deleted in the commit.
# -r: recurse into subtrees
# --name-only: show only the names of files
# --no-commit-id: suppresses the commit ID from the output
# The output will be a list of filenames.
CHANGED_FILES=$(git diff-tree -r --name-only --no-commit-id "$HASH")

# Loop through each changed file
echo "$CHANGED_FILES" | while IFS= read -r FILE; do
    # Skip if the file is empty (e.g., if the commit was only a deletion)
    if [[ -z "$FILE" ]]; then
        continue
    fi

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

            # Print the human-readable size and the filename
            printf "%-10s %s\n" "$HUMAN_READABLE_SIZE" "$FILE"
        fi
    fi
done

exit 0