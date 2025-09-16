## Filter by defaultRuntime=true
# Description: Filters for catalog entries where 'defaultRuntime' is true and displays key attributes.
# Usage: filter_default_runtime <catalog-entries.json>
function _dex-rtcatalog-filter-default-runtime() {
  if [[ -z "$1" ]]; then
    echo "Usage: _dex-rtcatalog-filter-default-runtime <catalog-entries.json>"
    return 1
  fi
  jq '[.[]
    | select(.defaultRuntime == true)
    | {
        id,
        cdeVersion: .attr.cdeVersion,
        datalakeVersion: .attr.datalakeVersion,
        sparkVersion: .attr.sparkVersion,
        osName: .attr.osName,
        defaultRuntime,
        gpuSupport
      }
  ]
  | sort_by(.cdeVersion, .datalakeVersion)' "$1"
}

function dex-rtcatalog-filter-default-runtime() {
  _dex-rtcatalog-filter-default-runtime $DEX_RTCATALOG_FILE
}


## Filter by cdeVersion
# Description: Filters for catalog entries with a specific 'cdeVersion'.
# Usage: filter_cde_version <cde_version> <catalog-entries.json>
function _dex-rtcatalog-filter-cde-version() {
  local cde_version="$1"
  local file_path="$2"
  if [[ -z "$cde_version" || -z "$file_path" ]]; then
    echo "Usage: _dex-rtcatalog-filter-cde-version <cde_version> <catalog-entries.json>"
    return 1
  fi
  jq --arg version "$cde_version" '[.[]
    | select(.attr.cdeVersion == $version)
    | {
        id,
        cdeVersion: .attr.cdeVersion,
        datalakeVersion: .attr.datalakeVersion,
        sparkVersion: .attr.sparkVersion,
        osName: .attr.osName,
        defaultRuntime
      }
  ]
  | sort_by(.cdeVersion, .datalakeVersion)' "$file_path"
}

function dex-rtcatalog-filter-cde-version() {
  local cde_version="$1"
  if [[ -z "$cde_version" ]]; then
    echo "Usage: dex-rtcatalog-filter-cde-version <cde_version>"
    return 1
  fi
  _dex-rtcatalog-filter-cde-version $cde_version $DEX_RTCATALOG_FILE
}


## Filter multiple attributes
# Description: Filters for catalog entries matching both 'cdeVersion' and 'sparkVersion'.
# Usage: filter_multiple_attributes <cde_version> <spark_version> <catalog-entries.json>
function _dex-rtcatalog-filter-multiple-attributes() {
  local cde_version="$1"
  local spark_version="$2"
  local file_path="$3"
  if [[ -z "$cde_version" || -z "$spark_version" || -z "$file_path" ]]; then
    echo "Usage: _dex-rtcatalog-filter-multiple-attributes <cde_version> <spark_version> <catalog-entries.json>"
    return 1
  fi
  jq --arg cde_ver "$cde_version" --arg spark_ver "$spark_version" '[.[]
    | select(.attr.cdeVersion == $cde_ver and .attr.sparkVersion == $spark_ver)
    | {
        id,
        cdeVersion: .attr.cdeVersion,
        datalakeVersion: .attr.datalakeVersion,
        sparkVersion: .attr.sparkVersion,
        osName: .attr.osName,
        defaultRuntime
      }
  ]
  | sort_by(.cdeVersion, .datalakeVersion)' "$file_path"
}

function dex-rtcatalog-filter-multiple-attributes() {
  local cde_version="$1"
  local spark_version="$2"
  if [[ -z "$cde_version" || -z "$spark_version" ]]; then
    echo "Usage: dex-rtcatalog-filter-multiple-attributes <cde_version> <spark_version>"
    return 1
  fi
  _dex-rtcatalog-filter-multiple-attributes $cde_version $spark_version $DEX_RTCATALOG_FILE
}


## Querying all images with a specific Datalake version in the repo string
# Description: Filters for entries where the Spark image repo URL contains a specific Datalake version string.
# Usage: filter_by_datalake_repo <datalake_version_part> <catalog-entries.json>
function _dex-rtcatalog-filter-by-datalake-repo() {
  local datalake_version="$1"
  local file_path="$2"
  if [[ -z "$datalake_version" || -z "$file_path" ]]; then
    echo "Usage: _dex-rtcatalog-filter-by-datalake-repo <datalake_version_part> <catalog-entries.json>"
    return 1
  fi
  jq --arg dl_ver "$datalake_version" '[.[]
    | select(.images.Spark.repo | contains($dl_ver))
    | {
        id,
        cdeVersion: .attr.cdeVersion,
        datalakeVersion: .attr.datalakeVersion,
        sparkVersion: .attr.sparkVersion,
        osName: .attr.osName,
        defaultRuntime,
        sparkrepo: .images.Spark.repo
      }
  ]
  | sort_by(.cdeVersion, .datalakeVersion)' "$file_path"

}

function dex-rtcatalog-filter-by-datalake-repo() {
  local datalake_version="$1"
  if [[ -z "$datalake_version" ]]; then
    echo "Usage: dex-rtcatalog-filter-by-datalake-repo <datalake_version_part>"
    return 1
  fi
  _dex-rtcatalog-filter-by-datalake-repo  
} 

---

## Querying images for CDE and Datalake versions
# Description: Filters for entries with a specific 'cdeVersion' and a partial match on 'datalakeVersion'.
# Usage: filter_by_cde_and_datalake <cde_version> <datalake_version_part> <catalog-entries.json>
function _dex-rtcatalog-filter-by-cde-and-datalake() {
  local cde_version="$1"
  local datalake_version_part="$2"
  local file_path="$3"
  if [[ -z "$cde_version" || -z "$datalake_version_part" || -z "$file_path" ]]; then
    echo "Usage: _dex-rtcatalog-filter-by-cde-and-datalake <cde_version> <datalake_version_part> <catalog-entries.json>"
    return 1
  fi
  jq --arg cde_ver "$cde_version" --arg dl_part "$datalake_version_part" '[.[]
    | select(.attr.cdeVersion == $cde_ver and (.attr.datalakeVersion | contains($dl_part)))
    | {
        id,
        cdeVersion: .attr.cdeVersion,
        datalakeVersion: .attr.datalakeVersion,
        sparkVersion: .attr.sparkVersion,
        osName: .attr.osName,
        defaultRuntime,
        sparkrepo: .images.Spark.repo
      }
  ]
  | sort_by(.cdeVersion, .datalakeVersion)' "$file_path"
}

function dex-rtcatalog-filter-by-cde-and-datalake() {
  local cde_version="$1"
  local datalake_version_part="$2"
  if [[ -z "$cde_version" || -z "$datalake_version_part" ]]; then
    echo "Usage: _dex-rtcatalog-filter-by-cde-and-datalake <cde_version> <datalake_version_part>"
    return 1
  fi
  _dex-rtcatalog-filter-by-cde-and-datalake $cde_version $datalake_version $DEX_RTCATALOG_FILE
}