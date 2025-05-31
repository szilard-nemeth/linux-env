#!/usr/bin/python3

import json
import logging
import sys
import os

DEBUG_ENABLED = True
LOG_FILE = '/tmp/compare-catalog.log'

def configure_logging(debug=False):
    level = logging.DEBUG if debug else logging.INFO
    fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    logging.basicConfig(filename=LOG_FILE,
                        filemode="w",
                        format=fmt,
                        level=level)

def load_json(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def make_key(entry):
    spark_base_version = ".".join(entry['attr']['sparkVersion'].split('.')[:3])
    return (
        entry['attr'].get('cdeVersion', ''),
        entry['attr'].get('datalakeVersion', ''),
        spark_base_version,
        entry['attr'].get('osName', ''),
        entry['gpuSupport']
    )

def map_by_key(json_array):
    result_map = {make_key(entry): entry for entry in json_array}
    entry_to_id_map = {make_key(entry): entry["id"] for entry in json_array}
    return result_map, entry_to_id_map

def compare_dicts(d1, d2, prefix=""):
    diffs = []
    keys = set(d1.keys()).union(d2.keys())
    for key in keys:
        v1 = d1.get(key)
        v2 = d2.get(key)

        full_key = f"{prefix}.{key}" if prefix else key

        if isinstance(v1, dict) and isinstance(v2, dict):
            diffs.extend(compare_dicts(v1, v2, full_key))
        elif v1 != v2:
            diffs.append((full_key, v1, v2))
    return diffs



def compare_mapped_json(map1, map2, entry_to_id_map1, entry_to_id_map2):
    #Sort by versions
    all_keys = sorted(set(map1.keys()).union(set(map2.keys())), key=lambda k: (k[0], k[1]))

    for idx, key in enumerate(all_keys):
        val1 = map1.get(key)
        val2 = map2.get(key)

        _print(f"[{idx}] --- Comparing key: {key} ---")
        if val1 and val2:
            diffs = compare_dicts(val1, val2)
            if not diffs:
                _print("MATCH")
            else:
                _print("DIFFERENCES FOUND:")

                # Print catalog ids first
                old_catalog_id = {entry_to_id_map1[key]}
                new_catalog_id = {entry_to_id_map2[key]}
                if old_catalog_id != new_catalog_id:
                    _print(f"  old catalog id: {entry_to_id_map1[key]}")
                    _print(f"  new catalog id: {entry_to_id_map2[key]}")
                else:
                    _print(f"  catalog id: {old_catalog_id}")

                for field, v1, v2 in diffs:
                    #Don't print differences in these fields as this will be changing in all the entries and too much verbose
                    if  any(val in field for val in ["digest", "id", "attr.sparkVersion", ".tag"]):
                        pass
                    else :
                        _print(f"Field: {field}")
                        _print(f"  old: {v1}")
                        _print(f"  new: {v2}")
        elif val1:
            _print("Only in File1")
        elif val2:
            _print("Only in File2")
        _print("")


def check_args():
    if len(sys.argv) != 3:
        _print("Error: Exactly 2 parameters are required.")
        _print("Usage: python script.py <old catalog> <new catalog>")
        sys.exit(1)

    file1, file2 = sys.argv[1], sys.argv[2]

    for file in (file1, file2):
        if not os.path.isfile(file):
            _print(f"Error: '{file}' is not a valid file.")
            sys.exit(1)

    # print("Both files are valid.")
    return file1, file2

def _print(msg, debug=False):
    print(msg)

    if debug:
        logging.getLogger().debug(msg)
    else:
        logging.getLogger().info(msg)

if __name__ == "__main__":
    # old_data = load_json('/Users/snemeth/Downloads/catalog-entries.json') # File1
    # new_data = load_json('/Users/snemeth/Downloads/catalog-entries-dale.json') # File2
    configure_logging(debug=DEBUG_ENABLED)


    old_catalog, new_catalog = check_args()
    _print(f"Old catalog file: {old_catalog} (File 1)")
    _print(f"New catalog file: {new_catalog} (File 2)")
    _print(f"Logging to file: {LOG_FILE}")

    old_data = load_json(old_catalog) # File1
    new_data = load_json(new_catalog) # File2
    
    map1, entry_to_id_map1 = map_by_key(old_data)
    map2, entry_to_id_map2 = map_by_key(new_data)

    compare_mapped_json(map1, map2, entry_to_id_map1, entry_to_id_map2)