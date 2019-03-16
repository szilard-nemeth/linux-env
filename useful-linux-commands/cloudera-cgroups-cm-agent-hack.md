Location of CM agent service files: 
```
systemctl list-unit-files --type=service | grep agent
find / -iname "cloudera-scm-agent.service" 
---> /usr/lib/systemd/system/cloudera-scm-agent.service
/lib/systemd/system/cloudera-scm-agent.service
/opt/cloudera/cm-agent/bin/cm
```


1. Get CM agent pid:
```
cm_agent_pid=$(ps auxww | grep "/opt/cloudera/cm-agent/bin/cm agent" | grep -v grep | tr -s " " | cut -d " " -f2)
echo "CM agent pid: $cm_agent_pid"
```

2. Get CM agent's parent pid: 
Get parent pid: https://superuser.com/questions/150117/how-to-get-parent-pid-of-a-given-process-in-gnu-linux-from-command-line

```
cm_agent_ppid=$(ps -o ppid= -p $cm_agent_pid)
echo "CM agent parent pid: $cm_agent_ppid"
```

3. Echo cgroups of CM agent:

```
echo "Cgroups of cm agent: ";cat /proc/$cm_agent_pid/cgroup
```


Replace CM agent python files on remote host and restart CM agent
=================================================================
These files will be replaced: 
/opt/cloudera/cm-agent/lib/python2.7/site-packages/cmf/process.py
/opt/cloudera/cm-agent/lib/python2.7/site-packages/cmf/cgroups.py

1. 
```
cmf_dir="$HOME/development/cloudera/cmf"
local_dir="$HOME/Downloads/cgroupshack/"
remote_dir="/home/systest/cgroupshack/"
remote_cm_agent_dir="/opt/cloudera/cm-agent/lib/python2.7/site-packages/cmf/"
host="zsiegl-gpu-2.vpc.cloudera.com"; 
cd $cmf_dir; for i in `git st --porcelain | cut -d ' ' -f3`; do echo "Copying $i";cp $i $local_dir; done; rsync -a $local_dir systest@$host: && ssh root@$host "set -x;cp "$remote_dir/*.py" $remote_cm_agent_dir;service cloudera-scm-agent restart && service cloudera-scm-agent status"
```

2. Set permissions correctly:

```
sudo cp /home/systest/cgroupshack/*.py /opt/cloudera/cm-agent/lib/python2.7/site-packages/cmf/
sudo chown cloudera-scm:cloudera-scm /opt/cloudera/cm-agent/lib/python2.7/site-packages/cmf/process.py
sudo chown cloudera-scm:cloudera-scm /opt/cloudera/cm-agent/lib/python2.7/site-packages/cmf/cgroups.py
```

3. Restart CM agent:

```sudo service cloudera-scm-agent restart```

4. Check log file: 

```less /var/log/cloudera-scm-agent/cloudera-scm-agent.log```