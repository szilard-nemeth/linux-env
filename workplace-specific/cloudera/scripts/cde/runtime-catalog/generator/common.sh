#! /bin/bash


function determine_latest_workdir {
  counter=1
    while true; do
      WORKDIR="${TASKDIR}testing-$(date +%Y%m%d)_$counter/"
      if [ ! -d "$WORKDIR" ]; then
        mkdir -p "$WORKDIR"
        break
      fi
      # echo "Found already existing dir: $WORKDIR, finding another one"
      ((counter++))
    done
    echo "$WORKDIR"
}
