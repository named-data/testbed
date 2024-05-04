import sys

from scripts.render import render

if __name__ == '__main__':
    arguments = sys.argv
    if (len(arguments) < 2):
        raise Exception('No node provided.')
    render(arguments[1])
