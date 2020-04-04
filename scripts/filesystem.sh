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

#dirsize - finds directory sizes and lists them for the current directory
function dirsize () {
    du -shx * .[a-zA-Z0-9_]* 2> /dev/null | \
    egrep '^ *[0-9.]*[MG]' | sort -n > /tmp/list
    egrep '^ *[0-9.]*M' /tmp/list
    egrep '^ *[0-9.]*G' /tmp/list
    rm -rf /tmp/list
}

function extract () {
     if [ -f $1 ] ; then
         case $1 in
             *.tar.bz2)   tar xjf $1        ;;
             *.tar.gz)    tar xzf $1     ;;
             *.bz2)       bunzip2 $1       ;;
             *.rar)       rar x $1     ;;
             *.gz)        gunzip $1     ;;
             *.tar)       tar xf $1        ;;
             *.tbz2)      tar xjf $1      ;;
             *.tgz)       tar xzf $1       ;;
             *.zip)       unzip $1     ;;
             *.Z)         uncompress $1  ;;
             *.7z)        7z x $1    ;;
             *)           echo "'$1' cannot be extracted via extract()" ;;
         esac
     else
         echo "'$1' is not a valid file"
     fi
}