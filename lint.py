import yaml

import framework.utils as utils
import framework.conf as conf

from typing import Any

# Read config file
config = conf.get()

def check_type(key: str, value: Any, typ: str, path: str):
    """
    Validate a value against a type.
     - value: The value to validate
     - typ: The type to validate against (string, number, boolean, list, dict)
    """

    valid_type = False
    if typ == 'string':
        valid_type = isinstance(value, str)
    elif typ == 'number':
        valid_type = isinstance(value, int) or isinstance(value, float)
    elif typ == 'boolean':
        valid_type = isinstance(value, bool)
    elif typ == 'list':
        valid_type = isinstance(value, list)
    elif typ == 'dict':
        valid_type = isinstance(value, dict)
    else:
        print(f"WARNING: Unknown type '{typ}' for key '{key}'")

    if not valid_type:
        print(f"WARNING: Key '{key}' has invalid type (got '{type(value).__name__}', epxected '{typ}') in file: {path}")

def lint(path: str):
    # Read YAML file
    content = None
    with open(path, 'r') as stream:
        try:
            content = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print("Error reading YAML file: ", path, exc)
            return

    # Create an ordered dict with the same order as the config file
    ordered_content = {}
    for key in config.variables:
        if key in content:
            check_type(key, content[key], config.variables[key], path)
            ordered_content[key] = content[key]
        else:
            print(f"WARNING: Missing key '{key}' in file: {path}")

    # Check for any unknown keys
    for key in content:
        if key not in config.variables:
            print(f"WARNING: Unknown key '{key}' in file: {path}")
            ordered_content[key] = content[key]

    # Sort keys by name and write the file back
    with open(path, 'w') as stream:
        yaml.dump(ordered_content, stream, sort_keys=False)

if __name__ == '__main__':
    for file in utils.get_files(config.host_vars_path):
        lint(file)