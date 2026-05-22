#!/bin/bash

function docker-cleanup-auto {
  # --- Configuration ---
  # Set the time limit for images to keep. '2m' means 2 months.
  TIME_LIMIT="2m"
  FILTER_ARG="until=$TIME_LIMIT"

  echo "--- 🧹 Starting Docker Image Cleanup ---"
  echo "Searching for images older than $TIME_LIMIT..."
  echo

  # 1. Simulate Dry Run by Listing the Image IDs to be Deleted
  echo "--- DRY RUN: Images that WOULD BE deleted (Image ID, Created Date, Size) ---"

  # Filter images older than TIME_LIMIT and format the output for display.
  # The 'all=true' ensures dangling and intermediate images are also included in the target list.
  # set -x
  # TODO This might not work correctly ->
  docker images --filter "$FILTER_ARG" --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}\t{{.Size}}"
  IMAGES_TO_DELETE=$(docker images --filter "$FILTER_ARG" --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}\t{{.Size}}")

  if [ -z "$IMAGES_TO_DELETE" ]; then
      echo "No images found older than $TIME_LIMIT. Exiting."
      echo "--- Finish Docker Image Cleanup Script ---"
      exit 0
  fi

  # Print the list of images found
  echo -e "IMAGE ID\tCREATED AT\t\t\tSIZE"
  echo -e "$IMAGES_TO_DELETE"
  echo

  # 2. Ask for Confirmation
  # The 'read' command is safer here.
  read -r -p "Do you want to proceed with the actual deletion of the images listed above? (y/n): " confirmation

  # 3. Check the user's input and run the command if confirmed
  if [[ "$confirmation" =~ ^[Yy]$ ]]; then
      echo
      echo "--- ACTUAL DELETION: Removing old images (Older than $TIME_LIMIT) ---"

      # Using the native 'docker image prune' which is designed for this cleanup.
      # --force suppresses the final confirmation prompt for the prune command.
      docker image prune --force --filter "$FILTER_ARG" --verbose

      echo "--- ✅ Deletion Complete ---"
  else
      echo
      echo "--- 🛑 Operation canceled by user. No images were removed. ---"
  fi

  echo "--- Finish Docker Image Cleanup Script ---"
}
