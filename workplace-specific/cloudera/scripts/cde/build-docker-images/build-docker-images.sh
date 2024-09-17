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

echo "Grepping for 7.1.7 images"
docker images | grep 7.1.7 | grep cloudera/dex | grep "cde-"

echo "Grepping for 7.1.8 images"
docker images | grep 7.1.8 | grep cloudera/dex | grep "cde-"

echo "Grepping for 7.1.9 images"
docker images | grep 7.1.9 | grep cloudera/dex | grep "cde-"

echo "Grepping for 7.2.15 images"
docker images | grep 7.2.15 | grep cloudera/dex | grep "cde-"

echo "Grepping for 7.2.16 images"
docker images | grep 7.2.16 | grep cloudera/dex | grep "cde-"

echo "Grepping for 7.2.18 images"
docker images | grep 7.2.18 | grep cloudera/dex | grep "cde-"