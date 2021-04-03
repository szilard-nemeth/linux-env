function myrepos-rm-pythoncommons() {
  #Original alias
  #mkdir -p /tmp/pcrm/;myrepos-list-pythoncommons | xargs -t -I % sh -c 'XARGSFILE=%;mkdir -p /tmp/pcrm/$XARGSFILE && mv $XARGSFILE /tmp/pcrm/$XARGSFILE'
  #xargs can't handle longer commands than 255 bytes and if it exceeds this limit, placeholders will not be replaced!
  #Solution: cd into dir, then execute command, then cd back to prev dir to have a shorter command

	IFS=$'\n';
	for line in `myrepos-list-pythoncommons | awk -F '/venv' '{print $1,$2}'`; do
		IFS=' ' read -r -A arr <<< "$line"
		#set -x
		#It's safer to always remove the dir /tmp/prcrm/ rather then removing the results of the above command list-pythoncommons command
		#Removing it in every iteration avoids "Directory not empty" errors from mv
		rm -rf "/tmp/pcrm/"
		local proj_dir="${arr[1]}"
		local result_dir="${arr[2]}"
    echo "Removing python-commons from $proj_dir/venv"
		#Cd into dir to make command shorter
		cd $proj_dir
		dest_path="/tmp/pcrm/$result_dir"
		mkdir -p $dest_path
		mv "./venv/$result_dir" $dest_path
		#set +x
		IFS=$'\n';
	done
}

function myrepos-reset-pythoncommons() {
  echo "Pushing python-commons"
  cd $PYTHON_COMMONS_ROOT; git push

  echo "Removing python-commons from projects"
  myrepos-rm-pythoncommons

  echo "Listing installed python-commons (Should give empty results): "
  myrepos-list-pythoncommons

  echo "Reinstalling python-commons in each project"
  myrepos-installpythoncommons

  echo "Listing installed python-commons:"
  myrepos-list-pythoncommons
}