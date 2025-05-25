#!/bin/bash

## Catalog id usually comes from: 
# [37] --- Comparing key: ('1.25.0', '7.1.9.1015', '3.3.2', 'chainguard', False) ---
# DIFFERENCES FOUND:
#   catalog id: {'urn:uuid:53624c9c-f138-4968-afcc-1ae398903313'}
# Field: attr.software.Python
#  old: 3.11
#  new: 3.8.17-2.module+el8.9.0+19642+a12b4af6

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <catalog id> <iteration>"
  echo "Usage example: 'urn:uuid:53624c9c-f138-4968-afcc-1ae398903313' 9"
  exit 1
fi

catalog_id="$1"
iteration="$2"
echo "catalog id: $catalog_id"
### Set up variables
TASKDIR=/Users/snemeth/development/my-repos/knowledge-base-private/cloudera/tasks/cde/DEX-17194/testing-results-local/
WORKDIR="$TASKDIR/testing-$(date +%Y%m%d)_$iteration/"
echo "Working directory: $WORKDIR"

grep $catalog_id $WORKDIR/enriched-catalog-entries/sbom_summaries -lR

sbom_summary_file=$(grep $catalog_id $WORKDIR/enriched-catalog-entries/sbom_summaries -lR)
sbom_summary_python3_version=$(jq '.container.python3Version' $sbom_summary_file)

echo "sbom summary file: $sbom_summary_file"
echo "--> Python3 version from SBOM summary file: $sbom_summary_python3_version"


CATALOG_JSON="$WORKDIR/catalog-entries.json"
echo "Generated catalog-entries.json: $CATALOG_JSON"


### Extract catalog data
entry_json=$(jq --arg id $catalog_id '.[] | select(.id==$id)' $CATALOG_JSON)
# echo "Entry: $entry_json"

if [[ -z "$entry_json" ]]; then
  echo "Error: Catalog entry not found with id: $catalog_id"
  exit 1
fi

python_version=$(jq '.attr.software.Python' <<< "$entry_json")
echo "--> Python3 version from catalog entry: $python_version"

repo=$(jq '.images.Spark.repo' <<< "$entry_json" | tr -d '"')
tag=$(jq '.images.Spark.tag' <<< "$entry_json" | tr -d '"')
docker_image="${repo}:${tag}"
echo "Docker image: $docker_image"


### Pull docker image and run command to verify python

docker pull $docker_image
# docker run -it --entrypoint /bin/sh $docker_image

echo "--> Python3 version from image $docker_image"
docker run -it --entrypoint /bin/sh $docker_image  -c "python3 --version" 2>/dev/null



### Grepping
load_release_sh_out=$WORKDIR/load_release_entries_sh_output.txt
echo "Grepping in result file: $load_release_sh_out"

grep -n "\*\*\*" $load_release_sh_out | grep --color=auto "$catalog_id"
