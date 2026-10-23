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

eval "$(/opt/homebrew/bin/brew shellenv)"


# initialize asdf
export ASDF_DIR="$(brew --prefix asdf)/libexec"
. "$ASDF_DIR/asdf.sh"