#!/usr/bin/env bash

function mongo-rename-db {
  local old_db_name="$1"
  local new_db_name="$2"
  set -x
  mongodump -h localhost:27017 -u admin -d $old_db_name --authenticationDatabase admin -o mongodump/
  mongorestore -h localhost:27017 -u admin -d $new_db_name --authenticationDatabase admin mongodump/$old_db_name
  set +x
}