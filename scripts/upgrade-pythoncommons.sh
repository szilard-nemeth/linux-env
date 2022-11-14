#!/usr/bin/env bash
YARN_DEV_TOOLS_DIR="$HOME/development/my-repos/yarn-dev-tools"
PYTHON_COMMONS_DIR="$HOME/development/my-repos/python-commons"
GOOGLE_API_WRAPPER_DIR="$HOME/development/my-repos/google-api-wrapper/"

function show-changes() {
  echo "Changes in $PYTHON_COMMONS_DIR" && cd $PYTHON_COMMONS_DIR && git --no-pager log origin/master..HEAD/Users/snemeth/development/my-repos/yarn-dev-tools
  echo "Changes in $GOOGLE_API_WRAPPER_DIR" && cd $GOOGLE_API_WRAPPER_DIR && git --no-pager log origin/master..HEAD
  echo "Changes in $YARN_DEV_TOOLS_DIR" && cd $YARN_DEV_TOOLS_DIR && git --no-pager reset --hard origin/master
}

function reset() {
  cd $PYTHON_COMMONS_DIR
  git reset --hard origin/master

  cd $GOOGLE_API_WRAPPER_DIR
  git reset --hard origin/master

  cd $YARN_DEV_TOOLS_DIR
  git reset --hard origin/master
}

function commit-version-bump() {
  commit_msg="$1"
  echo "Committing version bump..."
  git commit -am "\"$commit_msg\""
  if [[ $GIT_PUSH -eq 1 ]]; then
    git push
  fi
}

function check-git-changes() {
  current_br=$(git rev-parse --abbrev-ref HEAD)
  if [[ "master" != "$current_br" ]]; then
    echo "Current branch is not master in $(pwd)! Exiting..."
    exit 1
  fi

  if [[ ! -z $(git status -s) ]]; then
    echo "There are changed files in $PYTHON_COMMONS_DIR. Please remove changes and rerun this script!"
    exit 2
  fi
}

function bump-pythoncommons-version() {
  echo "Bumping version of: pythoncommons"
  check-git-changes

  cd $PYTHON_COMMONS_DIR
  current_version=$(poetry version --short)
  echo "Current version of python-commons is: $current_version"

  poetry version patch
  commit-version-bump "bump version (patch)"

  echo "Publishing pythoncommons..."
  poetry build && poetry publish
  new_pythoncommons_version=$(poetry version --short)
}

function bump-googleapiwrapper-version() {
  echo "Bumping version of: googleapiwrapper"
  check-git-changes

  cd $GOOGLE_API_WRAPPER_DIR
  # NOTE: Apparently, the command below does not work, in contrary to the documentation:
  # poetry add python-common-lib==$new_pythoncommons_version
  # Use sed to upgrade the package's version
  sed -i '' -e "s/^python-common-lib = \"[0-9].*/python-common-lib = \"$new_pythoncommons_version\"/" pyproject.toml
  git --no-pager diff
  poetry version patch
  commit-version-bump "bump version (patch)"

  echo "Publishing google-api-wrapper..."
  poetry build && poetry publish
  new_googleaiwrapper_version=$(poetry version --short)
}

function increase-package-versions-in-yarndevtools() {
  echo "yarndevtools: Increasing package versions for: googleapiwrapper, pythoncommons"
  cd $YARN_DEV_TOOLS_DIR
  sed -i '' -e "s/^python-common-lib = \"[0-9].*/python-common-lib = \"$new_pythoncommons_version\"/" pyproject.toml
  sed -i '' -e "s/^google-api-wrapper2 = \"[0-9].*/google-api-wrapper2 = \"$new_googleaiwrapper_version\"/" pyproject.toml
  git --no-pager diff
  poetry version patch
  poetry update
  commit-version-bump "increase version of packages: python-common-lib, google-api-wrapper2"

  echo "Publishing yarn-dev-tools..."
  poetry build && poetry publish
}

function myrepos-upgrade-pythoncommons() {
  GIT_PUSH=1
  show-changes
  reset
  bump-pythoncommons-version
  bump-googleapiwrapper-version
  increase-package-versions-in-yarndevtools
}
