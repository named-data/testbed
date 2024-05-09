import os
import sys
import yaml

import internal.utils as utils
import internal.conf as conf

from typing import Any

# Read config file
config = conf.get()

# Validation of links
NEIGHBORS = {}

# Configuration has errors
HAS_ERRORS = False
def log_error(message: str):
    print(message, file=sys.stderr)
    global HAS_ERRORS
    HAS_ERRORS = True

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
        log_error(f"WARNING: Unknown type '{typ}' for key '{key}'")

    if not valid_type:
        log_error(f"WARNING: Key '{key}' has invalid type (got '{type(value).__name__}', epxected '{typ}') in file: {path}")

def lint(path: str):
    node_name = os.path.basename(path)

    # Read YAML file
    raw_content = None
    content = None
    with open(path, 'r') as stream:
        try:
            raw_content = stream.read()
            content = yaml.safe_load(raw_content)
        except yaml.YAMLError as exc:
            log_error("Error reading YAML file: ", path, exc)
            return

    # Create an ordered dict with the same order as the config file
    ordered_content = {}
    for key, typ in config.variables.items():
        # Check if optional key
        is_optional = False
        if typ[0] == '?':
            is_optional = True
            typ = typ[1:]

        # Check if key is present
        if key in content:
            check_type(key, content[key], typ, path)
            ordered_content[key] = content[key]
        elif not is_optional:
            log_error(f"WARNING: Missing key '{key}' in file: {path}")

    # Check for any unknown keys
    for key in content:
        if key not in config.variables:
            log_error(f"WARNING: Unknown key '{key}' in file: {path}")
            ordered_content[key] = content[key]

    # Sort keys by name and check file
    raw_ordered_content = yaml.dump(ordered_content, sort_keys=False)
    if raw_content != raw_ordered_content:
        log_error(f"WARNING: File '{path}' was incorrectly formatted or last errors.")

    # Write the file back
    with open(path, 'w') as stream:
        stream.write(raw_ordered_content)

    # Validate neighbor pairs
    for name, params in ordered_content['neighbors'].items():
        flip = name + ':' + node_name
        if flip in NEIGHBORS:
            if NEIGHBORS[flip] != params:
                log_error(f"ERROR: Parameter mismatch in link '{flip}' ({path})")
            del NEIGHBORS[name + ':' + node_name]
            continue
        NEIGHBORS[node_name + ':' + name] = params

if __name__ == '__main__':
    for file in utils.get_files(config.host_vars_path):
        lint(file)

    # Any entries that remain are incomplete
    for invalid in NEIGHBORS:
        log_error(f"ERROR: Neighbor '{invalid}' is not symmetric")

    sys.exit(1 if HAS_ERRORS else 0)