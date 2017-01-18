#!/bin/bash
#ps cax | grep $1 > /dev/null
ps auxww | grep $1 > /dev/null
if [ $? -eq 0 ]; then
  echo "Process is running."
else
  echo "Process is not running."
fi

