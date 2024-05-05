import argparse

from framework.render import render

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='NDN Testbed',
        description='Manages the current node on the testbed')

    parser.add_argument('node', type=str, help='The name of the current node to manage')
    parser.add_argument('--dry', action='store_true', help='Dry run mode (no service management)')

    args = parser.parse_args()

    render(args.node, dry=args.dry)
