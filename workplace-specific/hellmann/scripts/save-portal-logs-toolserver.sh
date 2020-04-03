#!/usr/bin/env bash

#example usage: bash -x ./save-portal-logs-toolserver.sh --cell ab --basedir /home/snemeth/tmp/trace-logs-20170619/ --patterns "SystemOut*,trace*"
function print_usage {
    echo -e "Usage:\nsave-portal-logs-toolserver.sh --cell <a|b|ab> --basedir <dir> --patterns <pattern1,pattern2,pattern3,...>"
    echo -e example usage: ./save-portal-logs-toolserver.sh --cell b --basedir /home/snemeth/tmp/trace-logs-20170508/ --patterns "SystemOut*,trace*"
}

function save_logs_cell_a {
    CELL_DIR="cell-a"

    for machine in ${MACHINES[@]}; do
        BASENAME=`basename ${MACHINES_PATHS_CELL_A[$machine]}`
        mkdir -p ${BASE_DIR}/${CELL_DIR}/${machine}/${BASENAME}/;

        for pattern in "${patterns_array[@]}"
        do
            scp develop@emea-hps-a02d.hellmann.net:${MACHINES_PATHS_CELL_A[$machine]}/${pattern} ${BASE_DIR}/${CELL_DIR}/${machine}/${BASENAME}/;
        done
    done
}

function save_logs_cell_b {
    CELL_DIR="cell-b"

    for machine in ${MACHINES[@]}; do
        BASENAME=`basename ${MACHINES_PATHS_CELL_B[$machine]}`
        mkdir -p ${BASE_DIR}/${CELL_DIR}/${machine}/${BASENAME}/;

        for pattern in "${patterns_array[@]}"
        do
            scp develop@emea-hps-a02d.hellmann.net:${MACHINES_PATHS_CELL_B[$machine]}/${pattern} ${BASE_DIR}/${CELL_DIR}/${machine}/${BASENAME}/;
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
MACHINES=(emea-hps-a02d-a emea-hps-a02d-b emea-hps-a02d-c emea-hps-a02d-d)

declare -A MACHINES_PATHS_CELL_A;
CELL_A_LOGS_DIR=/toolserver/logs/WPS7/LiveA
MACHINES_PATHS_CELL_A[emea-hps-a02d-a]=${CELL_A_LOGS_DIR}/HPS-PORTAL-A/HPS-PORTAL-A
MACHINES_PATHS_CELL_A[emea-hps-a02d-b]=${CELL_A_LOGS_DIR}/HPS-PORTAL-B/HPS-PORTAL-B
MACHINES_PATHS_CELL_A[emea-hps-a02d-c]=${CELL_A_LOGS_DIR}/HPS-PORTAL-C/HPS-PORTAL-C
MACHINES_PATHS_CELL_A[emea-hps-a02d-d]=${CELL_A_LOGS_DIR}/HPS-PORTAL-D/HPS-PORTAL-D


declare -A MACHINES_PATHS_CELL_B;
CELL_B_LOGS_DIR=/toolserver/logs/WPS7/LiveB
MACHINES_PATHS_CELL_B[emea-hps-a02d-a]=${CELL_B_LOGS_DIR}/HPS-PORTAL-A/HPS-PORTAL-A
MACHINES_PATHS_CELL_B[emea-hps-a02d-b]=${CELL_B_LOGS_DIR}/HPS-PORTAL-B/HPS-PORTAL-B
MACHINES_PATHS_CELL_B[emea-hps-a02d-c]=${CELL_B_LOGS_DIR}/HPS-PORTAL-C/HPS-PORTAL-C
MACHINES_PATHS_CELL_B[emea-hps-a02d-d]=${CELL_B_LOGS_DIR}/HPS-PORTAL-D/HPS-PORTAL-D

if [ "${CELL}" == "a" ]; then
    save_logs_cell_a
elif [ "${CELL}" == "b" ]; then
    save_logs_cell_b
else
    save_logs_cell_a
    save_logs_cell_b
fi
