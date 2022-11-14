#!/usr/bin/env bash
YARN_DEV_TOOLS_DIR="$HOME/development/my-repos/yarn-dev-tools"
PYTHON_COMMONS_DIR="$HOME/development/my-repos/python-commons"
GOOGLE_API_WRAPPER_DIR="$HOME/development/my-repos/google-api-wrapper/"
PROJ_NAME_YARN_DEV_TOOLS="yarndevtools"
PROJ_NAME_PYTHON_COMMONS="pythoncommons"
PROJ_NAME_GOOGLE_API_WRAPPER="googleapiwrapper"

function get-project-dir() {
  local project="$1"

  if [[ ${project} == $PROJ_NAME_PYTHON_COMMONS ]]; then
    echo "$PYTHON_COMMONS_DIR"
  elif [[ ${project} == $PROJ_NAME_YARN_DEV_TOOLS ]]; then
    echo "$YARN_DEV_TOOLS_DIR"
  elif [[ ${project} == $PROJ_NAME_GOOGLE_API_WRAPPER ]]; then
    echo "$GOOGLE_API_WRAPPER_DIR"
  else
    echo "Unknown project: $project"
    return 1
  fi
}

# TODO Look for better way to check exit codes ("$?" -ne 0) ?
function check-git-changes() {
  local repo_dir=$1
  cd $repo_dir
  current_br=$(git rev-parse --abbrev-ref HEAD)

  if [[ "master" != "$current_br" ]]; then
    echo "Current branch is not master in $(pwd)! Exiting..."
    return 1
  fi

  if [[ ! -z $(git status -s) ]]; then
    echo "There are changed files in $repo_dir. Please remove changes and re-run this script"
    return 2
  fi

  if [[ ! -z $(git --no-pager log origin/master..HEAD) ]]; then
    echo "There are unpushed commits in $repo_dir. Please push or remove these commits and re-run this script"
    return 2
  fi
}

function show-changes() {
  echo "Listing changes in $PYTHON_COMMONS_DIR ..." && cd $PYTHON_COMMONS_DIR && git --no-pager log origin/master..HEAD
  echo "Listing changes in $GOOGLE_API_WRAPPER_DIR ..." && cd $GOOGLE_API_WRAPPER_DIR && git --no-pager log origin/master..HEAD
  echo "Listing changes in $YARN_DEV_TOOLS_DIR ..." && cd $YARN_DEV_TOOLS_DIR && git --no-pager log origin/master..HEAD

  check-git-changes $PYTHON_COMMONS_DIR
  if [[ "$?" -ne 0 ]]; then
    return 1
  fi

  check-git-changes $GOOGLE_API_WRAPPER_DIR
  if [[ "$?" -ne 0 ]]; then
    return 1
  fi

  check-git-changes $YARN_DEV_TOOLS_DIR
  if [[ "$?" -ne 0 ]]; then
    return 1
  fi
}

function reset() {
  cd $PYTHON_COMMONS_DIR
  git reset --hard origin/master

  cd $GOOGLE_API_WRAPPER_DIR
  git reset --hard origin/master

  cd $YARN_DEV_TOOLS_DIR
  git reset --hard origin/master
}

function poetry-build-and-publish() {
  local project="$1"
  echo "Publishing $project..."
  poetry build && poetry publish
  ret=$?

  if [[ "$ret" -ne 0 ]]; then
    echo "Failed to build / publish $project. Skipping commit"
    # TODO should do git repo reset here (for specific project)
    return 1
  fi
}

function commit-version-bump() {
  commit_msg="$1"
  echo "Committing version bump..."
  git commit -am "\"$commit_msg\""
  if [[ $GIT_PUSH -eq 1 ]]; then
    git push
  fi
}

function bump-project-version() {
  local project="$1"
  echo "Bumping version of: $project"

  project_dir=`get-project-dir $project`

  if [[ "$?" -ne 0 ]]; then
    echo $project_dir
    return 1
  fi

  cd $project_dir
  current_version=$(poetry version --short)
  echo "Current version of $project is: $current_version"

  poetry version patch
  git --no-pager diff

  poetry-build-and-publish $project
  if [[ "$?" -ne 0 ]]; then
    return 1
  else
    commit-version-bump "bump version (patch)"
  fi
}

function bump-pythoncommons-version() {
  bump-project-version "$PROJ_NAME_PYTHON_COMMONS"
  if [[ "$?" -ne 0 ]]; then
    echo "Failed to bump version of $PROJ_NAME_PYTHON_COMMONS"
    return 1
  fi

  new_pythoncommons_version=$(poetry version --short)
}

function bump-googleapiwrapper-version() {
  echo "Bumping version of: $PROJ_NAME_GOOGLE_API_WRAPPER"

  cd $GOOGLE_API_WRAPPER_DIR
  # NOTE: Apparently, the command below does not work, in contrary to the documentation:
  # poetry add python-common-lib==$new_pythoncommons_version
  # Use sed to upgrade the package's version
  sed -i '' -e "s/^python-common-lib = \"[0-9].*/python-common-lib = \"$new_pythoncommons_version\"/" pyproject.toml

  bump-project-version "$PROJ_NAME_GOOGLE_API_WRAPPER"
  if [[ "$?" -ne 0 ]]; then
    echo "Failed to bump version of $PROJ_NAME_GOOGLE_API_WRAPPER"
    return 1
  fi

  new_googleaiwrapper_version=$(poetry version --short)
}

function bump-yarndevtools-version() {
  bump-project-version $PROJ_NAME_YARN_DEV_TOOLS
  if [[ "$?" -ne 0 ]]; then
    echo "Failed to bump version of $PROJ_NAME_YARN_DEV_TOOLS"
    return 1
  fi

  new_yarndevtools_version=$(poetry version --short)
}

function update-package-versions-in-yarndevtools() {
  echo "$PROJ_NAME_YARN_DEV_TOOLS: Increasing package versions for: $PROJ_NAME_GOOGLE_API_WRAPPER, $PROJ_NAME_PYTHON_COMMONS"
  cd $YARN_DEV_TOOLS_DIR
  sed -i '' -e "s/^python-common-lib = \"[0-9].*/python-common-lib = \"$new_pythoncommons_version\"/" pyproject.toml
  sed -i '' -e "s/^google-api-wrapper2 = \"[0-9].*/google-api-wrapper2 = \"$new_googleaiwrapper_version\"/" pyproject.toml
  git --no-pager diff
  # TODO Check if two lines modified or user should manually confirm if git diff looks okay
  poetry version patch
  poetry update
  commit-version-bump "update version of packages: python-common-lib, google-api-wrapper2"

  echo "Publishing $PROJ_NAME_YARN_DEV_TOOLS..."
  poetry build && poetry publish
}

function myrepos-upgrade-pythoncommons() {
  GIT_PUSH=1
  show-changes

  reset # TODO Make this depend on flag like 'GIT_PUSH'

  bump-pythoncommons-version
  if [[ "$?" -ne 0 ]]; then
    return 1
  fi

  bump-googleapiwrapper-version
  if [[ "$?" -ne 0 ]]; then
    return 1
  fi

  update-package-versions-in-yarndevtools
  if [[ "$?" -ne 0 ]]; then
    return 1
  fi
}


function myrepos-upgrade-yarndevtools() {
  GIT_PUSH=0
  show-changes
  if [[ "$?" -ne 0 ]]; then
    return 1
  fi

  reset
  bump-yarndevtools-version
  if [[ "$?" -ne 0 ]]; then
    return 1
  fi
}
