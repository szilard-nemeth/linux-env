if [ -f ~/.bashrc ]; then
   source ~/.bashrc
fi

export PATH="/usr/local/opt/protobuf@2.5/bin:$PATH"

if hash /usr/libexec/java_home &>/dev/null; then
    JAVA_HOME=$(/usr/libexec/java_home)
    export JAVA_HOME
else
    echo "Cannot set JAVA_HOME as JDK was not found!"
fi

[ -f /usr/local/etc/bash_completion ] && . /usr/local/etc/bash_completion