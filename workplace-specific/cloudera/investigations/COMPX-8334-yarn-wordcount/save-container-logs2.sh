set -x
APP_ID="application_1653513220496_0001"
TARGET_DIR=~/Downloads/_work/hbase-7tb-replication-fails/investigation_1/yarntest_snemeth/
mkdir -p $TARGET_DIR
CLOUDBREAK_KEY=~/.ssh/nightly_id_rsa
# NM_IPS=(10.17.234.33 10.17.234.34 10.17.234.36 10.17.234.37 10.17.234.38 10.17.234.39 10.17.234.40 10.17.234.41 10.17.234.42 10.17.234.43 10.17.234.44 10.17.237.23 10.17.237.24 10.17.237.25 10.17.237.26 10.17.237.28 10.17.237.29 10.17.237.30 10.17.237.31 10.17.237.32 10.17.237.34)
NM_IPS=(10.17.234.34 10.17.234.36 10.17.234.37 10.17.234.38 10.17.234.39 10.17.234.40 10.17.234.41 10.17.234.42 10.17.234.43 10.17.234.44 10.17.237.23 10.17.237.24 10.17.237.25 10.17.237.26 10.17.237.28 10.17.237.29 10.17.237.30 10.17.237.31 10.17.237.32 10.17.237.34)

SSH_USER=systest
SSH_PARAMS="-o StrictHostKeyChecking=accept-new"
USR=systest
RESULT_DIR_ON_REMOTE_HOST="~$USR/yarntest_snemeth"
LOG_TAR_GZ_NAME=$APP_ID-logs.tar.gz
D1="/data/1/yarn/container-logs"
D2="/data/2/yarn/container-logs"
D3="/data/3/yarn/container-logs"

for IP in "${NM_IPS[@]}"; do
  echo $IP
  set +e
  ssh $IP -l $SSH_USER -i $CLOUDBREAK_KEY $SSH_PARAMS "mkdir -p $RESULT_DIR_ON_REMOTE_HOST"
  set -e
  #tar is capable of tarring multiple dirs into one archive -> https://www.linuxquestions.org/questions/linux-newbie-8/tar-multiple-directories-into-one-file-880881/
  ssh $IP -l $SSH_USER -i $CLOUDBREAK_KEY "sudo tar czvf $RESULT_DIR_ON_REMOTE_HOST/$LOG_TAR_GZ_NAME $D1/$APP_ID $D2/$APP_ID $D3/$APP_ID"
  # Add multiple commands here if there are more than 1 log roots
  # e.g. 
  # yarn_nodemanager_log_dirs = [/data/1/yarn/container-logs, /data/2/yarn/container-logs, /data/3/yarn/container-logs]
  ssh $IP -l $SSH_USER -i $CLOUDBREAK_KEY "sudo chown $USR $RESULT_DIR_ON_REMOTE_HOST/$LOG_TAR_GZ_NAME"
  scp -i $CLOUDBREAK_KEY $SSH_USER@$IP:yarntest_snemeth/$APP_ID-logs.tar.gz $TARGET_DIR/$APP_ID-logs_$IP.tar.gz
done

# Extract archives locally
for IP in $NM_IPS; do
  set +e
  mkdir $TARGET_DIR/$IP
  set -e
  tar -xvf $TARGET_DIR/$APP_ID-logs_$IP.tar.gz -C $TARGET_DIR/$IP
done
