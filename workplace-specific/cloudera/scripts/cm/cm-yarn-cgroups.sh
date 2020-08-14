#!/usr/bin/env bash

####Print pids with details
for pid in "${pids[@]}"; do echo "Found pid of MRAppMaster java process: $pid"; done
for pid in "${pids[@]}"; do echo "Process details for: $pid" && ps auxww | grep $pid; echo -e "\n\n"; done

####Get pid of container's java process
ps auxww | grep MRAppMaster | tr -s ' ' | cut -d' ' -f2 > /tmp/psresult
pgrep java > /tmp/java_procs
pids=($(comm -12 <(sort /tmp/psresult) <(sort /tmp/java_procs)))
for pid in "${pids[@]}"; do echo "cgroups of pid: $pid" && cat /proc/$pid/cgroup; echo -e "\n\n"; done


####Get cgroup of pid
for pid in "${pids[@]}"; do echo "Querying systemctl status of pid: $pid" && systemctl status $pid | grep -i cgroup; echo -e "\n\n";done


for pid in "${pids[@]}"; do echo "cat /proc/<pid>/cgroup of pid: $pid" && cat /proc/$pid/cgroup; echo -e "\n\n";done

#Store cpu_cgroup
cpu_cgroup=$(cat /proc/$pid/cgroup | grep cpuacct | cut -d ':' -f3)

####Verify if container java process is placed under cgroup: 259-yarn-NODEMANAGER
for pid in "${pids[@]}"; do echo "Printing /sys/fs/cgroup/cpu,cpuacct info for pid: $pid" && cat /sys/fs/cgroup/cpu,cpuacct/$cpu_cgroup/tasks | grep $pid; echo -e "\n\n";done

#List cgroups for CPU
for pid in "${pids[@]}"; do echo "Grepping systemd-cgls cpu for pid: $pid" && systemd-cgls cpu | grep $pid; echo -e "\n\n";done


#List cgroups for memory
for pid in "${pids[@]}"; do echo "Grepping systemd-cgls memory for pid: $pid" && systemd-cgls memory | grep $pid; echo -e "\n\n";done


####Verify that NODEMANAGER cgroup has correct values for CPU share: 40
cat /sys/fs/cgroup//cpu,cpuacct/$cpu_cgroup/cpu.shares
cgget -g cpu $cpu_cgroup