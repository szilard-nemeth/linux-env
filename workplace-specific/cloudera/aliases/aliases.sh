#!/bin/bash

#GOTO aliases
alias goto-cldr="cd $CLOUDERA_DEV_ROOT"
alias goto-cldr-hadoop="cd $CLOUDERA_HADOOP_ROOT"
alias goto-tasks="cd $HOME/Google Drive File Stream/My Drive/development/tasks/"
alias goto-hadoop="cd $HADOOP_DEV_DIR"
alias goto-hadoop-mvn="cd $HADOOP_MVN_DIR"
alias goto-hadoop-commit="cd $HOME/development/apache/hadoop-commit"
alias goto-qecmf="cd $CLOUDERA_DEV_ROOT/qe-cmf/systest"
alias goto-cmf="cd $CLOUDERA_DEV_ROOT/cmf"
alias goto-yarn-tasks="cd $HOME/yarn-tasks"
alias goto-eyarn="cd $EYARN_DIR"
alias goto-bundlelogprocessor="cd $CLOUDERA_DEV_ROOT/YARN-tools/bundle-log-processor"
alias goto-dex="cd $CLOUDERA_DEV_ROOT/cde/dex"

#git / gerrit commands
alias gerrit-branches5="git br -r | grep gerrit | grep -e '5.1\d.*' | cut -d_ -f 2-3 | sort -u | grep -v patch"
alias git-rebase-trunk="git co trunk && echo 'Pulling origin/trunk...' && git pull && git co - && git rebase trunk"

# Java convenience aliases
#alias j7='export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk1.7.0_80.jdk/Contents/Home'
#alias j8='export JAVA_HOME=/Library/Java//JavaVirtualMachines/jdk1.8.0_151.jdk/Contents/Home'
alias java8="sdk use java 8.0.232-trava"
alias java11="sdk use java 11.0.2-open"

alias git-push-to-cdpdmaster="git push cauldron HEAD:refs/for/cdpd-master%r=gandras,r=bteke,r=tdomok"
alias git-push-to-cdh71maint="git push cauldron HEAD:refs/for/CDH-7.1-maint%r=gandras,r=bteke,r=tdomok"

#==============================================
#YARN-related commands

alias grind-yarn="export GRIND_MAVEN_FLAGS=-Dmaven-dependency-plugin.version=2.10 && \
rm -rf ~/development/cloudera/dist_test/env/.grind/cache/ && \
goto-hadoop-mvn && \
mvn clean install -DskipTests -Dmaven.javadoc.skip=true && \
cd hadoop-yarn-project && \
grind --verbose test --java-version 8"

alias grind-yarn-exceptions="grind --verbose test --java-version 8 \
 -e TestHBaseStorageFlowActivity \
 -e TestHBaseStorageFlowRun \
 -e TestHBaseStorageFlowRunCompaction \
 -e TestHBaseTimelineStorageApps \
 -e TestHBaseTimelineStorageDomain \
 -e TestHBaseTimelineStorageEntities \
 -e TestHBaseTimelineStorageSchema"
#==============================================

#eYARN-related aliases
alias eyarn-deploy="cd $EYARN_DIR; make helm/install ns=$K8S_NAMESPACE; cd -"
alias eyarn-redeploy="cd $EYARN_DIR; make helm/delete ns=$K8S_NAMESPACE && make helm/install ns=$K8S_NAMESPACE; cd -"
alias start-minikube="minikube start --cpus=4"

# Other YARN aliases
alias yarn-fixbuild-zk-intellij="git apply $HOME/googledrive//development_drive/downstream-hadoop-build-issues-patches/fix-zk-intellij.patch"
alias yarn-fixbuild-avro="git apply $HOME/googledrive//development_drive/downstream-hadoop-build-issues-patches/hadoop-build-avro-change2.patch"

# Hadock / Hades aliases
alias hadock-stop="docker-compose -f ~/.hadock/docker-compose.yml down"
alias hadock-start="docker-compose -f ~/.hadock/docker-compose.yml up"

#==============================================
alias run-findbugs="mvn clean install -DskipTests && mvn findbugs:findbugs && mvn findbugs:gui"

alias mvn-hadoop-patch="mvn -Ptest-patch clean site site:stage"
alias mvn-hadoop-cdpd="mvn clean package -s $CLOUDERA_HADOOP_ROOT/cloudera/settings.xml -Pdist -DskipTests -Dmaven.javadoc.skip=true -DskipShade"
alias mvn-hadoop-upstream-build="mvn clean install -Pdist -DskipTests -Dmaven.javadoc.skip=true -DskipShade"
alias mvn-hadoop-upstream-native=build="mvn clean install -Pdist -Pnative -DskipTests -Dmaven.javadoc.skip=true -DskipShade"
alias mvn-generate-proto="mvn generate-sources"
alias cluster-roulette="$HOME/Google\ Drive\ File\ Stream/My\ Drive/development/scripts/cluster-roulette.sh"

#CM specific commands
CM_SKIPTESTS="-DskipTests"
CM_NOBUILD_DIST="-Dnot-dist-build=true"
CM_NOBUILD_NAV="-Dnot-nav-build=true"
CM_NOBUILD_FRONTEND="-DskipFrontend=true"
CM_NO_BUILD_TEST="-Dmaven.test.skip=true"
alias cm-build="make server"
alias cm-build-web="cd ./web && ../tools/cmf-mvn $CM_SKIPTESTS $CM_NOBUILD_FRONTEND install; cd -"
alias cm-build-libs="cd ./libs && ../tools/cmf-mvn $CM_SKIPTESTS $CM_NOBUILD_FRONTEND install; cd -"
alias cm-build-web-notestbuild="cd ./web && ../tools/cmf-mvn $CM_SKIPTESTS $CM_NOBUILD_FRONTEND $CM_NO_BUILD_TEST install; cd -"
alias cm-build-libs-notestbuild="cd ./libs && ../tools/cmf-mvn $CM_SKIPTESTS $CM_NOBUILD_FRONTEND $CM_NO_BUILD_TEST install; cd -"

alias backup-devdir="tmpdate=tar czf /tmp/devbackup-$(eval date-formatted).gz $HOME/development/"
alias backup-home="tar czf /tmp/homedir-backup-$(eval date-formatted).gz $HOME | tee /tmp/homedir-backup-$(date +%Y%m%d_%H%M%S).log"

function backup-currdir() {
  local backup_path="$HOME/googledrive/backup/codebackup/"
  tar czf "$backup_path/$(basename $(pwd))-$(eval date-formatted).gz" ./
  echo "Backup results in dir: $backup_path"
  ll -t $backup_path | grep gz | head -n1
}

alias python-precommit-all="pre-commit run --all-files"