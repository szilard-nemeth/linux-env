#!/usr/bin/env bash


function export-chrome-history() {
    #IDEA COMES FROM: 
    ####https://superuser.com/a/602274
    ####https://gist.github.com/TravelingTechGuy/7ac464f6cccde912a6ec7a1e2f8aa96a

    #set -x
    local CHROME_HIST_DB_SRC="$(echo $1 | tr -d "\\")"
    local PROFILE="$2"
    local currdate=$(date +%Y%m%d_%H%M%S)
    local basedir=$HOME/Downloads/chrome-history-export-${currdate}
    mkdir ${basedir}
    local CHROME_HIST_DB=${basedir}/chrome-history-db-${PROFILE}
    touch CHROME_HIST_DB
    local TARGET_FILE=${basedir}/chrome-history-export-${PROFILE}.csv
    
    echo "Copying Chrome history file from ${CHROME_HIST_DB_SRC} to ${CHROME_HIST_DB} (profile: $PROFILE)"
    cp "${CHROME_HIST_DB_SRC}" "${CHROME_HIST_DB}"
    #set +x
    
    echo "Using chrome history file from: $CHROME_HIST_DB (size: $(du -sh ${CHROME_HIST_DB} | awk '{print $1}'))"
    sqlite3 ${CHROME_HIST_DB} <<!
.headers on
.mode csv
.output ${TARGET_FILE}
select datetime(last_visit_time/1000000-11644473600,'unixepoch') as 'date',url from  urls order by last_visit_time desc;
!
    echo "Exported chrome history file to: ${TARGET_FILE} (size: $(du -sh ${TARGET_FILE} | awk '{print $1}'))"
}

function export-chrome-history-all() {
    #/Users/szilardnemeth/Library/Application Support/Google/Chrome//Profile 1/History
    #/Users/szilardnemeth/Library/Application Support/Google/Chrome//Default/History
    #/Users/szilardnemeth/Library/Application Support/Google/Chrome//Profile 3/History
    #/Users/szilardnemeth/Library/Application Support/Google/Chrome//System Profile/History
    #/Users/szilardnemeth/Library/Application Support/Google/Chrome//Guest Profile/History
    
    #RELATED: https://sessionbuddy.com/chrome-profile-location/
    ####Open this page to check active profile: chrome://version/

    find ~/Library/Application\ Support/Google/Chrome/ -iname History | while read file; do
        file=$(echo $file | sed 's/ /\\ /g')
        echo "Found chrome history DB file: '$file'"
        #https://superuser.com/a/443862
        
        #echo "Separated path: "
        local lastdir=${file##*/}
        local parentpath=${file%/*}
        #echo "LASTDIR: $lastdir"
        #echo "PARENTPATH: $parentpath"
        #This produces something like this: 
        ##/Users/szilardnemeth/Library/Application\ Support/Google/Chrome//Profile\ 3
        #echo "Basename of parent path: $(basename "${parentpath}")"
        local profile=$(basename "${parentpath}" | tr -d "\\" | tr -d " ") 
        
        #echo "File: $file"
        #echo "Profile: $profile"
        export-chrome-history "${file}" ${profile}
        #return
    done
}