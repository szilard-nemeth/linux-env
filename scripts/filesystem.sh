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

function diff_files_in_dirs() {
  #EXAMPLE CALL:
  #diff_files_in_dirs ~/development/my-repos/python/yarn-dev-func ~/development/my-repos/linux-env/workplace-specific/cloudera/scripts/yarn/python "*.py"
  if [ $# -ne 3 ]; then
    echo "Usage: $0 [dir1] [dir2] [filename-pattern]"
    echo "Example: $0 $(pwd)/ ~/somedir/ '*.py'"
    return 1
  fi

  local dir1=$1
  local dir2=$2
  local filename_expr=$3
#  set -x
  echo "Diffing files matching name $filename_expr between dirs: $dir1 vs. $dir2"
  for file in $(find $dir1 -maxdepth 1 -name $filename_expr -exec basename {} \;); do
#    echo $file
    diff "$dir1/$file" "${dir2}/${file##*/}";
  done
#  set +x
}

function zip-directory() {
    #EXAMPLE CALL:
    #zip-directory <dir> <path-to-tar>
    if [ $# -ne 2 ]; then
       echo "Usage: $0 [dir1] [path-to-tar]"
        echo "Example: $0 <some-directory> <path-to-tar-archive-with-name>"
        return 1
    fi
    tar -czvf $2.tar.gz -C $1 .
}