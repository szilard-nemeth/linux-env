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

# The next line updates PATH for the Google Cloud SDK.                                                                   
if [ -f '/Users/szilardnemeth/google-cloud-sdk/path.bash.inc' ]; then . '/Users/szilardnemeth/google-cloud-sdk/path.bash.inc'; fi
                                                                                                                         
# The next line enables shell command completion for gcloud.                                                             
if [ -f '/Users/szilardnemeth/google-cloud-sdk/completion.bash.inc' ]; then . '/Users/szilardnemeth/google-cloud-sdk/completion.bash.inc'; fi