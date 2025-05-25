#! /bin/bash


setopt interactivecomments
TASKDIR_LOCAL=/Users/snemeth/development/my-repos/knowledge-base-private/cloudera/tasks/cde/DEX-17194/testing-results-local/
WORKDIR="$TASKDIR_LOCAL/testing-20250508_2/"
local_entry="$WORKDIR/enriched-catalog-entries/cde-1.25.0-dl-7.1.7.3016-chainguard-20230214-spark-3.2.3-java-11-python-3.9.json"
# cat $local_entry

TASKDIR_YCLOUD=/Users/snemeth/development/my-repos/knowledge-base-private/cloudera/tasks/cde/DEX-17194/testing-results-from-ycloud/
WORKDIR="$TASKDIR_YCLOUD/testing-20250508_3/"
ycloud_entry="$WORKDIR/enriched-catalog-entries/cde-1.25.0-dl-7.1.7.3016-chainguard-20230214-spark-3.2.3-java-11-python-3.9.json"
# cat $ycloud_entry

echo "Diff $ycloud_entry vs. $local_entry"
diff $ycloud_entry $local_entry