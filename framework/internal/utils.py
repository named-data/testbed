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
