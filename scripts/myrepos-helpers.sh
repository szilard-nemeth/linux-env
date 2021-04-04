function myrepos-rm-pythoncommons() {
  # Remove python-commons from all locations
  # Note: This intends to remove python-commons from default location
  rm -rf "/tmp/pcrm/" && mkdir -p "/tmp/pcrm/"
  PC_LOC=$(pip3 show python-commons 2>/dev/null | grep Location | cut -d ':' -f2 | tr -s ' ')
  if [[ -d ${PC_LOC} ]]; then
    echo "Found python-commons in: $PC_LOC"
    echo "Removing python-commons from $PC_LOC"
    set -x
    mv -v $PC_LOC "/tmp/pcrm/"
    set +x
  else
      echo "python-commons not found with pip3"
  fi

  #Original alias
  #mkdir -p /tmp/pcrm/;myrepos-list-pythoncommons | xargs -t -I % sh -c 'XARGSFILE=%;mkdir -p /tmp/pcrm/$XARGSFILE && mv $XARGSFILE /tmp/pcrm/$XARGSFILE'
  #xargs can't handle longer commands than 255 bytes and if it exceeds this limit, placeholders will not be replaced!
  #Solution: cd into dir, then execute command, then cd back to prev dir to have a shorter command
	IFS=$'\n';
	for line in `myrepos-list-pythoncommons | awk -F '/venv' '{print $1,$2}'`; do
		IFS=' ' read -r -A arr <<< "$line"
		#set -x
		#It's safer to always remove the dir /tmp/prcrm/ rather then removing the results of the above command list-pythoncommons command
		#Removing it in every iteration avoids "Directory not empty" errors from mv
		rm -rf "/tmp/pcrm/"
		local proj_dir="${arr[1]}"
		local result_dir="${arr[2]}"
    echo "Removing python-commons from $proj_dir/venv"
		#Cd into dir to make command shorter
		cd $proj_dir
		dest_path="/tmp/pcrm/$result_dir"
		mkdir -p $dest_path
		mv -v "./venv/$result_dir" $dest_path
		#set +x
		IFS=$'\n';
	done
}

alias myrepos-list-pythoncommons="find $MY_REPOS_DIR -type d -name venv -print0 | xargs -0 -I % find % -type d \\( -iname \"pythoncommons\" -o -iname \"python_commons*\" \\) | sort"

#Make sure to unset PYTHONPATH: python-commons won't be installed in virtualenv when it is found *ANYWHERE* on PYTHONPATH
#Example output:
#➜ pip3 show python-commons
#Name: python-commons
#Version: 0.1.0
#Author: Szilard Nemeth
#Author-email: szilard.nemeth88@gmail.com
#License: Copyright (c) 2020, Szilard Nemeth
#Location: /Users/snemeth/development/my-repos/linux-env/venv/lib/python3.8/site-packages
alias myrepos-installpythoncommons="find $MY_REPOS_DIR -type d -name venv -print0 | xargs -0 -t -I % sh -c 'cd %;source ./bin/activate;unset PYTHONPATH;./bin/pip3 install git+https://github.com/szilard-nemeth/python-commons.git;deactivate'"


function myrepos-reset-pythoncommons() {
  echo "Pushing python-commons"
  cd $PYTHON_COMMONS_ROOT; git push

  echo "Removing python-commons from projects"
  myrepos-rm-pythoncommons

  echo "Listing installed python-commons (Should give empty results): "
  myrepos-list-pythoncommons

  echo "Reinstalling python-commons in each project"
  myrepos-installpythoncommons

  echo "Listing installed python-commons:"
  myrepos-list-pythoncommons
}

function myrepos-grep() {
  myrepos_filtered_find.py --extension "*.py" --exclude "site-packages" ".git" "pyspark" "Chromagnon" "fork" "dist_test" "samples-books-school-experiments" | xargs grep $1
}

function myrepos-grep-C5() {
  myrepos_filtered_find.py --extension "*.py" --exclude "site-packages" ".git" "pyspark" "Chromagnon" "fork" | xargs grep -C5 $1
}