#!/usr/bin/env bash


function print-script-step() {
    echo -e "[SCRIPT-STEP] ------------------------------------------------------------------------"
    echo -e "[SCRIPT-STEP] $1"
    echo -e "[SCRIPT-STEP] ------------------------------------------------------------------------"
}

function replace-logstrings-with-regexes() {
##This does not handle strings like "bla\"cc\"bla"
#TODO handle files or strings

#sed 1: Extracts log string from LOG.<info|debug> calls
#sed 2: Removes leading whitespaces
#sed 3: Removes pointless java string concatenations.
#Example: ...yy " + " xx... --> ...yy  xx...

#sed 4: convert var concatenations to regexes in the form of: bla1" + var + "bla2
#Example: ...xx" + somevar + "yy... --> ...xx.*yy...

#sed 5: Converts var concatenations to regexes if expression ends with var.
#Example: "...somestring=" + somevar$ --> ...somestring=.*$

#sed 6: Converts var concatenations to regexes if expression starts with var.
#Example: somevar + "somestring... --> .* + "xx...

    cat "$1"|\
    sed -e 's/^[ \t]*//'|\
    sed -r -n -e 's/.*\.(info|debug)\("(.*)\);/\2/p'|\
    sed -r -e 's/"\s+\+\s+[^"+]*\s+\+\s+"/.*/g'|\
    sed -r -e 's/"\s+\+\s+[^+]*$/.*/g'|\
    sed -r -e 's/^[^ +"]*\s+\+\s+"/.*/g'|\
    sed -r -e 's/"\s+\+\s+"//g'|\
    sed -r -e 's/"//g'
}
#
#function find-matched-log-records() {
#
#}

function logs2regex() {
    local BASE_DIR="$1/log2regex"
    local LOG_PATCH=$2
    
    mkdir -p ${BASE_DIR}
    
    local LOG_STMTS_FROM_DIFF="/$BASE_DIR/log-from-diff"
    local LOG_STMTS_FROM_CODE="/$BASE_DIR/log-from-code"
    local LOG_STMTS_FROM_DIFF_REGEX="/$BASE_DIR/log-from-diff-regex"
    local LOG_STMTS_FROM_CODE_REGEX="/$BASE_DIR/log-from-code-regex"
    LOG_STMTS_ALL_REGEX="/$BASE_DIR/log-from-all-regex"
    
    #TODO only match lines starting with plus sign (only consider added lines from diff)
    grep -iE 'log\.(info|debug).*' ${LOG_PATCH} > ${LOG_STMTS_FROM_DIFF}
    
    grep '#grepthis' * -R -A3 --include=*.java --no-filename hadoop-yarn-project/ |\
    grep -iE 'log\.(info|debug).*' | uniq > ${LOG_STMTS_FROM_CODE}
    
    set -e
    echo "About to execute: replace-logstrings-with-regexes $LOG_STMTS_FROM_CODE > $LOG_STMTS_FROM_CODE_REGEX"
    replace-logstrings-with-regexes ${LOG_STMTS_FROM_CODE} > ${LOG_STMTS_FROM_CODE_REGEX}
    
    echo "About to execute: replace-logstrings-with-regexes $LOG_STMTS_FROM_DIFF > $LOG_STMTS_FROM_DIFF_REGEX"
    replace-logstrings-with-regexes ${LOG_STMTS_FROM_DIFF} > ${LOG_STMTS_FROM_DIFF_REGEX}
    
    cat ${LOG_STMTS_FROM_CODE_REGEX} ${LOG_STMTS_FROM_DIFF_REGEX} > ${LOG_STMTS_ALL_REGEX}
    echo "Generated log regexes to: $LOG_STMTS_ALL_REGEX"
    set +e
}

function cp-with-prefix() {
    #TODO check if dirs do exist
    COPY_SRC="$1"
    COPY_DST="$2"
    #TODO validate prefix: should match [a-zA-z0-9_-]+
    PREFIX="$3"
    for f in ${COPY_SRC}/*.*; do cp "$f" "$COPY_DST/$PREFIX-$(basename ${f})"; done
}

function exec-junit-tests() {
    #TODO check parameter count!
    local TEST_CLASS=$1
    local TEST_RESULT_FILE_PREFIX=$2
    local BASE_DIR=$3
    local TEST_FILE_PATH=$(find . -iname "*${TEST_CLASS}.java") #TODO check if test file is an existing one!
    set -e
    
    MVN_BUILD_OUTPUT_FILE="$BASE_DIR/mvn-build-$TEST_RESULT_FILE_PREFIX.out"
    echo "Printing git diff to file $MVN_BUILD_OUTPUT_FILE before compiling test code"
    git diff > ${MVN_BUILD_OUTPUT_FILE}
    mvn clean package -DskipTests >> ${MVN_BUILD_OUTPUT_FILE}
    
    TESTCASES=($(grep '@Test' -A2 ${TEST_FILE_PATH} | grep 'test.*' | sed -r -n -e 's/.*(test[a-zA-Z0-9_]+)\(.*/\1/p'))
    echo "Discovered testcases in $TEST_CLASS:"
    printf '%s\n' "${TESTCASES[@]}"
    SUREFIRE_TC_PARAMS=("FairSharePreemptionWithDRF" "MinSharePreemptionWithDRF") #TODO make junit parameters a bash function parameter
    set +e
    
    TC_COUNTER=0
    for TC_NAME in "${TESTCASES[@]}"; do 
        for SF_PARAM in "${SUREFIRE_TC_PARAMS[@]}"; do
            TC_COUNTER=$(expr ${TC_COUNTER} + 1)
            #cleanup original surefire reports directory
            rm "$SUREFIRE_REPORTS_DIR"/* || true
            
            #create directory for surefire results
            TC_SUREFIRE_RESULTS_DIR="$BASE_DIR/$TEST_CLASS/$TC_NAME-$SF_PARAM"
            mkdir -p ${TC_SUREFIRE_RESULTS_DIR}
        
            #run testcase individually
            TC_FULL_NAME="$TEST_CLASS#$TC_NAME[$SF_PARAM]"
            echo "$TC_COUNTER. Running testcase: $TC_FULL_NAME"
            MVN_CMD="mvn test -Dtest=$TC_FULL_NAME -DfailIfNoTests"
            echo "$TC_COUNTER. $MVN_CMD > $TC_SUREFIRE_RESULTS_DIR/$TEST_RESULT_FILE_PREFIX-mvn-test.out 2>&1" 
            ${MVN_CMD} > ${TC_SUREFIRE_RESULTS_DIR}/${TEST_RESULT_FILE_PREFIX}-mvn-test.out 2>&1
            if [ $? -ne 0 ]; then
                echo "TEST $TC_FULL_NAME FAILED!"
                touch "$TC_SUREFIRE_RESULTS_DIR/$TEST_RESULT_FILE_PREFIX-failed"
            fi
            
            #copy surefire result files to result directory
            cp-with-prefix ${SUREFIRE_REPORTS_DIR} ${TC_SUREFIRE_RESULTS_DIR} ${TEST_RESULT_FILE_PREFIX}
#            cp $SUREFIRE_REPORTS_DIR/* $TC_SUREFIRE_RESULTS
        done
    done
}

function print-junit-report() {
    local BASE_DIR=$1
    OLDIFS="$IFS"
    local FAILED_TESTS=($(find ${BASE_DIR} -iname '*failed' | sed "s|$BASE_DIR/||g" | sed 's/^\s+//'))
    echo -e "[TEST_REPORT] ------------------------------------------------------------------------"
#    set -x
#for i in "${PARTS[@]}"; do printf '%s ' "$i"; done
    for TEST_PATH in "${FAILED_TESTS[@]}"; do
#        echo $TEST_PATH
        IFS="/" read -ra PARTS <<< "$TEST_PATH"
        IFS="$OLDIFS"
        local TEST_CLASS=${PARTS[0]}
        local TEST_CASE=${PARTS[1]}
        local MODE=$(echo ${PARTS[2]} | sed 's/-failed//')
        
        if [ "$MODE" = "with-codechange" ]; then
           FAILED_PREFIX="With codechange"   
        elif [ "$MODE" = "wo-codechange" ]; then
           FAILED_PREFIX="Without codechange"  
        fi
        echo -e "[TEST_REPORT] [FAILED $FAILED_PREFIX] Class: $TEST_CLASS - testcase: $TEST_CASE"
    done
    IFS="$OLDIFS"
    echo -e "[TEST_REPORT] ------------------------------------------------------------------------\n"
#    set +x
}

function grep-in-test-logs() {
    #TODO check BASE_DIR argument is provided!
    local BASE_DIR=$1
    OLDIFS="$IFS"
    #only print path names and not the filenames
    local FAILED_TESTS=($(find ${BASE_DIR} -iname '*failed' -exec dirname {} \; | sed "s|$BASE_DIR/||g" | sed 's/^\s+//'))
    
    for TEST_PATH in "${FAILED_TESTS[@]}"; do
        IFS="/" read -ra PARTS <<< "$TEST_PATH"
        IFS="$OLDIFS"
        local TEST_CLASS=${PARTS[0]}
        local WITH_CODE_CHANGE_PATTERN="with-codechange*$TEST_CLASS*-output.txt"
        local WO_CODE_CHANGE_PATTERN="wo-codechange*$TEST_CLASS*-output.txt"
        local TEST_OUTPUT_WITH_CODE_CHANGE=$(find ${BASE_DIR}/${TEST_PATH} -iname "$WITH_CODE_CHANGE_PATTERN")
        local TEST_OUTPUT_WO_CODE_CHANGE=$(find ${BASE_DIR}/${TEST_PATH} -iname "$WO_CODE_CHANGE_PATTERN")
        
        NUMBER_OF_RESULTS=$(echo "$TEST_OUTPUT_WITH_CODE_CHANGE" | wc -l)
        if [ ${NUMBER_OF_RESULTS} -gt 1 ]; then
            echo "Two or more files found for pattern $WITH_CODE_CHANGE_PATTERN in search root: $BASE_DIR/$TEST_PATH";
            echo "Exiting..."
            exit 2
        fi
        NUMBER_OF_RESULTS=$(echo "$TEST_OUTPUT_WO_CODE_CHANGE" | wc -l)
        if [ ${NUMBER_OF_RESULTS} -gt 1 ]; then
            echo "Two or more files found for pattern $WO_CODE_CHANGE_PATTERN in search root: $BASE_DIR/$TEST_PATH";
            echo "Exiting..."
            exit 2
        fi
        
        if [ -z "$LOG_STMTS_ALL_REGEX" ]; then
            echo "LOG_STMTS_ALL_REGEX is empty, please define it!"
            exit 1
        fi
        
        GREPPED_LOGS_FILENAME_WO_CHANGE="$(echo "$TEST_OUTPUT_WO_CODE_CHANGE" | sed -e 's/\.txt//')-grepped-log.txt"
        GREP_CMD="grep -f $LOG_STMTS_ALL_REGEX $TEST_OUTPUT_WO_CODE_CHANGE"
        #print-script-step "Executing command: $GREP_CMD > $GREPPED_LOGS_FILENAME_WO_CHANGE"
        ${GREP_CMD} > ${GREPPED_LOGS_FILENAME_WO_CHANGE}
        
        GREPPED_LOGS_FILENAME_WITH_CHANGE="$(echo "$TEST_OUTPUT_WITH_CODE_CHANGE" | sed -e 's/\.txt//')-grepped-log.txt"
        GREP_CMD="grep -f $LOG_STMTS_ALL_REGEX $TEST_OUTPUT_WITH_CODE_CHANGE"
        #print-script-step "Executing command: $GREP_CMD  > $GREPPED_LOGS_FILENAME_WITH_CHANGE"
        ${GREP_CMD}  > ${GREPPED_LOGS_FILENAME_WITH_CHANGE}
        
        print-script-step "Diff these files to analyze failure: $GREPPED_LOGS_FILENAME_WO_CHANGE <> $GREPPED_LOGS_FILENAME_WO_CHANGE"
    done
}

function cleanup() {
    ###6. CLEANUP: Reset git to original state: just the code changes, no log patch
    rv=$?
    git reset HEAD --hard
    print-script-step "CLEANUP: Restoring original code patch from file: $CODE_PATCH"
    git apply ${CODE_PATCH}
    exit ${rv}
}


#TODO create 2 branches alternatively with code changes and code changes+log changes (for future tracking of which code test was running against)
#TODO add option: whether to grep in tests results or not!
#TODO replace all exit calls with return, as exit will terminate the shell process!
function compare-yarn-rm-test-runs() {
    trap cleanup INT TERM EXIT

    #prepare params
    #TODO create param for project to execute tests for: hadoop-yarn-server-resourcemanager
    SUREFIRE_REPORTS_DIR="$HOME/development/apache/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-resourcemanager/target/surefire-reports/"
    local SUREFIRE_TEST_CLASS="TestFairSchedulerPreemptionCustomResources" #TODO make this a param, add possibility to execute 2 or more test classes
    local LOG_PATCH="$HOME/yarn-tasks/YARN-8059/log.patch" #TODO make this a param
    
    #prepare dirs
    local TEST_RUN_DATE=`date +%F-%H%M%S`
    local BASE_DIR="$HOME/yarn-testcomparison-$TEST_RUN_DATE/"
    mkdir -p "$BASE_DIR/$SUREFIRE_TEST_CLASS"
    
    goto-hadoop
    #create regex files from log changes
    logs2regex ${BASE_DIR} ${LOG_PATCH}
    
    goto-hadoop
    cd hadoop-yarn-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-resourcemanager
    
    ###1. Save code changes to patch file
    #global as cleanup code restores CODE_PATCH
    CODE_PATCH=${BASE_DIR}/code-changes.patch
    git diff > ${CODE_PATCH}
    
    #TODO make this check switchable i.e. if no code changes, just run tests in one go and store the results
    local SIZE_OF_PATCH=$(du ${CODE_PATCH} | cut -f1)
    if [ ${SIZE_OF_PATCH} -eq 0 ]; then 
        echo "'git diff' returned an empty result! Please make sure there are code changes to apply!"
        return 1
    fi
    
#    original_branch=$(git rev-parse --abbrev-ref HEAD)
    set -e
    ###2. Clean git workspace - throw away all changes
    print-script-step "Removing all changes from git workspace"
    git reset HEAD --hard
    
    ###3. Apply log patch
    print-script-step "Applying log patch from file: $LOG_PATCH..."
    git apply ${LOG_PATCH}
    set +e
    
    ###4. Execute junit for all testcases
    print-script-step "RUNNING JUNIT TESTS WITHOUT CODE CHANGES (WITH LOG PATCH)"
    exec-junit-tests ${SUREFIRE_TEST_CLASS} "wo-codechange" ${BASE_DIR}
    
    ###5. Remove log patch and apply code changes and log patch on top of it
    set -e
    print-script-step "Applying code changes and log patch"
    git reset HEAD --hard
    git apply ${CODE_PATCH}
    git apply ${LOG_PATCH}
    set +e
    
    print-script-step "RUNNING JUNIT TESTS WITH CODE CHANGES (WITH LOG PATCH AND CODE PATCH)"
    exec-junit-tests ${SUREFIRE_TEST_CLASS} "with-codechange" ${BASE_DIR}
    
    grep-in-test-logs ${BASE_DIR}
    print-junit-report ${BASE_DIR}
    #TODO print diff commands (meld) for failed tests
    cleanup
}
