#! /bin/bash

## INTENDED TO BE EXECUTED ON A YCLOUD MACHINE

DEX_HOME="/home/systest/dex"



### 1. Generate sboms
cd $DEX_HOME/build-tools/rtcatalog
python3 get_release_sbom.py --release 1.25.0-b78 --image-filter spark --save-disk-space
python3 get_release_sbom.py --release 1.25.0-b78 --image-filter livy --save-disk-space
python3 get_release_sbom.py --release 1.25.0-b78 --image-filter python-builder --save-disk-space


### 2. Build catalog server

cd $DEX_HOME/cmd
# rm -rf build; mkdir build
make catalog-server

### 3. Prepare sboms dir to only contain relevant entries
cd $DEX_HOME/build-tools/rtcatalog/
mv sboms sbom_orig 
mkdir sbom

# JSON_FILE="sbom_orig/docker-private.infra.cloudera.com_cloudera_dex_dex-spark-runtime-3.2.3-7.1.7.3016_1.25.0-b78.json";
# echo "JSON file: $JSON_FILE";
# cp $JSON_FILE sbom/

find ./sbom_orig -type f -name "*3.2.3-7.1.7.3016_1.25.0-b78*" -exec cp {} sbom/ \;
find ./sbom_orig -type f -name "*runtime-python-builder*7.1.7.3016_1.25.0-b78*" -exec cp {} sbom/ \;
ls -la sbom


### 4. Run catalog server
$DEX_HOME/build-tools/rtcatalog/load_release_entries.sh



### 5. Check results
ls -la enriched-catalog-entries/
cat enriched-catalog-entries/cde-1.25.0-dl-7.1.7.3016-chainguard-20230214-spark-3.2.3-java-11-python-3.9.json
ls -la enriched-catalog-entries/sbom_summaries/
cat enriched-catalog-entries/sbom_summaries/docker-private.infra.cloudera.com_cloudera_dex_dex-spark-runtime-3.2.3-7.1.7.3016_1.25.0-b78.json
