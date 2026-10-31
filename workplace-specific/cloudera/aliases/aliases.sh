#!/bin/bash

DEX_HOME="$HOME/development/cloudera/cde/dex"

#GOTO aliases
alias goto-cldr="cd $CLOUDERA_DEV_ROOT"
alias goto-cldr-hadoop="cd $CLOUDERA_HADOOP_ROOT"
alias goto-tasks="cd $HOME/googledrive/development/tasks/"
alias goto-hadoop="cd $HADOOP_DEV_DIR"
alias goto-hadoop-mvn="cd $HADOOP_MVN_DIR"
alias goto-hadoop-commit="cd $HOME/development/apache/hadoop-commit"
alias goto-qecmf="cd $CLOUDERA_DEV_ROOT/qe-cmf/systest"
alias goto-cmf="cd $CLOUDERA_DEV_ROOT/cmf"
alias goto-yarn-tasks="cd $HOME/yarn-tasks"
alias goto-cde-tasks="cd $HOME/development/my-repos/knowledge-base-private/cloudera/tasks/cde/"
alias goto-eyarn="cd $EYARN_DIR"
alias goto-bundlelogprocessor="cd $CLOUDERA_DEV_ROOT/YARN-tools/bundle-log-processor"
alias goto-dex="cd $DEX_DEV_ROOT"
alias goto-dex-awc="cd $DEX_AWC_DEV_ROOT/CDE"
alias goto-dex-review="cd $DEX_DEV_ROOT../dex-review"
alias goto-dex-spark-performance="cd $DEX_DEV_ROOT../spark-scale-and-perf"
alias goto-dexter="cd $HOME/development/cloudera/hackathon2022/dexter "
alias goto-thunderhead="cd $DEX_DEV_ROOT../thunderhead"
alias goto-csi="cd $DEX_DEV_ROOT../cloud-services-infra"
alias goto-hades="cd $HOME/development/other-repos/gandras/hades/"
alias goto-cldr-tasks="cd $CLOUDERA_TASKS_DIR"
alias goto-claude-proj-chatgpt-gemini-backup="cd /Users/snemeth/development/my-repos/gemini-chatgpt-backup"


#git / gerrit commands
alias gerrit-branches5="git br -r | grep gerrit | grep -e '5.1\d.*' | cut -d_ -f 2-3 | sort -u | grep -v patch"
alias git-rebase-trunk="git co trunk && echo 'Pulling origin/trunk...' && git pull && git co - && git rebase trunk"

# Java convenience aliases
#alias j7='export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk1.7.0_80.jdk/Contents/Home'
#alias j8='export JAVA_HOME=/Library/Java//JavaVirtualMachines/jdk1.8.0_151.jdk/Contents/Home'
alias java8="sdk use java 8.0.232-trava"
alias java11="sdk use java 11.0.2-open"
alias java17="sdk use java 17.0.14-tem"

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
alias mvn-hadoop-cdpd="asdf uninstall protoc && asdf uninstall maven && cp /usr/local/bin/protoc_old /usr/local/bin/protoc && mvn clean package -s $CLOUDERA_HADOOP_ROOT/cloudera/settings.xml -Pdist -DskipTests -Dmaven.javadoc.skip=true -DskipShade"
alias mvn-hadoop-cdpd-2="asdf uninstall protoc && asdf uninstall maven && cp /usr/local/bin/protoc_old /usr/local/bin/protoc && mvn clean package -s ~/.m2/settings-cdpd.xml -Pdist -DskipTests -Dmaven.javadoc.skip=true -DskipShade"

alias mvn-hadoop-upstream-build="asdf plugin-remove yarn;mvn clean install -Pdist -DskipTests -Dmaven.javadoc.skip=true -DskipShade"
alias mvn-hadoop-upstream-native=build="mvn clean install -Pdist -Pnative -DskipTests -Dmaven.javadoc.skip=true -DskipShade"
alias mvn-generate-proto="mvn generate-sources"
alias cluster-roulette="$HOME/googledrive/development/scripts/cluster-roulette.sh"

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

alias python-precommit-all="pre-commit run --all-files"

#### DEX
alias dex-test-with-clean="goto-dex;make clean-mocks && make gen-mocks && make test"
alias dex-test="goto-dex;make test"
alias dex-update-dev-env="goto-dex;make update-dev-env"
alias dex-docker-cleanup="docker rmi \$(docker images | grep \"1\.18\.0\" | tr -s ' ' | cut -d ' ' -f 3) -f"
alias dex-current-version="goto-dex;jq -r '.hwx[\"stack-version\"]' re_configs/dex-base.json; popd"
alias goto-dex-7712-clitesting="cd $CLOUDERA_TASKS_CDE_DIR/dev-work-from-20221129/cli-testing"
alias dex-print-tasks-dir="echo $CLOUDERA_TASKS_CDE_DIR"
alias pagerduty-when-am-i-on-call="source ~/development/cloudera/pagerduty-helper/venv/bin/activate;~/development/cloudera/pagerduty-helper/when_am_i_on_call.py --user snemeth"
alias pagerduty-when-am-i-on-call-custom="source ~/development/cloudera/pagerduty-helper/venv/bin/activate;~/development/cloudera/pagerduty-helper/when_am_i_on_call.py -s 2023-01-01 --user snemeth"



### DEX, Beni
alias dex-saml2aws="saml2aws exec --exec-profile cu_dex_dev -- bash"
alias dex-runtime-k9s="dexw -e dev -cid cluster-sn6sdnlq --auth cst -v -- k9s"


### DEXter
alias dexter-clean-repo-branches="cd $HOME/dexter/dex && git checkout upgradeDexVersion && git reset develop --hard && git checkout dexDepsRelease && git reset develop --hard"


## Runtime catalog
alias cde-rtcatalog-compare="$CLOUDERA_DIR/scripts/cde/runtime-catalog/compare_catalog.py"

## Claude
# claude-code-tools is an external repo (config/external-repos.json); `ensure` clones it on first use
# (unalias: claude-export used to be an alias, which would shadow this function in already-open shells)
unalias claude-export 2>/dev/null
function claude-export {
  local repo_dir
  repo_dir=$(python3 "$HOME_LINUXENV_DIR/scripts/external-repos.py" ensure claude_code_tools) || return 1
  python3 "$repo_dir/export_claude_sessions.py" "$@"
}
alias claude-export-force="claude-export --force"

function backup-currdir {
  local backup_path="$HOME/googledrive/backup/codebackup/"
  tar czf "$backup_path/$(basename $(pwd))-$(eval date-formatted).gz" ./
  echo "Backup results in dir: $backup_path"
  ls -lat $backup_path | grep gz | head -n1
}

alias vpn-globalprotect-reset="launchctl unload /Library/LaunchAgents/com.paloaltonetworks.gp.pangp* && launchctl load /Library/LaunchAgents/com.paloaltonetworks.gp.pangp*"

function goto-cde-task {
  local target_dir="$CLOUDERA_TASKS_CDE_DIR/$1"

  if [ ! -d "$target_dir" ]; then
    mkdir -p "$target_dir"
    echo "Directory created: $target_dir"
  fi

  cd "$target_dir"
}

function edit-cde-task {
  local target_dir="$CLOUDERA_TASKS_CDE_DIR/$1"
  subl $target_dir
}

# List the last N (default 15) cde task dirs by mtime desc, full paths.
# Usage: cde-recent [N]
function cde-recent {
  local n="${1:-15}"
  # BSD stat (macOS): '%m %N' = mtime-epoch + absolute path. Sort desc, strip mtime.
  find "$CLOUDERA_TASKS_CDE_DIR" -mindepth 1 -maxdepth 1 -type d \
    -exec stat -f '%m %N' {} + \
    | sort -rn \
    | head -n "$n" \
    | awk '{ $1=""; sub(/^ /,""); print }'
}

# Fuzzy-cd into a cde task dir. Accepts a full name, ticket number, or any substring.
# Examples: cde-cd 11292   cde-cd DEX-11292   cde-cd 22097   cde-cd ENGESC-21081
# On multiple matches: lists them (most-recent first) and does not cd.
function cde-cd {
  local query="$1"
  if [[ -z "$query" ]]; then
    echo "usage: cde-cd <ticket-number-or-substring>" >&2
    return 2
  fi

  # Exact hit first (handles "DEX-11292" cleanly, no ambiguity check needed).
  if [[ -d "$CLOUDERA_TASKS_CDE_DIR/$query" ]]; then
    cd "$CLOUDERA_TASKS_CDE_DIR/$query"
    return
  fi

  # Fuzzy: case-insensitive substring match on the basename, mtime-desc for readability.
  local matches
  matches=$(find "$CLOUDERA_TASKS_CDE_DIR" -mindepth 1 -maxdepth 1 -type d -iname "*${query}*" \
              -exec stat -f '%m %N' {} + | sort -rn | awk '{ $1=""; sub(/^ /,""); print }')

  local count
  count=$(printf '%s\n' "$matches" | sed '/^$/d' | wc -l | tr -d ' ')
  if [[ "$count" -eq 0 ]]; then
    echo "no cde task dir matches: $query" >&2
    return 1
  elif [[ "$count" -eq 1 ]]; then
    cd "$matches"
  else
    echo "multiple matches (most-recent first):"
    printf '%s\n' "$matches"
    return 1
  fi
}

my_error_handler() {
  echo "An error occurred!"
  # Add any specific error handling logic here, like logging, cleanup, etc.
  # exit 1 # Optional: exit with an error status
}

cde-rtcatalog-compare-current-with-develop() {
  compare_catalog_py="$CLOUDERA_DIR/scripts/cde/runtime-catalog/compare_catalog.py"
  log_file="/tmp/compare-catalog-out.txt"

  # 1. Save old catalog
  echo $DEX_HOME 
  cd "$DEX_HOME"
  git fetch origin || {
    echo "Git fetch failed, exiting."
    return 1
  }
  git show origin/develop:pkg/control-plane/service/catalog-entries.json > /tmp/catalog-entries-develop.json
  cd -

  old_catalog="/tmp/catalog-entries-develop.json"
  new_catalog="$HOME/development/cloudera/cde/dex/pkg/control-plane/service/catalog-entries.json"

  
  echo "Comparing catalogs..."
  echo "Old: $old_catalog"
  echo "New: $new_catalog"
  echo "Catalog stdtout is logged to: $log_file"
  "$compare_catalog_py" "$old_catalog" "$new_catalog" > $log_file
}


# Private CDE AWC helpers, kept in knowledge-base-private (not in this public repo)
[[ -f "${KB_PRIVATE_REPO}cloudera/cde/cde-awc/scripts/cde-awc-aliases.sh" ]] && source "${KB_PRIVATE_REPO}cloudera/cde/cde-awc/scripts/cde-awc-aliases.sh"

#==============================================
# CDE AWC kind clusters (cde-dev from 'make dev', cde-e2e from 'make test-e2e').
# Cluster-name argument is optional everywhere except cde-kind-delete; default is cde-e2e.
# Notes: knowledge-base-private/cloudera/cde/cde-awc/cde-awc-kind-101.md

alias cde-kind-clusters="kind get clusters"
alias cde-kind-nodes="docker ps --filter label=io.x-k8s.kind.cluster"

function cde-kind-stats {
  docker ps -q --filter label=io.x-k8s.kind.cluster \
    | xargs docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'
}

# Writes the same /tmp kubeconfig the CDE scripts use and exports KUBECONFIG to it.
function cde-kind-use {
  local cluster="${1:-cde-e2e}"
  local kc="/tmp/kubeconfig-kind-${cluster}"
  kind get kubeconfig --name "$cluster" > "$kc" || return 1
  export KUBECONFIG="$kc"
  echo "KUBECONFIG=$KUBECONFIG"
}

function cde-kind-shell {
  docker exec -it "${1:-cde-e2e}-control-plane" bash
}

function cde-kind-health {
  cde-kind-use "${1:-cde-e2e}" > /dev/null || return 1
  kubectl get engines
  kubectl get engineinstances -A
  kubectl get cdecomputes -A
  kubectl get helmreleases -A
  echo "--- pods not Running/Completed:"
  kubectl get pods -A --no-headers | grep -v -E 'Running|Completed'
}

# Top processes inside the node by cumulative CPU time. 'top' inside a kind node shows the
# whole Docker VM, so cumulative time is the useful per-cluster signal.
function cde-kind-top {
  docker exec "${1:-cde-e2e}-control-plane" sh -c 'ps -eo pid,etimes,time,rss,args --sort=-time | head -20' | cut -c1-160
}

# amd64-only images run under Rosetta on Apple Silicon and cost several times the CPU.
function cde-kind-rosetta {
  docker exec "${1:-cde-e2e}-control-plane" sh -c 'ps -eo pid,time,args | grep "/run/rosetta/rosetta" | grep -v grep' | cut -c1-140
}

# Maps a PID from cde-kind-top to its pod and images.
function cde-kind-pod-of-pid {
  local pid="$1" cluster="${2:-cde-e2e}"
  if [[ -z "$pid" ]]; then
    echo "usage: cde-kind-pod-of-pid <pid> [cluster]" >&2
    return 2
  fi
  local uid
  uid=$(docker exec "${cluster}-control-plane" cat "/proc/${pid}/cgroup" \
          | grep -o 'pod[0-9a-f_]*\.slice' | tail -1 | sed -e 's/^pod//' -e 's/\.slice$//' -e 's/_/-/g')
  if [[ -z "$uid" ]]; then
    echo "PID $pid is not in a pod (node-level process)" >&2
    return 1
  fi
  local kc
  kc=$(mktemp)
  kind get kubeconfig --name "$cluster" > "$kc"
  local pod
  pod=$(kubectl --kubeconfig "$kc" get pods -A -o json \
    | jq -r --arg uid "$uid" '.items[] | select(.metadata.uid == $uid)
        | "\(.metadata.namespace)/\(.metadata.name)  \([.spec.containers[].image] | join(" "))"')
  rm -f "$kc"
  # Static pods (kube-apiserver, etcd, ...) carry a config hash as UID, not their mirror pod's UID.
  echo "${pod:-no API pod with UID $uid (static control-plane pod?)}"
}

# Stop frees CPU and RAM; pause frees CPU only. Both keep the cluster for 'make test-e2e' reuse.
function cde-kind-stop    { docker stop    "${1:-cde-e2e}-control-plane"; }
function cde-kind-start   { docker start   "${1:-cde-e2e}-control-plane"; }
function cde-kind-pause   { docker pause   "${1:-cde-e2e}-control-plane"; }
function cde-kind-unpause { docker unpause "${1:-cde-e2e}-control-plane"; }

# No default: a bare 'kind delete cluster' deletes the cluster named 'kind'.
function cde-kind-delete {
  if [[ -z "$1" ]]; then
    echo "usage: cde-kind-delete <cluster>   (clusters: $(kind get clusters | tr '\n' ' '))" >&2
    return 2
  fi
  kind delete cluster --name "$1"
}

function cde-kind-export-logs {
  local cluster="${1:-cde-e2e}"
  local dir="/tmp/kind-logs-${cluster}-$(date +%Y%m%d-%H%M%S)"
  kind export logs "$dir" --name "$cluster"
}

function cde-kind-jobs-api-pf {
  cde-kind-use "${1:-cde-e2e}" > /dev/null || return 1
  echo "Jobs API / UI on http://localhost:18443/ (Ctrl-C to stop)"
  kubectl port-forward svc/cde-jobs-api 18443:8443 -n cde-job-mgmt-ns
}

#==============================================
# Removes every directory under CDE-wt except the kept ones (default: dex-review integration).
# Removal is forced, so untracked and ignored files go too; review the warnings before confirming.
function cde-wt-clean {
  local repo="$HOME/development/cloudera/cde/dex-awc/CDE"
  local wt_root="$HOME/development/cloudera/cde/dex-awc/CDE-wt"
  local -a keep=("$@")
  (( ${#keep[@]} )) || keep=(dex-review integration)

  local -a targets=()
  local d name k kept dirty unpushed
  for d in "$wt_root"/*; do
    [[ -d "$d" ]] || continue
    name="${d##*/}"
    kept=0
    for k in "${keep[@]}"; do [[ "$name" == "$k" ]] && kept=1; done
    (( kept )) || targets+=("$d")
  done

  if (( ${#targets[@]} == 0 )); then
    echo "Nothing to remove (keeping: ${keep[*]})"
    return 0
  fi

  echo "Keeping: ${keep[*]}"
  echo "Removing:"
  for d in "${targets[@]}"; do
    if git -C "$repo" worktree list --porcelain | grep -qxF "worktree $d"; then
      dirty=$(git -C "$d" status --porcelain | wc -l | tr -d ' ')
      unpushed=$(git -C "$d" rev-list --count HEAD --not --remotes)
      echo "  ${d##*/}  [$(git -C "$d" symbolic-ref -q --short HEAD || echo detached)] dirty=$dirty commits-on-no-remote=$unpushed"
    else
      echo "  ${d##*/}  [not a worktree, safe-rm -rf]"
    fi
  done

  printf "Proceed? [y/N] "
  local reply
  read -r reply
  [[ "$reply" == [yY] ]] || { echo "Aborted"; return 1; }

  for d in "${targets[@]}"; do
    if git -C "$repo" worktree list --porcelain | grep -qxF "worktree $d"; then
      git -C "$repo" worktree remove --force "$d"
    else
      safe-rm -rf "$d"
    fi
  done
  git -C "$repo" worktree prune
  git -C "$repo" worktree list
}
