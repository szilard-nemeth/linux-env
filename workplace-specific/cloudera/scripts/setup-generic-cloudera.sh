function cde-grep-dex-wiki {
  cd $CDE_DEV_ROOT/dex.wiki
  git checkout master && git pull
  grep -i $1 . -R 
}

function cde-open-dex-wiki {
  subl $CDE_DEV_ROOT/dex.wiki/$1
}


function download-gbn-logs {
  # echo "Moved to DEXter, decommissioned."
  # echo "Example usage: dexter triage download-logs"
  # echo "Example usage: dexter triage download-logs 1.23.0 --failed"
  # return 1
	if [ $# -ne 2 ]; then
    echo "Usage: $0 <GBN> <DEX version>"
    return 1
  fi
	# Example arg: https://cloudera-build-us-west-1.vpc.cloudera.com/s3/build/52060464/LOGS/
	# gbn=$(echo $1 | sed 's/.*\/s3\/build\/\([[:digit:]]*\).*/\1/')

	# Usage: <GBN> <DEX version>
	# Usage: 52060464 1.22.0-b66
	local gbn=$1
	local dex_version=$2
	local dir_name="gbn-$gbn-$dex_version"
	local tmp_dir="/tmp/$dir_name"
	
	mkdir -p $tmp_dir
	wget -P $tmp_dir -r -nH --cut-dirs=2 --reject="index.html*"  --no-parent https://cloudera-build-us-west-1.vpc.cloudera.com/s3/build/$gbn/LOGS/


	local target_dir=~/Downloads/$dir_name
	if [[ ! -e $target_dir ]]; then
			mkdir -p $target_dir
			cp -R $tmp_dir ~/Downloads/
			echo "Downloaded to: $target_dir"
	else
			echo "Skip copying, directory already exists: $target_dir"
	fi
}


function download-gtn-logs {
	if [ $# -ne 2 ]; then
    echo "Usage: $0 <GTN> <Quanta link>"
    return 1
  fi

	# Usage: 
	# 53112090 https://logserver.eng.hortonworks.com/?prefix=qelogs/qaas/st-dex-vnd27o
	local gtn="$1"
	local quanta_link="$2"
	
	local dir_name="gtn-$gtn"
	local target_dir="/tmp/$dir_name"

	mkdir -p $target_dir
	wget -P $target_dir -r -nH --cut-dirs=2 --reject="index.html*"  --no-parent $quanta_link


	echo "Execute: "
	echo "mv $target_dir ~/Downloads/$dir_name"

}

function md2jira {
  if [ $# -ne 1 ]; then
    echo "Usage: $0 <input file>"
    return 1
  fi

	local input="$1"
	j2m $input --toJ
}

function md2jira-cb {
	pbpaste | j2m --stdin --toJ | subl
}

function grep-in-diagbundle {
	if [ $# -ne 2 ]; then
    echo "Usage: $0 <diagnostic bundle file> <pattern to grep for>"
    return 1
  fi

	BUNDLE="$1"
	PATTERN="$2"
	
	
	NEW_TMP_DIR=`mktemp -d`
	bundle_name_txt=$(echo ${BUNDLE} | sed 's/.tar.gz$/.txt/')
	bundle_name=$(echo ${BUNDLE} | sed 's/.tar.gz$//')
	bundle_date=$(date -r $(echo $bundle_name | grep -o 'diagnostics-[0-9]*' | cut -d '-' -f2))
	telemetry_logs_file_name=$(tar -tf $BUNDLE | grep ".*telemetry-logs.*" | sed "s/$bundle_name\///")
	# telemetry_logs_dir_name=$(echo ${telemetry_logs_file_name} | sed 's/.zip$//')

	echo "$BUNDLE ::: Pattern to search for: $PATTERN"
	echo "$BUNDLE ::: Temp dir: $NEW_TMP_DIR"
	echo "$BUNDLE ::: Telemetry logs file: $telemetry_logs_file_name"
	echo "$BUNDLE ::: Bundle name: $bundle_name"
	echo "$BUNDLE ::: Bundle date: $bundle_date"


	curr_date=$(date +%Y%m%d_%H%M%S)
	GREP_RESULT_FILE="/tmp/grep-results-$bundle_name_txt-$curr_date"
	GREP_RESULT_FILE_FILELISTING="/tmp/grep-results-filelisting-$bundle_name_txt-$curr_date"
	tar -C $NEW_TMP_DIR -zxf $BUNDLE
	set -x
	tar -C "$NEW_TMP_DIR/$bundle_name" -zxf "$NEW_TMP_DIR/$bundle_name/$telemetry_logs_file_name"
	set +x
	
	# UNCOMMENT THIS TO SHOW RESULT FILES
	# find $NEW_TMP_DIR
	
	set -x
	grep -InHR $PATTERN $NEW_TMP_DIR > $GREP_RESULT_FILE
	grep -lR $PATTERN $NEW_TMP_DIR > $GREP_RESULT_FILE_FILELISTING
	set +x
	rm -rf $NEW_TMP_DIR

	echo "$BUNDLE ::: Grep results: $GREP_RESULT_FILE"
	echo "$BUNDLE ::: Grep results for file listing: $GREP_RESULT_FILE_FILELISTING"
	echo "$BUNDLE ::: No. of matches in $GREP_RESULT_FILE: $(wc -l $GREP_RESULT_FILE)"


	# ////////////////////
	# tar -C $NEW_TMP_DIR -zxvf $BUNDLE $telemetry_logs_file_name
	# GREP / https://stackoverflow.com/a/42258011
	# for i in $(tar -tzf "$BUNDLE"); do
  # 	results=$(tar -Oxzf "$BUNDLE" "$i" | grep --label="$i" -H "$PATTERN")
	# 	echo "$results"
  # done
	# zgrep -a "33724" $NEW_TMP_DIR/$telemetry_logs_file_name
	# rm -rf $NEW_TMP_DIR
}

function grep-in-all-diag-bundles {
	if [ $# -ne 2 ]; then
    echo "Usage: $0 <base dir> <pattern to grep for>"
    return 1
  fi

  BASE_DIR="$1"
  PATTERN="$2"

  for bundle in $(find $BASE_DIR -type f -depth 1 -exec basename {} \; | grep ".*diagnostics-[0-9]*.*"); do
  	echo "============================================================="
  	# echo "Grepping in bundle: $bundle $PATTERN"
  	grep-in-diagbundle $bundle $PATTERN
		echo "============================================================="
		echo;echo
  done
}


function casefiles-download {
  cd ~/development/my-repos/linux-env
  venv=$(poetry env list --full-path | grep "3\.9" | cut -d ' ' -f1)
  $venv/bin/python $(which ./workplace-specific/cloudera/scripts/download-casefiles.py)
}