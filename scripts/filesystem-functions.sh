#!/bin/bash

function mount-iso() {
#    dir=/home/szyszy/mnt/temp_imagedisk
    dir=$1
    mkdir -p ${dir}
    mount -o loop "$1" ${dir}
    cd ${dir}
    ls -l
}

function extractall() {
    ls *.zip|awk -F'.zip' '{print "unzip "$0" -d "$1}' | sh
}

function up() {
  local d=""
  limit=$1
  for ((i=1 ; i <= limit ; i++))
    do
      d=${d}/..
    done
  d=$(echo ${d} | sed 's/^\///')
  if [ -z "$d" ]; then
    d=..
  fi
  cd ${d}
}