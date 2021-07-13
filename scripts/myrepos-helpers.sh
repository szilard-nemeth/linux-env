PYTHON_COMMONS_ROOT="$HOME/development/my-repos/python-commons/"
COMMON_EXCLUDES=("site-packages" ".git" ".idea" "pyspark" "Chromagnon" "fork" "dist_test" "samples-books-school-experiments" "superscraper-libs", "the-coding-train-challenges", "coding-practice")

#Problem: $CLOUDERA_DEV_ROOT is not yet defined atm
YARN_CDSW_DIR="$HOME/development/cloudera/my-repos/yarn-cdsw"

function myrepos-list-pythoncommons {
  #Could be an alias but would not work from another script that sources this
  #Example error message:
  # /Users/snemeth/.linuxenv/scripts/myrepos-helpers.sh: line 18: myrepos-list-pythoncommons: command not found
  find $MY_REPOS_DIR $YARN_CDSW_DIR -type d -name venv -print0 | xargs -0 -I % find % -type d \( -iname "pythoncommons" -o -iname "python_commons*" \) | sort
}

function myrepos-install-pythoncommons {
  #Make sure to unset PYTHONPATH: python-commons won't be installed in virtualenv when it is found *ANYWHERE* on PYTHONPATH
  #Example output:
  #➜ pip3 show python-commons
  #Name: python-commons
  #Version: 0.1.0
  #Author: Szilard Nemeth
  #Author-email: szilard.nemeth88@gmail.com
  #License: Copyright (c) 2020, Szilard Nemeth
  #Location: /Users/snemeth/development/my-repos/linux-env/venv/lib/python3.8/site-packages
  find $MY_REPOS_DIR $YARN_CDSW_DIR -type d -name venv -print0 | xargs -0 -t -I % sh -c 'cd %;source ./bin/activate;unset PYTHONPATH;./bin/pip3 install git+https://github.com/szilard-nemeth/python-commons.git;deactivate'
}

function myrepos-install-pythoncommons-dev {
  find $MY_REPOS_DIR $YARN_CDSW_DIR -type d -name venv -print0 | xargs -0 -t -I % sh -c 'cd %;source ./bin/activate;unset PYTHONPATH;./bin/pip3 install $MY_REPOS_DIR/python-commons;deactivate' && say "pythoncommons completed"
}

function myrepos-install-linuxenv-dependencies {
  cd $LINUXENV_DIR/venv;source ./bin/activate;pip3 uninstall -y python-commons yarn-dev-tools;./bin/pip3 install -r $LINUXENV_DIR/requirements.txt && deactivate && say "Installation completed"
}

function myrepos-install-linuxenv-dependencies-dev {
  cd $LINUXENV_DIR/venv;source ./bin/activate;pip3 uninstall -y python-commons yarn-dev-tools;./bin/pip3 install $MY_REPOS_DIR/python-commons $MY_REPOS_DIR/yarn-dev-tools && deactivate && say "Installation completed"
}

function myrepos-install-googleapiwrapper-dev {
  grep --include=requirements.txt -rw $MY_REPOS_DIR -e "google-api-wrapper.git" | cut -d':' -f1 | sed 's/requirements.txt/venv/g' | tr '\n' '\0' | xargs -0 -t -I % sh -c 'cd %;source ./bin/activate;unset PYTHONPATH;./bin/pip3 install $MY_REPOS_DIR/google-api-wrapper;deactivate';say "google API wrapper completed"
}


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

function myrepos-reset-pythoncommons() {
  echo "Pushing python-commons"
  cd $PYTHON_COMMONS_ROOT; git push

  echo "Removing python-commons from projects"
  myrepos-rm-pythoncommons

  echo "Listing installed python-commons (Should give empty results): "
  myrepos-list-pythoncommons

  echo "Reinstalling python-commons in each project"
  myrepos-install-pythoncommons

  echo "Listing installed python-commons:"
  myrepos-list-pythoncommons
}

function myrepos-grep-python() {
  myrepos_filtered_find.py --extension "*.py" --exclude $COMMON_EXCLUDES | xargs grep $1
}

function myrepos-grep-all() {
  # This did not work with files containing spaces:
  #https://serverfault.com/questions/268368/how-can-i-handle-spaces-in-file-names-when-using-xargs-on-find-results

  #TODO Binary file /Users/snemeth/development/my-repos/resume/fonts/FontAwesome.ttf matches
  # TODO Add option to filter only test files with myrepos_filtered_find.py: https://stackoverflow.com/questions/898669/how-can-i-detect-if-a-file-is-binary-non-text-in-python // https://unix.stackexchange.com/questions/46276/finding-all-non-binary-files
  myrepos_filtered_find.py --exclude $COMMON_EXCLUDES | tr '\n' '\0' | xargs -0 grep $1
}

function myrepos-grep-C5-python-todos {
 myrepos_filtered_find.py --extension "*.py" --exclude $COMMON_EXCLUDES | xargs grep -C5 TODO
}

# TODO add function that greps for python + shell scripts --> myrepos_filtered_find should accept multiple extensions

function myrepos-grep-C5() {
  myrepos_filtered_find.py --extension "*.py" --exclude $COMMON_EXCLUDES | xargs grep -C5 $1
}