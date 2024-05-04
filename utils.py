import os
import hashlib

def get_files(path: str) -> str:
    """
    Arguments:
    - path: path to the directory to get all files/templates from

    This function takes in the path to a directory, and returns all files
    in the directory as a list.
    """

    nodes = [os.path.join(path, f) for f in os.listdir(path)]
    files = [file for file in nodes if os.path.isfile(file)]

    return files

def hash_file(path: str) -> str:
    """
    Arguments:
    - template_path: path to the template whose hash is desired

    This function takes in a path to a template, and returns the md5 hash of
    the contents of the file.
    """
    return hashlib.md5(open(path, 'rb').read()).hexdigest()
