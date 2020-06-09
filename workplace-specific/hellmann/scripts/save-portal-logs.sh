#!/usr/bin/env bash

#example usage: ./save-portal-logs.sh --cell b --basedir /home/snemeth/tmp/trace-logs-20170508/ --patterns "SystemOut*,trace*"
function print_usage {
    echo -e "Usage:\nsave-portal-logs.sh --cell <a|b|ab> --basedir <dir> --patterns <pattern1,pattern2,pattern3,...>"
    echo -e example usage: ./save-portal-logs.sh --cell b --basedir /home/snemeth/tmp/trace-logs-20170508/ --patterns "SystemOut*,trace*"
}

function save_logs_cell_a {
    CELL_DIR="cell-a"

    for machine in ${MACHINES[@]}; do
        mkdir -p ${BASE_DIR}/${CELL_DIR}/${machine}/;

        for pattern in "${patterns_array[@]}"
        do
            scp root@${machine}.hellmann.net:${MACHINES_PATHS_CELL_A[$machine]}/${pattern} ${BASE_DIR}/${CELL_DIR}/${machine}/;
        done
    done
}

function save_logs_cell_b {
    CELL_DIR="cell-b"

    for machine in ${MACHINES[@]}; do
        mkdir -p ${BASE_DIR}/${CELL_DIR}/${machine}/;

        for pattern in "${patterns_array[@]}"
        do
            scp root@${machine}.hellmann.net:${MACHINES_PATHS_CELL_B[$machine]}/${pattern} ${BASE_DIR}/${CELL_DIR}/${machine}/;
        done
    done
}


if [[ $# -eq 1 ]]; then
    case "$1" in
    -h|--help)
        print_usage
        exit 1
        ;;
    *)
        echo "Unknown parameter $1"
        print_usage
        exit 1
        ;;
    esac
fi

while [[ $# > 1 ]]
do
key="$1"
case ${key} in
    --cell)
    CELL="${2}"
    shift
    ;;
    --basedir)
    BASE_DIR="${2}"
    shift
    ;;
     --patterns)
    PATTERNS="${2}"
    shift
    ;;
    *)
    echo "Unknown parameter $key"
    print_usage
    exit 1
    ;;
esac
shift
done

ERROR=0
if [ "${CELL}" != "a" ] && [ "${CELL}" != "b" ] && [ "${CELL}" != "ab" ]; then
    echo "Cell parameter is not 'a' or 'b' or 'ab'"
    ERROR=1
fi
if [ -z "$BASE_DIR" ]; then
    echo "Basedir parameter is not provided."
    ERROR=1
fi
if [ -z "$PATTERNS" ]; then
    echo "Patterns parameter is not provided."
    ERROR=1
fi


if [ "$ERROR" -eq 1 ]; then
    print_usage
    exit 1
fi

#IFS=',' ;for i in `echo "Hello,World,Questions,Answers,bash shell,script"`; do echo $i; done
IFS=', ' read -r -a patterns_array <<< "$PATTERNS"
MACHINES=(host02p host03p host04p host05p)

declare -A MACHINES_PATHS_CELL_A;
CELL_A_LOGS_DIR=/opt/IBM/WebSphere/wp_profile/logs/
MACHINES_PATHS_CELL_A[host02p]=${CELL_A_LOGS_DIR}/HPS-PORTAL-A/
MACHINES_PATHS_CELL_A[host03p]=${CELL_A_LOGS_DIR}/HPS-PORTAL-B/
MACHINES_PATHS_CELL_A[host04p]=${CELL_A_LOGS_DIR}/HPS-PORTAL-C/
MACHINES_PATHS_CELL_A[host05p]=${CELL_A_LOGS_DIR}/HPS-PORTAL-D/


declare -A MACHINES_PATHS_CELL_B;
CELL_B_LOGS_DIR=/opt/IBM/WebSphere_clusterB/wp_profile/logs/
MACHINES_PATHS_CELL_B[host02p]=${CELL_B_LOGS_DIR}/HPS-PORTAL-D/
MACHINES_PATHS_CELL_B[host03p]=${CELL_B_LOGS_DIR}/HPS-PORTAL-C/
MACHINES_PATHS_CELL_B[host04p]=${CELL_B_LOGS_DIR}/HPS-PORTAL-B/
MACHINES_PATHS_CELL_B[host05p]=${CELL_B_LOGS_DIR}/HPS-PORTAL-A/

if [ "${CELL}" == "a" ]; then
    save_logs_cell_a
elif [ "${CELL}" == "b" ]; then
    save_logs_cell_b
else
    save_logs_cell_a
    save_logs_cell_b
fi
