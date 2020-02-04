#!/bin/bash

#TODO remove
#MOUNT the given image parameter

#[root@szyszyLAPTOP _SCRIPTS]# sudo ./mount_ISO.sh "/media/Szyszy's Ext_HDD/torrents/diablo_film/Dr House 1.évad/House_1-1.ISO"
#total 4
#dr-xr-xr-x 2 4294967295 4294967295   40 2006-05-31 21:41 AUDIO_TS
#dr-xr-xr-x 2 4294967295 4294967295 1444 2006-05-31 21:41 VIDEO_TS
 

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
      d=$d/..
    done
  d=$(echo $d | sed 's/^\///')
  if [ -z "$d" ]; then
    d=..
  fi
  cd $d
}