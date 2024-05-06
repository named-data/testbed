import argparse
from os import getenv

from internal.render import render

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='NDN Testbed',
        description='Manages the current node on the testbed')

    parser.add_argument('node', nargs='?', type=str, help='The name of the current node to manage')
    parser.add_argument('--dry', action='store_true', help='Dry run mode (no service management)')

    args = parser.parse_args()

    if not args.node:
        args.node = getenv('MANAGED_HOST')

    if not args.node:
        print('No node specified. Please provide a node or define MANAGED_HOST in the environment')

    render(args.node, dry=args.dry)
