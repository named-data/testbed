"""Resolve tracked host selection for shell maintenance jobs."""
import argparse
from os import getenv

from internal import conf
from internal.utils import read_dotenv

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--service', choices=list(conf.get().services))
args = parser.parse_args()
if args.service:
    node = getenv('MANAGED_HOST', read_dotenv().get('MANAGED_HOST'))
    print(int(conf.service_enabled(conf.get().services[args.service], node)))
else:
    print(conf.compose_profiles())
