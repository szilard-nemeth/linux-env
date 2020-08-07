#!/usr/bin/env bash
echo "Loading setup-vars.sh..."

export MAVEN_OPTS="-Xmx1024m -XX:MaxPermSize=1024m"
export ANT_OPTS="-XX:PermSize=512m -XX:MaxPermSize=512m -Xmx1024m -Xms1024m"
export GIT_EDITOR='vim'

#Start of npm config
export NODE_PATH='/usr/local/lib/node_modules'
NPM_PACKAGES="${HOME}/.npm-packages"

PATH="$NPM_PACKAGES/bin:$PATH"

#Ruby
PATH="$HOME/.rbenv/shims:$PATH"
PATH=$(find $(gem environment gempath | tr ':' '\n') -type d -name bin | tr '\n' ':'):$PATH 

# Unset manpath so we can inherit from /etc/manpath via the `manpath` command
unset MANPATH # delete if you already modified MANPATH elsewhere in your config
export MANPATH="$NPM_PACKAGES/share/man:$(manpath)"
#End of npm config

export KB_REPO="$HOME/development/my-repos/knowledge-base/"
export KB_PRIVATE_REPO="$HOME/development/my-repos/knowledge-base-private/"