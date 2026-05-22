function sync-cde-investigation-notes {
    python3 "$HOME_LINUXENV_DIR"/scripts/investigation/sync_cde_investigation_notes.py "$@"
}

function sync-cde-investigation-notes-examples {
  echo "sync_cde_investigation_notes.py ENGESC-33163/investigation/ --exclude .git --exclude __pycache__ --exclude tmp --exclude container-splits-stderr --exclude container-splits-stdout --exclude container-splits-stderr --exclude cursor_log_analysis* "
}

