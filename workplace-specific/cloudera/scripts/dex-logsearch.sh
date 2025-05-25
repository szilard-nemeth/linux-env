#!/usr/bin/env bash

function dex-logsearch-last-hour {
  AWS_PROFILE=cu_logs_dev log-search --env dev --from 'now-1h/h' --to 'now/h' '@app:dex'
}

function dex-logsearch-last-hour2 {
  AWS_PROFILE=cu_logs_dev log-search --env dev --from 'now-1h/h' --to 'now/h'  --fields-to-print "@timestamp,@message" --print-stats --print-config "@app.keyword:dex AND @cluster:mow-priv AND @env:manowar_dev"
}

function dex-logsearch-dex-13563 {
  # FROM: May 9 2024 9:18:00 AM 
  # TO: May 9 2024, 5:12:00 PM --> Add 30 seconds
  local dest_file=/tmp/logsearch-results-$(date-formatted)
  echo "Saving results to file: $dest_file"
  set -x
  AWS_PROFILE=cu_logs_dev log-search --env dev --from "2024-05-09T09:18:00.000Z" --to "2024-05-09T17:12:30.000Z" --fields-to-print "@timestamp,@message" --print-stats --print-config "@app.keyword:dex AND @cluster:mow AND @env:manowar_dev" > $dest_file
  set +x
}


function dex-logsearch-dex-14173 {
  local dest_file=/tmp/logsearch-results-dex-14173-$(date-formatted)
  echo "Saving results to file: $dest_file"
  set -x
  AWS_PROFILE=cu_logs_dev log-search --env dev --from "2024-07-16T17:01:00.000Z" --to "2024-07-16T17:49:00.000Z" --fields-to-print "@timestamp,@message" --print-stats --print-config "@app.keyword:dex AND @cluster:mow-int-eu-central-1 AND @env:manowar_int_euc1" > $dest_file
  set +x
}

function dex-logsearch-ENGESC-26999-prod {
  local dest_file=/tmp/logsearch-results-ENGESC-26999-$(date-formatted)
  echo "Saving results to file: $dest_file"
  set -x
  AWS_PROFILE=cu_logs_prod log-search --env prod --from "2024-09-25T16:26:39.000Z" --to "2024-09-25T16:27:42.000Z" --fields-to-print "@timestamp,@message" --print-stats --print-config "@app.keyword:dex AND @cluster:mow-prod AND @env:manowar_prod" > $dest_file
  set +x
}

function dex-logsearch-ENGESC-30122-prod {
  local dest_file=/tmp/logsearch-results-ENGESC-30122-$(date-formatted)
  echo "Saving results to file: $dest_file"
  set -x
  AWS_PROFILE=cu_logs_prod log-search --env prod --from "2025-05-23T00:00:00.000Z" --to "2025-05-25T00:00:00.000Z" --fields-to-print "@timestamp,@message" --print-stats --print-config "@app.keyword:dex AND @cluster:mow-prod AND @env:manowar_prod" > $dest_file
  set +x
}

function dex-logsearch-DEX-14006 {
  # Example 1
  # CLUSTER="cluster-9pchfn2n"
  # APP="test351-dex"

  # Example 2
  CLUSTER="cluster-zsgt9lr9"
  APP="inplacejgp-dex"

  local dest_file=/tmp/logsearch-results-DEX-14006-${CLUSTER}-$(date-formatted)
  echo "Saving results to file: $dest_file"
  set -x
  AWS_PROFILE=cu_logs_dev log-search --env dev --from "2025-01-01T00:00:00.000Z" --to "2025-03-04T00:00:00.000Z" --fields-to-print "@timestamp,@message" --print-stats --print-config "@app.keyword:$APP AND @message:\"$CLUSTER\"" > $dest_file
  set +x
}