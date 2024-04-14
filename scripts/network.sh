#!/usr/bin/env bash
getMyIP() {
    local _ip _myip _line _nl=$'\n'
    while IFS=$': \t' read -a _line ;do
        [ -z "${_line%inet}" ] &&
           _ip=${_line[${#_line[1]}>4?1:2]} &&
           [ "${_ip#127.0.0.1}" ] && _myip=${_ip}
      done< <(LANG=C /sbin/ifconfig)
    printf ${1+-v} $1 "%s${_nl:0:$[${#1}>0?0:1]}" ${_myip}
}

#netinfo - shows network information for your system
function netinfo {
    echo "--------------- Network Information ---------------"
    /sbin/ifconfig | awk /'inet addr/ {print $2}'
    /sbin/ifconfig | awk /'Bcast/ {print $3}'
    /sbin/ifconfig | awk /'inet addr/ {print $4}'
    /sbin/ifconfig | awk /'HWaddr/ {print $4,$5}'
    echo "---------------------------------------------------"
}

function setproxy {
    if [[ -z "$http_proxy" ]];
        then export http_proxy=http://159.107.0.62:8080;export https_proxy=http://159.107.0.62:8080;echo "e/// proxy on";
    else unset http_proxy;unset https_proxy;echo "e/// proxy off";
    fi
}

function net-disconnect {
    GW="$(sudo /sbin/route -n | awk '$1=="0.0.0.0" {print $2; exit}')"
    if [ ! -z "$GW" ]; then
        sudo /sbin/route del default gw "$GW"
        echo "$GW" > ~/.gateway
    fi
}

function net-connect {
    sudo /sbin/route add default gw "$(cat ~/.gateway)"
}
