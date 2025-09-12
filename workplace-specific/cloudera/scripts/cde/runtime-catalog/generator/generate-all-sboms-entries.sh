#! /bin/bash

## INTENDED TO BE EXECUTED ON LOCAL MACHINE AS SBOMS ARE IN PLACE

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DEX_HOME="/Users/snemeth/development/cloudera/cde/dex"


function validate_input() {
  if [ $# -ne 1 ]; then
    echo "Error: This script requires exactly one parameter, the DEX task id in KB private e.g. 'DEX-17194'"
    exit 1
  else
    DEX_TASK_ID="$1"
    echo "DEX_TASK_ID=$DEX_TASK_ID"
  fi
}


function setup_workdir() {
  TASKDIR="/Users/snemeth/development/my-repos/knowledge-base-private/cloudera/tasks/cde/$DEX_TASK_ID/testing-results-local/"
  . "$SCRIPT_DIR/common.sh"
  WORKDIR=$(determine_latest_workdir)
  echo "Work dir is: $WORKDIR"
}


function cleanup_catalog() {
  echo "Cleanup.."
  rm -rf "$DEX_HOME/build-tools/rtcatalog/enriched-catalog-entries"
  mkdir "$DEX_HOME/build-tools/rtcatalog/enriched-catalog-entries"
}


function build_catalog_server() {
  echo "Making catalog-server"
  cd "$DEX_HOME/cmd"
  make catalog-server
  cd -
}

function generate_sboms() {
  cd $DEX_HOME/build-tools/rtcatalog
  python3 get_release_sbom.py --release 1.25.0-b78 --image-filter spark --save-disk-space
  python3 get_release_sbom.py --release 1.25.0-b78 --image-filter livy --save-disk-space
  python3 get_release_sbom.py --release 1.25.0-b78 --image-filter runtime-python-builder --save-disk-space
}




function generate_catalog_entries() {
  echo "GENERATING RUNTIME CATALOG! Running load_release_entries.sh..."
  rm -rf "$WORKDIR"
  mkdir -p "$WORKDIR"
  "$DEX_HOME/build-tools/rtcatalog/load_release_entries.sh" > "$WORKDIR/load_release_entries_sh_output.txt" 2>&1
}


function copy_results_to_workdir() {
  echo "Copying results to workdir: $WORKDIR"
  set -x
  cp -R "$DEX_HOME/build-tools/rtcatalog/enriched-catalog-entries" "$WORKDIR"
  set +x
}


function save_old_catalog() {
  cd "$DEX_HOME"
  git fetch origin
  git show origin/develop:pkg/control-plane/service/catalog-entries.json > /tmp/catalog-entries-develop.json
}


function compare_catalogs() {
  echo "Comparing catalogs..."
  set -x
  old_catalog="/tmp/catalog-entries-develop.json"
  new_catalog="$WORKDIR/enriched-catalog-entries/catalog-entries.json"
  python3 /Users/snemeth/development/my-repos/linux-env/workplace-specific/cloudera/scripts/cde/runtime-catalog/compare_catalog.py "$old_catalog" "$new_catalog" > "$WORKDIR/compare_catalog_output.txt"
  cp "$old_catalog" "$WORKDIR/"
  cp "$new_catalog" "$WORKDIR/"
  set +x
}

function cleanup_empty_workdir() {
  echo "Clean up workdir if empty: $WORKDIR"
  if [ -d "$WORKDIR" ] && [ -z "$(ls -A "$WORKDIR")" ]; then
    rmdir "$WORKDIR"
    echo "Work dir was empty and has been removed."
  else
    echo "Work dir not empty, keeping: $WORKDIR"
  fi
}


### Main execution flow
validate_input "$@"
setup_workdir
cleanup_catalog
### 1. Generate sboms - SKIP
# generate_sboms
build_catalog_server
generate_catalog_entries
copy_results_to_workdir
save_old_catalog
compare_catalogs
cleanup_empty_workdir
