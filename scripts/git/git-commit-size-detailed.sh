#!/bin/bash

# Script: git-commit-size.sh
# Purpose: List files changed in a commit and their size in the repository.

# Check if a commit hash is provided
if [ $# -ne 1 ]; then
  echo "Usage: $0 <commit hash>" 1>&2
  exit 1
fi

HASH=$1

# Get a list of files in the commit, including the blob hash and file mode.
# Using 'git ls-tree -r' is more robust than parsing 'git diff-tree' for this purpose.
# The format will be: <mode> <type> <object> <file>
# We only care about blobs ('-') which are the files being tracked.
FILE_DETAILS=$(git ls-tree -r "$HASH")

# Loop through each line of file details
echo "$FILE_DETAILS" | while IFS=$' \t' read -r MODE TYPE BLOB_HASH FILE; do
    # Only process entries that are blobs (regular files) and check if a file name exists
    if [[ "$TYPE" == "blob" ]] && [[ -n "$FILE" ]]; then

        # Check if the BLOB_HASH is valid (it should be for a 'blob' type)
        if git cat-file -t "$BLOB_HASH" 2>/dev/null | grep -q 'blob'; then
            # Get the size of the blob in bytes
            SIZE_IN_BYTES=$(git cat-file -s "$BLOB_HASH")

            # Convert the size to a human-readable format
            # Use printf for consistent padding and alignment
            HUMAN_READABLE_SIZE=$(numfmt --to=iec --suffix=B --padding=7 "$SIZE_IN_BYTES")

            # Print the human-readable size and the filename
            # Use printf for clean output formatting
            printf "%-10s %s\n" "$HUMAN_READABLE_SIZE" "$FILE"
        fi
    fi
done

exit 0