result=`git log $1..$2 --oneline --no-merges | grep -e '[A-Z]\+-[0-9]\+' -o`
gitlog=`git log $1 --oneline --no-merges`

for value in $result
do
  if ! grep -q "$value" <<< "$gitlog"; then
    echo "$value exists on branch=$2, but not exist on $1"
  fi
done
