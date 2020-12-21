. ./setup-vars.sh

set -e
set -x
echo "Syncing SLS config files to remote host: $CLUSTER_HOST1..."
ssh $CLUSTER_HOST1 "mkdir -p $REMOTE_BASEDIR/config"
scp -r $INVESTIGATION_BASEDIR/config $CLUSTER_HOST1:$REMOTE_BASEDIR/

echo "Syncing SLS scripts to remote host: $CLUSTER_HOST1..."
rsync -avP $INVESTIGATION_BASEDIR/scripts --prune-empty-dirs --include "/*/"  --include="*.sh" --exclude="*" \
$INVESTIGATION_BASEDIR/ $CLUSTER_HOST1:$REMOTE_BASEDIR/

echo "Launching SLS on remote host: $CLUSTER_HOST1"
ssh $CLUSTER_HOST1 "$REMOTE_BASEDIR/scripts/start-sls.sh $HADOOP_VERSION $REMOTE_BASEDIR"
$INVESTIGATION_BASEDIR/scripts/save-latest-sls-logs.sh