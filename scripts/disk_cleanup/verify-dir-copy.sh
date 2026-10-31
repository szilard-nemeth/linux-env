#!/usr/bin/env bash

# Script: verify-dir-copy.sh
# Purpose: Before deleting a directory, prove that another directory holds everything in it.
#          Every regular file and symlink under SOURCE must exist at the same relative path
#          under COPY, with identical content (cmp) / identical link target.
#          Files that exist only under COPY are fine and are just counted.
#
# Usage:   verify-dir-copy.sh [-v] SOURCE COPY
#            -v   also print one OK line per verified file
#
# Exit:    0 = safe to delete SOURCE (nothing would be lost)
#          1 = something under SOURCE is missing from COPY or differs
#          2 = usage error

set -uo pipefail

verbose=0
if [[ "${1:-}" == "-v" ]]; then
    verbose=1
    shift
fi

if [[ $# -ne 2 ]]; then
    echo "Usage: $(basename "$0") [-v] SOURCE COPY" >&2
    exit 2
fi

src="${1%/}"
copy="${2%/}"
for d in "$src" "$copy"; do
    if [[ ! -d "$d" ]]; then
        echo "ERROR: not a directory: $d" >&2
        exit 2
    fi
done

ok=0
missing=0
differs=0
empty_dirs_missing=0

# -print0 / read -d '' so names with spaces or newlines are handled
while IFS= read -r -d '' path; do
    rel="${path#"$src"/}"
    target="$copy/$rel"
    if [[ -L "$path" ]]; then
        if [[ ! -L "$target" ]]; then
            echo "MISSING  (symlink) $rel"
            missing=$((missing + 1))
        elif [[ "$(readlink "$path")" != "$(readlink "$target")" ]]; then
            echo "DIFFERS  (symlink target) $rel"
            differs=$((differs + 1))
        else
            ok=$((ok + 1))
            [[ $verbose -eq 1 ]] && echo "OK       $rel"
        fi
    elif [[ ! -e "$target" ]]; then
        echo "MISSING  $rel"
        missing=$((missing + 1))
    elif ! cmp -s "$path" "$target"; then
        echo "DIFFERS  $rel"
        differs=$((differs + 1))
    else
        ok=$((ok + 1))
        [[ $verbose -eq 1 ]] && echo "OK       $rel"
    fi
done < <(find "$src" \( -type f -o -type l \) -print0)

# Empty directories hold no data, but report them so nothing is silently dropped
while IFS= read -r -d '' dir; do
    rel="${dir#"$src"/}"
    if [[ ! -d "$copy/$rel" ]]; then
        echo "MISSING  (empty dir) $rel"
        empty_dirs_missing=$((empty_dirs_missing + 1))
    fi
done < <(find "$src" -mindepth 1 -type d -empty -print0)

src_files=$((ok + missing + differs))
copy_files=$(find "$copy" \( -type f -o -type l \) | wc -l | tr -d ' ')

echo
echo "SOURCE: $src ($src_files files, $(du -sh "$src" | cut -f1))"
echo "COPY:   $copy ($copy_files files, $(du -sh "$copy" | cut -f1))"
echo "  identical:          $ok"
echo "  missing from COPY:  $missing"
echo "  content differs:    $differs"
echo "  empty dirs missing: $empty_dirs_missing"
echo "  only in COPY:       $((copy_files - ok - differs)) (fine)"

if [[ $missing -eq 0 && $differs -eq 0 ]]; then
    echo "RESULT: SAFE TO DELETE SOURCE - every file in it exists in COPY with identical content"
    exit 0
fi
echo "RESULT: NOT SAFE - save the MISSING / DIFFERS entries above before deleting SOURCE"
exit 1
