import sys

import yaml
import difflib

def diff_yaml_files(file1_path, file2_path):
    """
    Compares two YAML files and prints a unified diff.
    """
    try:
        with open(file1_path, 'r') as file1, open(file2_path, 'r') as file2:
            data1 = yaml.safe_load(file1)
            data2 = yaml.safe_load(file2)

        # Convert the loaded data back to a string with a consistent format
        # This is key for line-by-line comparison
        yaml_string1 = yaml.dump(data1, sort_keys=True)
        yaml_string2 = yaml.dump(data2, sort_keys=True)

        # Get the lines to compare
        lines1 = yaml_string1.splitlines(keepends=True)
        lines2 = yaml_string2.splitlines(keepends=True)

        # Generate the unified diff
        diff = difflib.unified_diff(lines1, lines2, fromfile=file1_path, tofile=file2_path)

        # Print the diff
        print("".join(diff))

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")

import yaml

def structural_diff_files(file1_path, file2_path, list_key='files', item_key='path'):
    """
    Performs a structural diff on a specific list within two YAML files,
    identifying missing and added items based on a unique key.

    Args:
        file1_path (str): The path to the first YAML file.
        file2_path (str): The path to the second YAML file.
        list_key (str): The key for the list you want to compare (e.g., 'files').
        item_key (str): The key within each list item that serves as a unique identifier (e.g., 'path').
    """
    try:
        with open(file1_path, 'r') as f1, open(file2_path, 'r') as f2:
            data1 = yaml.safe_load(f1)
            data2 = yaml.safe_load(f2)

        # Access the list of items from each file, or an empty list if not found
        list1 = data1.get('resource', {}).get(list_key, [])
        list2 = data2.get('resource', {}).get(list_key, [])

        i = 1
        for d in [data1, data2]:
            name = d.get('resource').get("name")
            created = d.get('resource').get("created")
            modified = d.get('resource').get("modified")
            print(f"Resource #{i} name: {name}, created: {created}, modified: {modified}")
            i += 1

        # Create sets of unique identifiers (e.g., file paths)
        set1 = {item.get(item_key) for item in list1 if item.get(item_key)}
        set2 = {item.get(item_key) for item in list2 if item.get(item_key)}

        # Find the differences
        missing_in_2 = set1 - set2
        added_in_2 = set2 - set1

        # Report the results
        if not missing_in_2 and not added_in_2:
            print("No structural differences found in the 'files' list.")
        else:
            if missing_in_2:
                print(f"🚨 Missing in the second file (resource: {data2.get('resource').get('name')}):")
                for item in sorted(list(missing_in_2)):
                    print(f"- {item}")
            if added_in_2:
                print(f"✨ Added to the second file (resource: {data2.get('resource').get('name')}):")
                for item in sorted(list(added_in_2)):
                    print(f"- {item}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")

def test_structural():
    # Example Usage:
    # Assuming you have two YAML files, 'file1.yaml' and 'file2.yaml',
    # where file1 has the content you provided and file2 is a slightly
    # modified version (e.g., one file removed and another added).

    # Create a sample file with some changes for demonstration
    with open('file1.yaml', 'w') as f:
        f.write("""
    resource:
      name: PipelineResource-CAU_ETL-1712225495297
      type: files
      files:
        - path: file_A.txt
        - path: file_B.txt
        - path: file_C.txt
        """)

    with open('file2.yaml', 'w') as f:
        f.write("""
    resource:
      name: PipelineResource-CAU_ETL-1712225495297
      type: files
      files:
        - path: file_A.txt
        - path: file_C.txt
        - path: file_D.txt
        """)

    # Now run the function
    structural_diff_files('file1.yaml', 'file2.yaml')


def test():
    # Example usage:
    # Create two sample YAML files for demonstration
    with open('file1.yaml', 'w') as f:
        f.write("""
    name: John Doe
    age: 30
    city: New York
    skills:
      - Python
      - JavaScript
      - Docker
    """)

    with open('file2.yaml', 'w') as f:
        f.write("""
    name: John Doe
    age: 31
    city: New York
    skills:
      - Python
      - JavaScript
      - Kubernetes
      - Ansible
    """)

    diff_yaml_files('file1.yaml', 'file2.yaml')

if __name__ == '__main__':
    # Initial implementation from: https://gemini.google.com/app/1ee7d6f7f08b4f56
    args = sys.argv
    # print(args)
    print(f"File 1: {args[1]}")
    print(f"File 2: {args[2]}")
    structural_diff_files(args[1], args[2])