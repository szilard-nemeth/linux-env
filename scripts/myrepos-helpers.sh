PYTHON_COMMONS_ROOT="$HOME/development/my-repos/python-commons/"
COMMON_EXCLUDES=("site-packages" ".git" ".idea" "pyspark" "Chromagnon" "fork" "dist_test" "samples-books-school-experiments" "superscraper-libs", "the-coding-train-challenges", "coding-practice")

function find-poetry-projects {
#  set -x
  POETRY_ROOT=$HOME/Library/Caches/pypoetry/virtualenvs/
  for proj in $(gfind $MY_REPOS_DIR -name 'pyproject.toml' -printf "%h\n"); do
    # echo "cding to $proj"
    cd $proj
    p_env=$(poetry env list)

    if [[ "$?" -ne 0 ]]; then
      # echo "Poetry setup not defined for $proj, skipping..."
      echo -n '' # placeholder
    else
       p_env=$(echo $p_env | cut -d' ' -f1)
       final_p_env="$POETRY_ROOT/$p_env"
       echo $final_p_env
    fi
    popd 1>/dev/null
#    set +x
  done
}

function pip-install-to-env {
  set -x
  env_path=$1
  package=$2
  echo "$env_path\n$package" | xargs -n 2 sh -c 'cd $1;source ./bin/activate;unset PYTHONPATH;./bin/pip3 install $2;deactivate' argv0
  set +x
}

function myrepos-install {
  #Make sure to unset PYTHONPATH: python-commons won't be installed in virtualenv when it is found *ANYWHERE* on PYTHONPATH
  #Example output:
  #➜ pip3 show python-commons
  #Name: python-commons
  #Version: 0.1.0
  #Author: Szilard Nemeth
  #Author-email: szilard.nemeth88@gmail.com
  #License: Copyright (c) 2020, Szilard Nemeth
  #Location: /Users/snemeth/development/my-repos/linux-env/venv/lib/python3.8/site-packages

  package_to_install="$1"
  say="$2"

  # 1. This is for legacy (non-poetry based) projects
  for env_path in $(find $MY_REPOS_DIR -type d -name venv); do
    echo "Current virtualenv: $env_path"
    pip-install-to-env $env_path $package_to_install
  done

  # 2. Poetry projects
  poetry_envs=($(find-poetry-projects))
  echo "Discovered Poetry envs: $poetry_envs"
  IFS=$'\n'
  for env_path in $poetry_envs; do
    echo "Current Poetry env: $env_path"
    pip-install-to-env $env_path $package_to_install
  done
}

# TODO migrate
function myrepos-list-pythoncommons {
  #Could be an alias but would not work from another script that sources this
  #Example error message:
  # /Users/snemeth/.linuxenv/scripts/myrepos-helpers.sh: line 18: myrepos-list-pythoncommons: command not found
  find $MY_REPOS_DIR -type d -name venv -print0 | xargs -0 -I % find % -type d \( -iname "pythoncommons" -o -iname "python_commons*" \) | sort
}


function myrepos-install-pythoncommons-git-all {
  myrepos-install "git+https://github.com/szilard-nemeth/python-commons.git" "pythoncommons completed"
}

function myrepos-install-pythoncommons-dev-all {
  myrepos-install "$MY_REPOS_DIR/python-commons" "pythoncommons completed"
}

function myrepos-install-pythoncommons {
  myrepos-install-pythoncommons-dev-all
}

function myrepos-install-pythoncommons-dev-just-yarndevtools {
  sh -c 'cd $MY_REPOS_DIR/yarn-dev-tools/;poetry update python-common-lib' && say "pythoncommons completed"
}

function myrepos-install-pythoncommons-dev-just-expense-summarizer {
  echo "!! NOT WORKING, MIGRATE TO POETRY !!"
  sh -c 'cd $MY_REPOS_DIR/monthly-expense-summarizer/;poetry update python-common-lib' && say "pythoncommons completed"
}


function myrepos-install-yarndevtools-dev-all {
  myrepos-install "$MY_REPOS_DIR/yarn-dev-tools" "yarndevtools completed"
}


function myrepos-install-pytest-all {
  myrepos-install "pytest" "Installation of pytest to all venvs completed"
}

function myrepos-install-linuxenv-deps {
  cd $LINUXENV_DIR;poetry install && say "Installation completed"
}

function myrepos-install-googleapiwrapper-dev-just-yarndevtools {
  sh -c 'cd $MY_REPOS_DIR/yarn-dev-tools/;poetry update google-api-wrapper2' && say "Google API wrapper completed"
}

function myrepos-install-googleapiwrapper-dev {
  # Legacy projects
  for env_path in $(grep --include=requirements.txt -rw $MY_REPOS_DIR -e "google-api-wrapper.git" | cut -d':' -f1 | sed 's/requirements.txt/venv/g'); do
    echo "Current virtualenv: $env_path"
    pip-install-to-env $env_path "$MY_REPOS_DIR/google-api-wrapper"
  done

  # 2. Poetry projects
  poetry_envs=($(find-poetry-projects))
  echo "Discovered Poetry envs: $poetry_envs"
  IFS=$'\n'
  for env_path in $poetry_envs; do
    echo "Current Poetry env: $env_path"
    sh -c 'cd $env_path/;poetry update google-api-wrapper2' && say "Google API wrapper completed"
  done

  # 3. Poetry dev
  # Tried the following poetry commands, neither of them worked:
  # poetry update --only localdev google-api-wrapper2 -vvv
  # poetry update --only localdev -vvv --no-cache | subl
  # poetry update google-api-wrapper2 --only localdev -vvv --no-cache 
  venv=$(poetry env list --full-path | cut -d ' ' -f1)
  # cp -R ~/development/my-repos/google-api-wrapper/googleapiwrapper/  /Users/snemeth/Library/Caches/pypoetry/virtualenvs/email-sorter-sOW-XU4m-py3.8/lib/python3.8/site-packages/googleapiwrapper
  cp -R ~/development/my-repos/google-api-wrapper/googleapiwrapper/ $venv/lib/python3.8/site-packages/googleapiwrapper
  cp -R ~/development/my-repos/python-commons/pythoncommons/ $venv/lib/python3.8/site-packages/pythoncommons
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
  #https://serverfault.com/questions/268368/how-can-proj-handle-spaces-in-file-names-when-using-xargs-on-find-results

  #TODO Binary file /Users/snemeth/development/my-repos/resume/fonts/FontAwesome.ttf matches
  # TODO Add option to filter only test files with myrepos_filtered_find.py:
  #  https://stackoverflow.com/questions/898669/how-can-proj-detect-if-a-file-is-binary-non-text-in-python
  #  https://unix.stackexchange.com/questions/46276/finding-all-non-binary-files
  myrepos_filtered_find.py --exclude $COMMON_EXCLUDES | tr '\n' '\0' | xargs -0 grep $1
}

function myrepos-grep-C5-python-todos {
 myrepos_filtered_find.py --extension "*.py" --exclude $COMMON_EXCLUDES | xargs grep -C5 TODO
}

function myrepos-grep-python-todos {
 myrepos_filtered_find.py --extension "*.py" --exclude $COMMON_EXCLUDES | xargs grep TODO
}

function myrepos-grep-todos {
 myrepos_filtered_find.py --exclude $COMMON_EXCLUDES | xargs grep TODO
}

# TODO add function that greps for python + shell scripts --> myrepos_filtered_find should accept multiple extensions

function myrepos-grep-C5() {
  myrepos_filtered_find.py --extension "*.py" --exclude $COMMON_EXCLUDES | xargs grep -C5 $1
}

function yarndevtools-run-tests {
  cd /Users/snemeth/development/my-repos/yarn-dev-tools/; \
  MAIL_ACC_PASSWORD=fake MAIL_ACC_USER=jenkinstestreporter@gmail.com \
  poetry run python -m pytest -k 'CdswConfigReaderTest' \
  --html=report.html \
  --self-contained-html --doctest-ignore-import-errors \
  --doctest-modules \
  --junitxml=junit/test-resultpy39.xml \
  --cov=./ \
  --cov-report=html
  # MAIL_ACC_PASSWORD=fake MAIL_ACC_USER=jenkinstestreporter@gmail.com poetry run python -m pytest -k 'CdswConfigReaderTest' --html=report.html --self-contained-html --doctest-ignore-import-errors --doctest-modules --junitxml=junit/test-resultpy39.xml --cov=./ --cov-report=xml --cov-report=html
}

function email-sorter-nsziszy {
  cd /Users/snemeth/development/my-repos/email-sorter/
  (export PYTHONCOMMONS_PROJECTUTILS_PROJECT_DETERMINATION_STRATEGY=common_file && python3 /Users/snemeth/development/my-repos/email-sorter/emailsorter/cli.py -d --account-email nsziszy@gmail.com discover-inbox)
}

function email-sorter-snemeth {
  cd /Users/snemeth/development/my-repos/email-sorter/
  (export PYTHONCOMMONS_PROJECTUTILS_PROJECT_DETERMINATION_STRATEGY=common_file && python3 /Users/snemeth/development/my-repos/email-sorter/emailsorter/cli.py -d --account-email snemeth@cloudera.com discover-inbox)
}