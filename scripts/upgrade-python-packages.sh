#!/usr/bin/env bash
YARN_DEV_TOOLS_DIR="$HOME/development/my-repos/yarn-dev-tools"
PYTHON_COMMONS_DIR="$HOME/development/my-repos/python-commons"
GOOGLE_API_WRAPPER_DIR="$HOME/development/my-repos/google-api-wrapper/"
BACKUP_MANAGER_DIR="$HOME/development/my-repos/backup-manager/"
PROJ_NAME_YARN_DEV_TOOLS="yarndevtools"
PROJ_NAME_PYTHON_COMMONS="pythoncommons"
PROJ_NAME_GOOGLE_API_WRAPPER="googleapiwrapper"
PROJ_NAME_BACKUP_MANAGER="backup-manager"

SKIP_POETRY_PUBLISH=0
UPGRADE_PYTHON_PACKAGE_GOOGLEAPIWRAPPER=0
UPGRADE_PYTHON_PACKAGE_PYTHONCOMMONS=0

function remove-links-with-target() {
  local lnk_target_to_remove_1="$1"
  local lnk_target_to_remove_2="$2"

  cd $YARN_DEV_TOOLS_DIR
  find . -type l |
  while IFS= read -r lnkname;
  do
    lnk_target=$(readlink "$lnkname")
    if [[ "$lnk_target" =~ "^$lnk_target_to_remove_1$" || "$lnk_target" =~ "^$lnk_target_to_remove_2$" ]]; then
      echo "Removing link: $lnkname -> $lnk_target"
      rm -- "$lnkname"
    fi
  done
}

function cleanup-yarndevtools-links() {
  remove-links-with-target "/tmp/.*" "/home/cdsw/snemeth-dev-projects.*"
}


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
  local git_branch=$2
  
  cd $repo_dir
  current_br=$(git rev-parse --abbrev-ref HEAD)

  if [[ "$git_branch" != "$current_br" ]]; then
    echo "Current branch is not $git_branch in $(pwd)! Exiting..."
    return 1
  fi

  if [[ ! -z $(git status -s) ]]; then
    echo "There are changed files in $repo_dir. Please remove changes and re-run this script"
    return 2
  fi

  if [[ ! -z $(git --no-pager log origin/$git_branch..HEAD) ]]; then
    echo "There are unpushed commits in $repo_dir. Please push or remove these commits and re-run this script"
    return 2
  fi
}

function show-changes-all {
  echo "UPGRADE_PYTHON_PACKAGES_BRANCH=$UPGRADE_PYTHON_PACKAGES_BRANCH"
  echo "UPGRADE_PYTHON_PACKAGES_DEPENDENCY_BRANCH=$UPGRADE_PYTHON_PACKAGES_DEPENDENCY_BRANCH"
  _show-changes-pythoncommons
  _show-changes-googleapiwrapper
  _show-changes-yarndevtools
  if [[ "$?" -ne 0 ]]; then
    echo "Uncommitted changes detected, see messages above"
    return 1
  fi
}

function _show-changes-pythoncommons {
  echo "Listing changes in $PYTHON_COMMONS_DIR" && cd $PYTHON_COMMONS_DIR && git --no-pager log origin/$UPGRADE_PYTHON_PACKAGES_DEPENDENCY_BRANCH..HEAD
  check-git-changes $PYTHON_COMMONS_DIR $UPGRADE_PYTHON_PACKAGES_DEPENDENCY_BRANCH
  if [[ "$?" -ne 0 ]]; then
    echo "Uncommitted changes detected in dir: $PYTHON_COMMONS_DIR"
    return 1
  fi
}

function _show-changes-googleapiwrapper {
  echo "Listing changes in $GOOGLE_API_WRAPPER_DIR" && cd $GOOGLE_API_WRAPPER_DIR && git --no-pager log origin/$UPGRADE_PYTHON_PACKAGES_DEPENDENCY_BRANCH..HEAD
  check-git-changes $GOOGLE_API_WRAPPER_DIR $UPGRADE_PYTHON_PACKAGES_DEPENDENCY_BRANCH
  if [[ "$?" -ne 0 ]]; then
    echo "Uncommitted changes detected in dir: $GOOGLE_API_WRAPPER_DIR"
    return 1
  fi
}

function _show-changes-yarndevtools {
  echo "Listing changes in $YARN_DEV_TOOLS_DIR" && cd $YARN_DEV_TOOLS_DIR && git --no-pager log origin/$UPGRADE_PYTHON_PACKAGES_BRANCH..HEAD
  check-git-changes $YARN_DEV_TOOLS_DIR $UPGRADE_PYTHON_PACKAGES_BRANCH
  if [[ "$?" -ne 0 ]]; then
    echo "Uncommitted changes detected in dir: $YARN_DEV_TOOLS_DIR"
    return 1
  fi
}

function reset() {
  cd $PYTHON_COMMONS_DIR
  # TODO Show diff and ask confirmation before doing git reset --hard
  #git reset --hard origin/$UPGRADE_PYTHON_PACKAGES_BRANCH

  cd $GOOGLE_API_WRAPPER_DIR
  #git reset --hard origin/$UPGRADE_PYTHON_PACKAGES_BRANCH

  cd $YARN_DEV_TOOLS_DIR
  #git reset --hard origin/$UPGRADE_PYTHON_PACKAGES_BRANCH
}

function poetry-build-and-publish() {
  local project="$1"

  if [[ $SKIP_POETRY_PUBLISH -eq 0 ]]; then
    echo "Publishing $project_name..."
    poetry build && poetry publish
  else
    echo "Only building (Skip publishing) $project_name"
    poetry build
  fi

  ret=$?
  if [[ "$ret" -ne 0 ]]; then
    echo "Failed to build / publish $project. Skipping commit"
    # TODO should do git repo reset here (for specific project)
    return 1
  fi
}

function commit-version-bump() {
  commit_msg="$1"
  new_version="$2"
  echo "Committing version bump..."
  git commit -am "$commit_msg"

  if [[ $UPGRADE_PYTHON_PACKAGES_GIT_PUSH -eq 1 ]]; then
    # Push commit
    git push --dry-run

    # Push tag
    tag_name="$new_version"
    git tag $tag_name -a -m "Release created by shell script: $new_version"
    git push origin $tag_name --dry-run

    # Print info
    echo "========================[NOTICE]========================"
    echo "Execute these to check commit and push (simply copy-paste this block)"
    echo "cd `pwd`"
    echo "git --no-pager show -1"
    echo "git tag -l | grep $tag_name"
    echo "git push # push commit"
    echo "git push origin $tag_name # push tag"
    echo "========================[NOTICE]========================"
  else
    echo "Skipping git push"
  fi
}
  
function bump-project-version() {
  local project="$1"
  echo "Bumping version of $project"

  project_dir=`get-project-dir $project`

  if [[ "$?" -ne 0 ]]; then
    echo $project_dir
    return 1
  fi

  cd $project_dir
  current_version=$(poetry version --short)

  if [[ -z $current_version ]]; then
    echo "failed to parse current project version!"
    return 1
  fi

  echo "Current version of $project is: $current_version"

  poetry version patch
  git --no-pager diff

  poetry-build-and-publish $project
  if [[ "$?" -ne 0 ]]; then
    return 1
  else
    new_version=$(poetry version --short)
    commit-version-bump "Bump version to $new_version (patch)" "$new_version"
  fi
}

function bump-pythoncommons-version() {
  bump-project-version "$PROJ_NAME_PYTHON_COMMONS"
  if [[ "$?" -ne 0 ]]; then
    echo "Failed to bump version of $PROJ_NAME_PYTHON_COMMONS"
    return 1
  fi
}

function bump-googleapiwrapper-version() {
  # Wherever bump-pythoncommons-version is called, new_pythoncommons_version is parsed again to a valid version
  # If it is empty, no need to update pythoncommons here
  if [[ ! -z "$new_pythoncommons_version" ]] ; then
    echo "Updating $PROJ_NAME_PYTHON_COMMONS" for "$PROJ_NAME_GOOGLE_API_WRAPPER"
    cd $GOOGLE_API_WRAPPER_DIR
    # NOTE: Apparently, the command below does not work, in contrary to the documentation:
    # poetry add python-common-lib==$new_pythoncommons_version
    # Use sed to upgrade the package's version
    sed -i '' -e "s/^python-common-lib = \"[0-9].*/python-common-lib = \"$new_pythoncommons_version\"/" pyproject.toml
  else
    echo "Not updating $PROJ_NAME_PYTHON_COMMONS" for "$PROJ_NAME_GOOGLE_API_WRAPPER"
  fi
  

  bump-project-version "$PROJ_NAME_GOOGLE_API_WRAPPER"
  if [[ "$?" -ne 0 ]]; then
    echo "Failed to bump version of $PROJ_NAME_GOOGLE_API_WRAPPER"
    return 1
  fi
}

function bump-yarndevtools-version() {
  bump-project-version $PROJ_NAME_YARN_DEV_TOOLS
  if [[ "$?" -ne 0 ]]; then
    echo "Failed to bump version of $PROJ_NAME_YARN_DEV_TOOLS"
    return 1
  fi
}

function update-package-versions-in-yarndevtools() {
  _update-package-versions-in-project $PROJ_NAME_YARN_DEV_TOOLS $YARN_DEV_TOOLS_DIR
  if [[ "$?" -ne 0 ]]; then
    echo "Failed to upgrade package dependencies"
    return 1
  fi
}

function update-package-versions-in-backup-manager() {
  _update-package-versions-in-project $PROJ_NAME_BACKUP_MANAGER $BACKUP_MANAGER_DIR
  if [[ "$?" -ne 0 ]]; then
    echo "Failed to upgrade package dependencies"
    return 1
  fi
}

function _update-package-versions-in-project {
  local project_name=$1
  local project_dir=$2

  cd $project_dir
  if [[ ! -z $(git status -s) ]]; then
    echo "Uncommitted changes detected in $project_dir. Exiting.."
    return 1
  fi

  echo "UPDATING PACKAGE VERSIONS FOR PROJECT: $project_name"
  
  if [[ $UPGRADE_PYTHON_PACKAGE_GOOGLEAPIWRAPPER -eq 0 ]] && [[ $UPGRADE_PYTHON_PACKAGE_GOOGLEAPIWRAPPER -eq 0 ]]; then
    echo "No package will be updated, invalid config!"
    return 1
  fi

  local commit_msg="update version of packages: "
  if [[ $UPGRADE_PYTHON_PACKAGE_GOOGLEAPIWRAPPER -eq 1 ]]; then
    echo "Increasing package version for dependency: $PROJ_NAME_GOOGLE_API_WRAPPER"
    sed -i '' -e "s/^google-api-wrapper2 = \"[0-9].*/google-api-wrapper2 = \"$new_googleapiwrapper_version\"/" pyproject.toml
    commit_msg+="google-api-wrapper2"
  fi

  if [[ $UPGRADE_PYTHON_PACKAGE_PYTHONCOMMONS -eq 1 ]]; then
    echo "Increasing package version for dependency: $PROJ_NAME_PYTHON_COMMONS"
    sed -i '' -e "s/^python-common-lib = \"[0-9].*/python-common-lib = \"$new_pythoncommons_version\"/" pyproject.toml
    commit_msg+=", python-common-lib"
  fi

  
  echo "Showing git diff after dependency upgrades..."
  git --no-pager diff
  # TODO Check if two lines modified or user should manually confirm if git diff looks okay
 

  poetry update
  if [[ "$?" -ne 0 ]]; then
    echo "Failed to build $project_name"

    echo "CURRENT PROJECT: $project_name"
    echo "CURRENT PROJECT DIR: `pwd`"
    echo "CURRENT PROJECT VERSION: $(cd $project_dir && poetry version --short)"
    
    echo "PRINTING DEPENDENCY VERSIONS (AFTER CHANGE)"
    # NOTE: poetry show exits with 1 if the dependency versions are not correct
    # Just use grep here
    # poetry show | grep "google-api-wrapper2\|python-common-lib"
    # poetry show python-common-lib
    # poetry show google-api-wrapper2
    grep "google-api-wrapper2\|python-common-lib" pyproject.toml

    echo "====================================================="
    echo "PROJECT: $PROJ_NAME_PYTHON_COMMONS"
    echo "PROJECT VERSION: $(cd $PYTHON_COMMONS_DIR && poetry version --short)"
    

    echo "====================================================="
    echo "PROJECT: $PROJ_NAME_GOOGLE_API_WRAPPER"
    echo "PROJECT VERSION: $(cd $GOOGLE_API_WRAPPER_DIR && poetry version --short)"
    echo "PRINTING DEPENDENCY VERSIONS"
    # echo "$(cd $GOOGLE_API_WRAPPER_DIR && poetry show python-common-lib)"
    echo "$(cd $GOOGLE_API_WRAPPER_DIR && grep "python-common-lib" pyproject.toml)"
    

    echo "Restoring changes of pyproject.toml"
    git restore pyproject.toml
    return 1
  fi

  # Only do 'poetry version patch' if poetry update was successful
  poetry version patch
  echo "Showing git diff after poetry version upgrade..."
  git --no-pager diff


  # Need to have this symlink hack for now :(
  # Temporarily remove symlinks
  ## Related github issues:
  # https://github.com/python-poetry/poetry/issues/3589
  # https://github.com/python-poetry/poetry/issues/4697
  # https://github.com/python-poetry/poetry/issues/1998
  rm modules/trello-backup/config.py


  # TODO Can be refactored to use poetry-build-and-publish
  # ================================
      echo "Building $project_name..."
      poetry build
      if [[ "$?" -ne 0 ]]; then
        echo "Failed to build $project_name"
        return 1
      fi

      if [[ $SKIP_POETRY_PUBLISH -eq 0 ]]; then
        echo "Publishing $project_name..."
        poetry publish
      else
        echo "Skip publishing $project_name"
      fi
      
      if [[ "$?" -ne 0 ]]; then
        echo "Failed to publish $project_name"
        return 2
      else
        new_version=$(poetry version --short)
        commit-version-bump $commit_msg "$new_version"

        # Add back original symlinks
        ln -s ~/development/my-repos/project-data/input-data/backup-manager/trello-backup/config.py modules/trello-backup/config.py
      fi
  # END OF TODO
  # ================================
}

function myrepos-upgrade-pythoncommons-in-yarndevtools() {
  UPGRADE_PYTHON_PACKAGES_GIT_PUSH=1
  cleanup-yarndevtools-links
  show-changes-all
  if [[ "$?" -ne 0 ]]; then
    return 1
  fi

  # reset # TODO Make this depend on flag like 'UPGRADE_PYTHON_PACKAGES_GIT_PUSH'

  bump-pythoncommons-version
  if [[ "$?" -ne 0 ]]; then
    return 1
  fi
  new_pythoncommons_version=$(cd $PYTHON_COMMONS_DIR && echo $(poetry version --short))

  # TODO this is wrong, it should not be just bumped, it should match the version of googleapiwrapper from pythoncommons pyproject.toml to avoid: 
  # ERROR: Cannot install yarn-dev-tools and yarn-dev-tools==1.1.13 because these package versions have conflicting dependencies.
# The conflict is caused by:
#     yarn-dev-tools 1.1.13 depends on python-common-lib==1.0.8
#     google-api-wrapper2 1.0.4 depends on python-common-lib==1.0.4

  bump-googleapiwrapper-version
  if [[ "$?" -ne 0 ]]; then
    return 1
  fi
  new_googleapiwrapper_version=$(cd $GOOGLE_API_WRAPPER_DIR && echo $(poetry version --short))
  

  UPGRADE_PYTHON_PACKAGE_GOOGLEAPIWRAPPER=1
  UPGRADE_PYTHON_PACKAGE_PYTHONCOMMONS=1
  update-package-versions-in-yarndevtools
  unset-all-package-upgrade-vars  

  if [[ "$?" -ne 0 ]]; then
    return 1
  fi
}

function myrepos-upgrade-googleapiwrapper-in-yarndevtools() {
  UPGRADE_PYTHON_PACKAGES_GIT_PUSH=1
  #UPGRADE_PYTHON_PACKAGES_BRANCH="cloudera-mirror-version" # only used in _show-changes-yarndevtools
  UPGRADE_PYTHON_PACKAGES_DEPENDENCY_BRANCH="master"

  cleanup-yarndevtools-links
  _show-changes-googleapiwrapper
  if [[ "$?" -ne 0 ]]; then
    return 1
  fi

  # reset # TODO Make this depend on flag like 'UPGRADE_PYTHON_PACKAGES_GIT_PUSH'

  bump-googleapiwrapper-version
  if [[ "$?" -ne 0 ]]; then
    return 1
  fi
  new_googleapiwrapper_version=$(cd $GOOGLE_API_WRAPPER_DIR && echo $(poetry version --short))


  UPGRADE_PYTHON_PACKAGE_GOOGLEAPIWRAPPER=1
  update-package-versions-in-yarndevtools
  unset-all-package-upgrade-vars  

  if [[ "$?" -ne 0 ]]; then
    return 1
  fi
}

function unset-all-package-upgrade-vars {
  UPGRADE_PYTHON_PACKAGE_GOOGLEAPIWRAPPER=0
  UPGRADE_PYTHON_PACKAGE_PYTHONCOMMONS=0
}

function myrepos-upgrade-pythoncommons-in-backup-manager() {
  # TODO unify logic with myrepos-upgrade-pythoncommons-in-yarndevtools
  UPGRADE_PYTHON_PACKAGES_GIT_PUSH=1
  UPGRADE_PYTHON_PACKAGES_BRANCH="cloudera-mirror-version" # only used in _show-changes-yarndevtools
  UPGRADE_PYTHON_PACKAGES_DEPENDENCY_BRANCH="master"

  _show-changes-pythoncommons
  _show-changes-googleapiwrapper
  
  if [[ "$?" -ne 0 ]]; then
    echo "Uncommitted changes detected, see messages above"
    return 1
  fi

  #reset # TODO Make this depend on flag like 'UPGRADE_PYTHON_PACKAGES_GIT_PUSH'

  bump-pythoncommons-version
  if [[ "$?" -ne 0 ]]; then
    return 1
  fi
  new_pythoncommons_version=$(cd $PYTHON_COMMONS_DIR && echo $(poetry version --short))

  bump-googleapiwrapper-version
  if [[ "$?" -ne 0 ]]; then
    return 1
  fi
  new_googleapiwrapper_version=$(cd $GOOGLE_API_WRAPPER_DIR && echo $(poetry version --short))

  SKIP_POETRY_PUBLISH=1
  remove-links-with-target "/tmp/.*" "$HOME/development/my-repos/project-data/input-data/backup-manager.*"

  UPGRADE_PYTHON_PACKAGE_GOOGLEAPIWRAPPER=1
  UPGRADE_PYTHON_PACKAGE_PYTHONCOMMONS=1
  update-package-versions-in-backup-manager
  unset-all-package-upgrade-vars

  if [[ "$?" -ne 0 ]]; then
    return 1
  fi
}


function myrepos-release-yarndevtools() {
  UPGRADE_PYTHON_PACKAGES_GIT_PUSH=1
  UPGRADE_PYTHON_PACKAGES_BRANCH="cloudera-mirror-version" # only used in _show-changes-yarndevtools
  UPGRADE_PYTHON_PACKAGES_DEPENDENCY_BRANCH="master"
  
  cleanup-yarndevtools-links
  show-changes-all
  if [[ "$?" -ne 0 ]]; then
    return 1
  fi

  reset
  bump-yarndevtools-version
  if [[ "$?" -ne 0 ]]; then
    return 1
  fi
  new_yarndevtools_version=$(cd $YARN_DEV_TOOLS_DIR && echo $(poetry version --short))
  echo "Newly released version of $PROJ_NAME_YARN_DEV_TOOLS: $new_yarndevtools_version"
}
