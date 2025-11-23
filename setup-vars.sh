#!/usr/bin/env bash
echo "Loading setup-vars.sh..."

#===================================
#Setup npm
export NODE_PATH='/usr/local/lib/node_modules'
NPM_PACKAGES="${HOME}/.npm-packages"
add_to_path_directly "$NPM_PACKAGES/bin"
# Unset manpath so we can inherit from /etc/manpath via the `manpath` command
unset MANPATH # delete if you already modified MANPATH elsewhere in your config
export MANPATH="$NPM_PACKAGES/share/man:$(manpath)"
#End of npm config
#===================================

#Setup Ruby
add_to_path_directly "$HOME/.rbenv/shims:$PATH"
add_to_path_directly $(find $(gem environment gempath | tr ':' '\n') -type d -name bin | tr '\n' ':')

# Add common bins to path
add_to_path_directly "$HOME/.local/bin"
#===================================

export MAVEN_OPTS="-Xmx1024m -XX:MaxPermSize=1024m"
export ANT_OPTS="-XX:PermSize=512m -XX:MaxPermSize=512m -Xmx1024m -Xms1024m"
export GIT_EDITOR='vim'
export MY_REPOS_DIR="$HOME/development/my-repos/"
export OTHER_REPOS_DIR="$HOME/development/other-repos/"
export FORKED_REPOS_DIR="$HOME/development/my-repos/fork"
export LINUXENV_DIR="$HOME/development/my-repos/linux-env/"
export KB_REPO="$HOME/development/my-repos/knowledge-base/"
export KB_PRIVATE_REPO="$HOME/development/my-repos/knowledge-base-private/"
export PYTHON_COMMONS_REPO="$HOME/development/my-repos/python-commons/"
export YARNDEVTOOLS_REPO="$HOME/development/my-repos/yarn-dev-tools/"