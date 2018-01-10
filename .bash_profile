if [ -f ~/.bashrc ]; then
   source ~/.bashrc
fi

export PATH="/usr/local/opt/protobuf@2.5/bin:$PATH"
JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk1.8.0_151.jdk/Contents/Home/
export JAVA_HOME

[ -f /usr/local/etc/bash_completion ] && . /usr/local/etc/bash_completion