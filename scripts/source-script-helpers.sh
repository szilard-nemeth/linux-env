function sync-cde-investigation-notes {
    python3 "$HOME_LINUXENV_DIR"/scripts/investigation/sync_cde_investigation_notes.py "$@"
}

function sync-cde-investigation-notes-examples {
  echo "sync-cde-investigation-notes /Users/snemeth/development/my-repos/knowledge-base-private/cloudera/tasks/cde/ENGESC-33163/investigation/ --exclude .git --exclude __pycache__ --exclude tmp"
}

