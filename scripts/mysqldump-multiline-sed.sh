##https://stackoverflow.com/questions/15750535/using-mysqldump-to-format-one-insert-per-line

#!/bin/bash

cd my_git_directory/

ARGS="--host=myhostname --user=myusername --password=mypassword --opt --skip-dump-date"
/usr/bin/mysqldump $ARGS --database mydatabase | sed 's$VALUES ($VALUES\n($g' | sed 's$),($),\n($g' > mydatabase.sql

git fetch origin master
git merge origin/master
git add mydatabase.sql
git commit -m "Daily backup."
git push origin master