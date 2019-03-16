File operations (find / ls)
===========================
1. Extract files from jar file to console, print with separator

```find . -iname "*<somename>.jar" -exec sh -c "echo file: {}; unzip -p {} META-INF/services/javax.ws.rs.ext.MessageBodyWriter; echo '$\n\n'" \;```

2. List recursive, show depth: 

```ls /export/apps -R | grep ":$" | sed -e 's/:$//' -e 's/[^-][^\/]*\//--/g' -e 's/^/   /' -e 's/-/|/'```


3. Remove multiple files: 

```find . -iname *versionsBackup -print0 | xargs -0 rm```

4. Find for specific file types, grep in them:

```find / -regex ".*\.\(xml\|txt\|ini\|cfg\)" 2>/dev/null | xargs grep <string>```

5. Find multiple files, with exclusion of filenames:

```find /opt/hadoop/share/hadoop/yarn/ -iname 'hadoop-yarn-server*nodemanager*' ! -iname "*test*.jar" ! -iname "*sources*jar" -printf "unzip -c %p | grep -q '' && echo %p\n" | sh```


Jar commands
============

1. Extract specific file from jar file:

```jar xf <jarfile> META-INF/services/javax.ws.rs.ext.MessageBodyWriter```

2. List filenames of jar file: 

```unzip -Z1 <jarfile> | less | grep "about"```

3. List files in jar file: 

```jar tf <jarfile>```

4. unzip a file from jar file: 

```unzip -p <jarfile> org/apache/hadoop/yarn/api/protocolrecords/ResourceTypes.class```

Networking commands 
===================

1. Restart network manager:

```sudo service network-manager restart``` OR

```sudo service networking restart``` OR

```sudo /etc/init.d/network restart```

2. Bring wlan interface down & up:

```
ifconfig wlan0 down
ifconfig wlan0 up
```

3. Ask for new IP (new DHCP lease): 

```sudo dhclient -v wlan0```


Linux version commands 
======================
Find out linux version (method 1):

```cat /etc/*-release```

Find out linux version (method 2):

```lsb_release -a```

Find out linux version (method 3):

```uname -a```

Find out linux version (method 4):

```cat /proc/version```



Rsync / SSH commands
====================

1. Rsync whole folder to remote machine:

```rsync -a <dir> <user>@$<host>:```

2. Open a SSH tunnel: https://plenz.com/tunnel-everything.php

```ssh -NL 2345:127.0.0.1:8000 <user>@<host>```


Text manipulation commands
==========================

1. Replace spaces with newlines (tr): 

```cat /proc/19368/environ | tr '\0' '\n'```

2. Grep for multiple patterns: 

```grep "<pattern1> \|<pattern2>" -A2 <inputfile>```

3. Format timestamps (epoch): 

```for i in `ls -tr1 | sort | cut -d'.' -f1`; do echo $i.json `date -f "%s" -j $(($i / 1000 - 9*3600)) "+%Y%m%d-%H%M%S"`; done```


Other tricks
============

1. Trick: Watch directory contents for changes (cgroup)

```while true; do date +'%H:%M:%S:%N' | tee -a /tmp/tmp2 && find /sys/fs/cgroup | grep hadoop 2>&1 | tee -a /tmp/tmp2; sleep 1; done```