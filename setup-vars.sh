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
# Prepend rbenv shims so `ruby`, `gem`, `bundle` resolve to the rbenv-managed
# Ruby before the macOS system Ruby at /usr/bin. add_to_path_directly appends,
# not prepends, so we cannot use it here — the shim path MUST come first, or
# /usr/bin/ruby wins the lookup and the whole rbenv indirection is defeated.
export PATH="$HOME/.rbenv/shims:$PATH"
# `gem environment gempath` runs against whichever gem is first on PATH — with
# rbenv shims prepended above, this now yields the rbenv gempaths, so their
# `bin` dirs get added and gem-installed executables (colorls, etc.) are
# reachable directly. The 2>/dev/null suppresses the "No such file or
# directory" warning `find` prints when a listed path was removed out-of-band
# (e.g. `~/.gem/ruby/2.6.0` after migrating off system Ruby).
add_to_path_directly $(find $(gem environment gempath | tr ':' '\n') -type d -name bin 2>/dev/null | tr '\n' ':')

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
# Where claude-session-exporter writes exported Claude Code transcripts.
# One subdir per project-slug (e.g. Users-snemeth-development-cloudera-cde-dex);
# see claude-sessions-recent / claude-sessions-cd in aliases/aliases.sh.
export CLAUDE_SESSIONS_DIR="${KB_PRIVATE_REPO}claude-sessions"
export PYTHON_COMMONS_REPO="$HOME/development/my-repos/python-commons/"
export YARNDEVTOOLS_REPO="$HOME/development/my-repos/yarn-dev-tools/"