import os
import hashlib

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
