#! /bin/bash

function yarn-compare-upstream-filter-vs-downstream() {
    # IMPORTANT --> PREREQUISITES
    # 1. Save csv file from jira filter to $DIR
    # 2. CSV file should be in this format: Issue key is expected to be in the 2nd column

    # EXAMPLE LINE:
    # Issue Type,Issue key,Issue id,Summary,Assignee,Reporter,Priority,Status,Resolution,Created,Updated,Due Date,Component/s,Component/s,Component/s,Component/s,Labels,Labels,Labels
    # Bug,YARN-10988,13407969,Spark application stuck at ACCEPTED state at spark-submit,,unical1988,Major,Resolved,Invalid,22/Oct/21 16:55,25/Oct/21 19:07,,applications,,,,,,

    if [ -z "$SCRIPT" ]
    then 
        /usr/bin/script log.txt /bin/bash -c "$0 $*"
        exit 0
    fi

    set -x
    # Dynamic variables: Session dir name should be changed per run
    CLDR_HADOOP_ROOT="$HOME/development/cloudera/hadoop"
    SESSION="monitor-us-bugs-highprio"


    # STEP1: Setup file variables
    UPSTREAM_FILTER_FILE=upstream-yarn-mapred.txt
    UPSTREAM_FILTER_FILE_SORTED=upstream-yarn-mapred-sorted.txt
    CDPDMASTER_RAW_GREP_FILE="cdpd-master-yarn-mapred-grep-raw.txt"
    CDPDMASTER_GREP_SORTED_FILE="cdpd-master-yarn-mapred-grep-sorted.txt"
    FINAL_RESULT_FILE="result-upstream-vs-cdpdmaster-diff-yarn.txt"


    # STEP2: Create dirs
    cd /
    DIR="$HOME/Downloads/upstream-vs-downstream-yarndiff/$SESSION"
    mkdir -p $DIR

    # Ensure that CSV file is there
    # https://serverfault.com/a/225827/375328
    find $DIR -iname "*.csv" | grep .
    if [[ "$?" -ne 0 ]]; then
        echo "CSV file not found in directory: $DIR"
        exit 1
    fi

    CSV_FILE=$(find $DIR -iname "*.csv")

    # Sanitize csv filename
    cd $DIR
    mv "$CSV_FILE" "${CSV_FILE// /_}"
    CSV_FILE=$(basename `find $DIR -iname "*.csv"`)
    cd -

    # STEP3: Create file that has the jira ids only
    cat $DIR/$CSV_FILE | cut -d ',' -f2 > $DIR/$UPSTREAM_FILTER_FILE


    # STEP4: Sort upstream list
    cat $DIR/$UPSTREAM_FILTER_FILE | sort | uniq > $DIR/$UPSTREAM_FILTER_FILE_SORTED


    # STEP4: Create grepped commit list from cdpd-master: MAPREDUCE, YARN + sort + uniq
    cd $CLDR_HADOOP_ROOT
    git pull
    git log --oneline | grep -e 'MAPREDUCE-[0-9]*\|YARN-[0-9]*' -o > $DIR/$CDPDMASTER_RAW_GREP_FILE
    cat $DIR/$CDPDMASTER_RAW_GREP_FILE | sort | uniq > $DIR/$CDPDMASTER_GREP_SORTED_FILE


    # STEP5: Grep all results that are in upstream list of YARN/MAPREDUCE commits, but not in cdpd-master list
    comm -23 $DIR/$UPSTREAM_FILTER_FILE_SORTED $DIR/$CDPDMASTER_GREP_SORTED_FILE > $DIR/$FINAL_RESULT_FILE

    echo "Absolute path of final result file: $DIR/$FINAL_RESULT_FILE"
    echo "Number of commits not found on cdpd-master: `wc -l $DIR/$FINAL_RESULT_FILE`"
}