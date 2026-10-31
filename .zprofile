# Startup profiling, off by default (also defined in .zshrc for non-login shells):
#   LINUXENV_ZPROF=1 zsh -li -c exit     per-function profile written to /tmp/zprof.txt
#   LINUXENV_PROFILE=1 zsh -li -c exit   elapsed ms per startup section, on stderr
[[ -n $LINUXENV_ZPROF ]] && zmodload zsh/zprof
if [[ -n $LINUXENV_PROFILE ]]; then
    zmodload zsh/datetime
    typeset -g _LENV_T0=$EPOCHREALTIME
fi
function _lenv_t {
    [[ -n $LINUXENV_PROFILE ]] || return 0
    local now=$EPOCHREALTIME
    printf '%8.1fms %+8.1fms  %s\n' $(( (now - _LENV_T0) * 1000 )) $(( (now - ${_LENV_TL:-$_LENV_T0}) * 1000 )) "$1" >&2
    typeset -g _LENV_TL=$now
}

function setup-java {
    if hash /usr/libexec/java_home &>/dev/null; then
        JAVA_HOME=$(/usr/libexec/java_home)
        export JAVA_HOME
    else
        echo "Cannot set JAVA_HOME as JDK was not found!"
    fi
}

echo "$(date) -- .zprofile executed" >> $HOME/.zprofile.log

if [[ -f ~/.zshrc ]]; then
   #source ~/.zshrc
fi

# Output cache for slow init commands; the file is deployed by setup-env.sh, so it is missing on the very first shell
[[ -f ~/.linuxenv/scripts/startup-cache.sh ]] && . ~/.linuxenv/scripts/startup-cache.sh

if ! { (( $+functions[linuxenv-cached-source] )) && linuxenv-cached-source brew-shellenv /opt/homebrew/bin/brew /opt/homebrew/bin/brew shellenv; }; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi
_lenv_t "zprofile: brew shellenv"


# initialize asdf
export ASDF_DIR="$(brew --prefix asdf)/libexec"
. "$ASDF_DIR/asdf.sh"
_lenv_t "zprofile: asdf"