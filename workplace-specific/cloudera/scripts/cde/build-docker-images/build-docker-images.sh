#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

set -e
$DIR/build717.sh
$DIR/build718.sh
$DIR/build719.sh
$DIR/build7215.sh
$DIR/build7216.sh
$DIR/build7218.sh
set +e