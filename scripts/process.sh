#!/bin/bash

function get-pids-of-process {
    PROCESS=$1
    PIDS=`ps auxww | grep ${PROCESS} | awk '{print $2}'`
    #PIDS=`ps cax | grep $PROCESS | grep -o '^[ ]*[0-9]*'`
    if [ -z "$PIDS" ]; then
      echo "Process not running." 1>&2
      exit 1
    else
      for PID in ${PIDS}; do
        echo ${PID}
      done
    fi
}

function is-process-running {
    #ps cax | grep $1 > /dev/null
    ps auxww | grep $1 > /dev/null
    if [ $? -eq 0 ]; then
      echo "Process is running."
    else
      echo "Process is not running."
    fi
}

function psgrep {
    if [ ! -z $1 ] ; then
        echo "Grepping for processes matching $1..."
        ps aux | grep $1 | grep -v grep
    else
        echo "!! Need name to grep for"
    fi
}

function psgrep-silent {
    if [ ! -z $1 ] ; then
        ps aux | grep $1 | grep -v grep
    else
        echo "!! Need name to grep for"
    fi
}