import os
import hashlib
import sys

def get_files(path: str, recursive: bool = False):
    """
    Arguments:
    - path: path to the directory to get all files/templates from

    This function takes in the path to a directory, and returns all files
    in the directory as a list.
    """

    for root, dirs, files in os.walk(path):
        for file in files:
            yield os.path.join(root, file)

        if not recursive:
            break

def hash_file(path: str) -> str:
    """
    Arguments:
    - template_path: path to the template whose hash is desired

    This function takes in a path to a template, and returns the md5 hash of
    the contents of the file.
    """
    return hashlib.md5(open(path, 'rb').read()).hexdigest()

def ndn_cert_name(text: str) -> str:
    """Read the full certificate name from an ndn-cxx base64 certificate."""
    import base64
    from ndn.app_support.security_v2 import parse_certificate
    from ndn.encoding import Name

    wire = base64.b64decode(''.join(text.split()), validate=True)
    return Name.to_str(parse_certificate(wire).name)

def ndn_lvs_name(name: str) -> str:
    """Encode an NDN name as literal components in an LVS schema."""
    import json
    from ndn.encoding import Component, Name

    return '/'.join(json.dumps(Component.to_str(comp)) for comp in Name.normalize(name))

def read_dotenv(file='.env') -> dict[str, str]:
    """
    This function reads a .env file and returns a dictionary of the key-value
    """

    if not os.path.exists(file):
        return {}

    dotenv = {}
    with open(file) as f:
        for line in f:
            if not line.strip() or line.startswith('#'):
                continue
            key, value = line.strip().split('=', 1)
            dotenv[key] = value
    return dotenv

def run_safe(func, *args, **kwargs):
    """Run a function and catch any exceptions that occur"""

    try:
        return func(*args, **kwargs)
    except Exception as e:
        print(f"Error running status function {func.__name__}: {e}", file=sys.stderr)
        return None
