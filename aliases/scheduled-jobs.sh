# --- Scheduled jobs (launchd agents from config/scheduled-jobs.json) -----
# Edit the descriptor in the repo, then `jobs-install` to sync: new/changed jobs
# are (re)loaded, removed or disabled ones are unloaded.
# See scripts/scheduler/scheduled_jobs.py for why this is launchd, not /loop.
alias jobs-list="scheduled_jobs.py --list"
alias jobs-install="scheduled_jobs.py --install"
alias jobs-uninstall="scheduled_jobs.py --uninstall"
alias jobs-status="scheduled_jobs.py --status"
alias jobs-run="scheduled_jobs.py --run"

jobs-logs() {
  local name="${1:?usage: jobs-logs NAME}"
  local log="$HOME/Library/Logs/linuxenv-jobs/$name.log"
  [[ -f $log ]] || { echo "no log yet at $log" >&2; return 1; }
  tail -f "$log"
}
