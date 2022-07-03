set -x
APP_ID="application_$1"
INVESTIGATION_ID=$2
TARGET_DIR=~/Downloads/_work/COMPX-8334/investigation_$INVESTIGATION_ID/yarntest_snemeth/
mkdir -p $TARGET_DIR
CLOUDBREAK_KEY=~/.ssh/ycloud_priv_key
NM_IPS=(172.27.19.135 172.27.11.65 172.27.53.65 172.27.89.71)
SSH_USER=cloudbreak
USR=cloudbreak
RESULT_DIR_ON_REMOTE_HOST=$USR/yarntest_snemeth
LOG_TAR_GZ_NAME=$APP_ID-logs.tar.gz
LOG_ROOT_REMOTE="/hadoopfs/root1/nodemanager/log/"

for IP in "${NM_IPS[@]}"; do
  ssh $IP -l $SSH_USER -i $CLOUDBREAK_KEY "mkdir -p $RESULT_DIR_ON_REMOTE_HOST"
  #tar is capable of tarring multiple dirs into one archive -> https://www.linuxquestions.org/questions/linux-newbie-8/tar-multiple-directories-into-one-file-880881/
  ssh $IP -l $SSH_USER -i $CLOUDBREAK_KEY "sudo tar czvf $RESULT_DIR_ON_REMOTE_HOST/$LOG_TAR_GZ_NAME $LOG_ROOT_REMOTE/$APP_ID"
  # Add multiple commands here if there are more than 1 log roots
  # e.g. 
  # yarn_nodemanager_log_dirs = [/data/1/yarn/container-logs, /data/2/yarn/container-logs, /data/3/yarn/container-logs]
  ssh $IP -l $SSH_USER -i $CLOUDBREAK_KEY "sudo chown $USR $RESULT_DIR_ON_REMOTE_HOST/$LOG_TAR_GZ_NAME"
  scp -i $CLOUDBREAK_KEY $SSH_USER@$IP:yarntest_snemeth/$APP_ID-logs.tar.gz $TARGET_DIR/$APP_ID-logs_$IP.tar.gz
done

# Extract archives locally
for IP in $NM_IPS; do
  mkdir $TARGET_DIR/$IP
  tar -xvf $TARGET_DIR/$APP_ID-logs_$IP.tar.gz -C $TARGET_DIR/$IP
done
