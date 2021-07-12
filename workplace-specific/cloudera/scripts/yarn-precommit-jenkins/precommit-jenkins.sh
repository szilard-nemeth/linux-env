#!/usr/bin/env bash

set -xv

YETUSDIR=${WORKSPACE}/yetus
ARTIFACTS=${WORKSPACE}/out
BASEDIR=${WORKSPACE}/sourcedir
TOOLS=${WORKSPACE}/tools
rm -rf "${ARTIFACTS}" "${YETUSDIR}"
mkdir -p "${ARTIFACTS}" "${YETUSDIR}" "${TOOLS}"
if [[ -d /sys/fs/cgroup/pids/user.slice ]]; then
  pids=$(cat /sys/fs/cgroup/pids/user.slice/user-910.slice/pids.max)
  if [[ ${pids} -gt 13000 ]]; then
    echo "passed: ${pids}"
    PIDMAX=10000
  else
    echo "failed: ${pids}"
    PIDMAX=5500
  fi
else
  systemctl status $$ 2>/dev/null
  echo "passed? no limit on trusty?"
  PIDMAX=10000
fi
echo "Downloading Yetus 0.13.0-SNAPSHOT"
curl -L https://api.github.com/repos/apache/yetus/tarball/6ab19e71eaf3234863424c6f684b34c1d3dcc0ce -o yetus.tar.gz
gunzip -c yetus.tar.gz | tar xpf - -C "${YETUSDIR}" --strip-components 1

patchfile=$YETUSDIR/precommit/src/main/shell/core.d/patchfiles.sh
sed '129s/.*/set -xv/' $patchfile > tmp.1
sed '167s/.*/set +xv/' tmp.1 > tmp.2
mv tmp.2 $patchfile

YETUS_ARGS+=("--archive-list=checkstyle-errors.xml,spotbugsXml.xml")
YETUS_ARGS+=("--basedir=${BASEDIR}")
YETUS_ARGS+=("--brief-report-file=${ARTIFACTS}/email-report.txt")
YETUS_ARGS+=("--build-url-artifacts=artifact/out")
YETUS_ARGS+=("--console-report-file=${ARTIFACTS}/console-report.txt")
YETUS_ARGS+=("--console-urls")
YETUS_ARGS+=("--docker")
YETUS_ARGS+=("--dockerfile=${BASEDIR}/dev-support/docker/Dockerfile")
YETUS_ARGS+=("--dockermemlimit=20g")
YETUS_ARGS+=("--spotbugs-strict-precheck")
YETUS_ARGS+=("--html-report-file=${ARTIFACTS}/console-report.html")
YETUS_ARGS+=("--java-home=/usr/lib/jvm/java-8-openjdk-amd64")
YETUS_ARGS+=("--jira-password=${JIRA_PASSWORD}")
YETUS_ARGS+=("--jira-user=${JIRA_USER}")
YETUS_ARGS+=("--multijdkdirs=/usr/lib/jvm/zulu-7-amd64,/usr/lib/jvm/java-11-openjdk-amd64")
YETUS_ARGS+=("--multijdktests=compile")
YETUS_ARGS+=("--mvn-custom-repos")
YETUS_ARGS+=("--patch-dir=${ARTIFACTS}")
YETUS_ARGS+=("--personality=${WORKSPACE}/${SOURCEDIR}/dev-support/bin/hadoop.sh")
YETUS_ARGS+=("--project=hadoop")
YETUS_ARGS+=("--proclimit=${PIDMAX}")
YETUS_ARGS+=("--reapermode=kill")
YETUS_ARGS+=("--resetrepo")
YETUS_ARGS+=("--robot")
YETUS_ARGS+=("--sentinel")
YETUS_ARGS+=("--shelldocs=${BASEDIR}/dev-support/bin/shelldocs")
YETUS_ARGS+=("--tests-filter=checkstyle,pylint,shelldocs")
YETUS_ARGS+=("--mvn-javadoc-goals=process-sources,javadoc:javadoc-no-fork")
YETUS_ARGS+=("YARN-${ISSUE_NUM}")
export MAVEN_OPTS="-Xms256m -Xmx1536m -Dhttps.protocols=TLSv1.2 -Dhttps.cipherSuites=TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA256"
TESTPATCHBIN=${YETUSDIR}/precommit/src/main/shell/test-patch.sh
/bin/bash ${TESTPATCHBIN} "${YETUS_ARGS[@]}"