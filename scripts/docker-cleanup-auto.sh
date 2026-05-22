#!/bin/bash

function docker-cleanup-auto {
  # --- Configuration ---
  # Keep images newer than ~2 months (Go duration: h = hours, not calendar months).
  TIME_LIMIT="1440h"
  FILTER_ARG="until=$TIME_LIMIT"
  IMAGE_FORMAT="table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}\t{{.Size}}"

  echo "--- 🧹 Starting Docker Image Cleanup ---"
  echo "Policy:"
  echo "  1. Remove all unused dangling images (any age)"
  echo "  2. Remove unused images older than $TIME_LIMIT (tagged and untagged)"
  echo

  echo "--- DRY RUN (step 1): unused dangling images ---"
  DANGLING_IDS=$(docker images --filter "dangling=true" -q)
  if [ -z "$DANGLING_IDS" ]; then
    echo "(none)"
  else
    docker images --filter "dangling=true" --format "$IMAGE_FORMAT"
  fi
  echo

  echo "--- DRY RUN (step 2): images older than $TIME_LIMIT ---"
  echo "(Unused only at deletion; images referenced by containers are kept.)"
  OLD_IDS=$(docker images --filter "$FILTER_ARG" -q)
  if [ -z "$OLD_IDS" ]; then
    echo "(none matching age filter)"
  else
    docker images --filter "$FILTER_ARG" --format "$IMAGE_FORMAT"
  fi
  echo

  if [ -z "$DANGLING_IDS" ] && [ -z "$OLD_IDS" ]; then
    echo "Nothing to clean up. Exiting."
    echo "--- Finish Docker Image Cleanup ---"
    return 0
  fi

  read -r -p "Proceed with deletion as described above? (y/n): " confirmation

  if [[ "$confirmation" =~ ^[Yy]$ ]]; then
    echo
    echo "--- DELETING (step 1): unused dangling images ---"
    docker image prune --force --verbose

    echo
    echo "--- DELETING (step 2): unused images older than $TIME_LIMIT ---"
    docker image prune --all --force --filter "$FILTER_ARG" --verbose

    echo "--- ✅ Deletion Complete ---"
  else
    echo
    echo "--- 🛑 Operation canceled by user. No images were removed. ---"
  fi

  echo "--- Finish Docker Image Cleanup ---"
}
