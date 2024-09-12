#!/usr/bin/python3

import os
import sys
from typing import Set

BASEDIR = "~/development/my-repos/project-data/run-configurations"
KNOWN_IDES = {"pycharm", "intellij"}


def parse_project_and_run_config_name(base_dir, path):
    path = os.path.relpath(path, base_dir)
    split = path.split(os.sep)
    if ".run" in split:
        split.remove(".run")
    if len(split) != 3:
        raise ValueError(f"Unexpected length. List should contain <IDE name>, <project name>, <run config name>, actual value: {split}" )
    return split

def parse_script_and_params(path):
    from lxml import objectify
    tree = objectify.parse(path)

    type = tree.getroot().configuration.attrib["type"]
    if type != "PythonConfigurationType":
        return None, None
    # PythonConfigurationType
    options = {el.attrib["name"]: el.attrib["value"] for el in tree.getroot().configuration.iterchildren(tag='option')}
    # print(config)
    return options["SCRIPT_NAME"], options["PARAMETERS"]


def print_run_configs(filter: Set[str] = None, only_commands=False, print_warnings=False):
    base_dir = BASEDIR
    if "~" in BASEDIR:
        base_dir = os.path.expanduser(BASEDIR)
    if not os.path.exists(base_dir):
        raise ValueError(f"Cannot find basedir: {base_dir}")

    for subdir, dirs, files in os.walk(base_dir):
        for file in files:
            filepath = subdir + os.sep + file
            if filepath.endswith(".xml"):
                _, project_name, run_config_name = parse_project_and_run_config_name(base_dir, filepath)
                if filter and project_name not in filter:
                    if print_warnings:
                        print(f"SKIPPED PROJECT '{project_name}' PER FILTER")
                    continue

                script, params = parse_script_and_params(filepath)
                if script and params:
                    cmd = f"{script} {params}"
                    if only_commands:
                        print(cmd)

                    else:
                        print(f"PROJECT: {project_name}")
                        print(f"RUN CONFIG FILE: '{filepath}'")
                        print(f"RUN CONFIG: {run_config_name}")
                        print(f"COMMAND: {cmd}\n\n")
                else:
                    if print_warnings:
                        print(f"Dropped config as type != PythonConfigurationType: {filepath}")


if __name__ == '__main__':
    if len(sys.argv) not in (1, 2):
        raise ValueError("Invalid arguments! Need to be called without argument or one argument for project filter!")

    project_filter = None
    if len(sys.argv) == 2:
        project_filter = {sys.argv[1]}
    print_run_configs(filter=project_filter, only_commands=True)