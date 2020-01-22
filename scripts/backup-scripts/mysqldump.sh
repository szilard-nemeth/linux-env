#!/bin/bash

#TODO Move to https://github.com/szilard-nemeth/linux-backup-scripts
#mysqldump-multiline-sed
##https://stackoverflow.com/questions/15750535/using-mysqldump-to-format-one-insert-per-line
function mysqldump-commit() {
    cd my_git_directory/
    
    #Windows version
    #MYSQL_DUMP_BIN='/c/Program\ Files\ (x86)/MySQL/MySQL\ Workbench\ CE\ 6.1.6/'
    MYSQL_DUMP_BIN="/usr/bin/mysqldump"
    
    ARGS="--host=myhostname --user=myusername --password=mypassword --opt --skip-dump-date"
    #ARGS="--host=localhost --user=root --password=root --opt --skip-dump-date"
    DB="homedb"
    
    $MYSQL_DUMP_BIN $ARGS --database $DB | sed 's$VALUES ($VALUES\n($g' | sed 's$),($),\n($g' > sqldump.sql
    
    #Make git commit
    git fetch origin master
    git merge origin/master
    git add mydatabase.sql
    git commit -m "Daily backup."
    git push origin master
}