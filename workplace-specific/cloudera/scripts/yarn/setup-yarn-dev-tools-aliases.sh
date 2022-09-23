#!/usr/bin/env bash

function setup-vars() {
    # HADOOP_DEV_DIR and CLOUDERA_HADOOP_ROOT need to be defined
    export UPSTREAM_HADOOP_DIR=${HADOOP_DEV_DIR}
    export DOWNSTREAM_HADOOP_DIR=${CLOUDERA_HADOOP_ROOT}

    # Replace this with the dir of your choice
    export YARNDEVTOOLS_ROOT="$HOME/.yarndevtools"
}

function yarndevtools() {
    ORIG_PYTHONPATH=$PYTHONPATH
    unset PYTHONPATH

    source $YARNDEVTOOLS_ROOT/venv/bin/activate
    export HADOOP_DEV_DIR && export CLOUDERA_HADOOP_ROOT
    python -m yarndevtools.yarn_dev_tools "$@"

    # Cleanup
    deactivate
    PYTHONPATH=$ORIG_PYTHONPATH
}

function print-yarn-dev-tools-aliases {
  echo "============================================YARNDEVTOOLS SETUP============================================\n\n"
  echo "CLOUDERA_HADOOP_ROOT=$CLOUDERA_HADOOP_ROOT"
  echo "HADOOP_DEV_DIR=$HADOOP_DEV_DIR"
  echo "YARN_DEV_TOOLS_DIR=$YARN_DEV_TOOLS_DIR"
  echo "YARN_DEV_TOOLS_ENV=export HADOOP_DEV_DIR;export CLOUDERA_HADOOP_ROOT"
  echo "Aliases: "
  alias | grep -e '^yarn-.*='
  echo "\n"
  echo "============================================YARNDEVTOOLS SETUP============================================"
}

function setup-aliases-yarndevtools-source {
  YARN_DEV_TOOLS_DIR="$HOME/development/my-repos/yarn-dev-tools"
  YARN_DEV_TOOLS_ENV="export HADOOP_DEV_DIR;export CLOUDERA_HADOOP_ROOT"

  alias yarn-backport-c6="cd $YARN_DEV_TOOLS_DIR;$YARN_DEV_TOOLS_ENV; poetry run exec-yarndevtools BACKPORT_C6; popd"
  alias yarn-save-patch="cd $YARN_DEV_TOOLS_DIR;$YARN_DEV_TOOLS_ENV; poetry run exec-yarndevtools SAVE_PATCH; popd"
  alias yarn-create-review-branch="cd $YARN_DEV_TOOLS_DIR;$YARN_DEV_TOOLS_ENV; poetry run exec-yarndevtools CREATE_REVIEW_BRANCH; popd"
  alias yarn-upstream-commit-pr="cd $YARN_DEV_TOOLS_DIR;$YARN_DEV_TOOLS_ENV; poetry run exec-yarndevtools UPSTREAM_PR_FETCH; popd"
  alias yarn-diff-patches="cd $YARN_DEV_TOOLS_DIR;$YARN_DEV_TOOLS_ENV; poetry run exec-yarndevtools DIFF_PATCHES_OF_JIRA; popd"
  alias yarn-save-diff-as-patches="cd $YARN_DEV_TOOLS_DIR;$YARN_DEV_TOOLS_ENV; poetry run exec-yarndevtools SAVE_DIFF_AS_PATCHES; popd"
  alias yarn-get-umbrella-data="cd $YARN_DEV_TOOLS_DIR;$YARN_DEV_TOOLS_ENV; poetry run exec-yarndevtools FETCH_JIRA_UMBRELLA_DATA; popd"
  print-yarn-dev-tools-aliases
}

function setup-aliases-yarndevtools-package {
  YARN_DEV_TOOLS_ENV="export HADOOP_DEV_DIR;export CLOUDERA_HADOOP_ROOT"

  alias yarn-backport-c6="$YARN_DEV_TOOLS_ENV; yarndevtools BACKPORT_C6; popd"
  alias yarn-save-patch="$YARN_DEV_TOOLS_ENV; yarndevtools SAVE_PATCH; popd"
  alias yarn-create-review-branch="$YARN_DEV_TOOLS_ENV; yarndevtools CREATE_REVIEW_BRANCH; popd"
  alias yarn-upstream-commit-pr="$YARN_DEV_TOOLS_ENV; yarndevtools UPSTREAM_PR_FETCH; popd"
  alias yarn-diff-patches="$YARN_DEV_TOOLS_ENV; yarndevtools DIFF_PATCHES_OF_JIRA; popd"
  alias yarn-save-diff-as-patches="$YARN_DEV_TOOLS_ENV; yarndevtools SAVE_DIFF_AS_PATCHES; popd"
  alias yarn-get-umbrella-data="$YARN_DEV_TOOLS_ENV; yarndevtools FETCH_JIRA_UMBRELLA_DATA; popd"
  print-yarn-dev-tools-aliases
}

setup-vars
setup-aliases-yarndevtools-package