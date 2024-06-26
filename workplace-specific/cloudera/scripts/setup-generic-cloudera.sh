function cde-grep-dex-wiki {
  cd $CDE_DEV_ROOT/dex.wiki
  git checkout master && git pull
  grep -i $1 . -R 
}

function cde-open-dex-wiki {
  subl $CDE_DEV_ROOT/dex.wiki/$1
}


function download-gbn-logs {
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
