#!/usr/bin/env python3

import sys
import yaml
import json
import time
import subprocess

from internal.utils import get_files, run_safe
import internal.compose as compose
import internal.conf as conf

def get_timestamp():
    return int(time.time())

def get_revision():
    cmd = ['git', 'describe', '--dirty', '--always']
    return subprocess.check_output(cmd, timeout=5).decode('utf-8').strip()

def get_services():
    services = {}
    for service in compose.config().get('services', {}):
        print(f"Getting status for {service}", file=sys.stderr)
        compose_status = compose.status(service)
        services[service] = {
            'image': compose_status.get('Image', 'N/A'),
            'status': compose_status.get('Status', 'N/A'),
        }
    return services

def get_nfd():
    print('Getting NFD status', file=sys.stderr)
    nfd = {}
    _, stdout = compose.exec('nfd', ['nfdc', 'status'], timeout=5)
    for line in stdout.decode('utf-8').splitlines():
        line = line.strip()
        if '=' in line:
            name, value = line.split('=', 1)
            nfd[name] = value
    return nfd

def get_nlsr():
    print('Getting NLSR status', file=sys.stderr)
    nlsr = {}
    _, stdout = compose.exec('nlsr', ['nlsr', '-V'], timeout=5)
    nlsr['version'] = stdout.decode('utf-8').strip()
    return nlsr

def get_ndnping():
    config = conf.get()
    result = {}

    for host_path in get_files(config.host_vars_path):
        host_name = host_path.split('/')[-1]
        ping_prefix: str | None = None

        with open(host_path) as stream:
            host = yaml.safe_load(stream)
            ping_prefix = host['default_prefix']

        if ping_prefix:
            print(f'ndnping {host_name} with prefix {ping_prefix} -> ', file=sys.stderr, end='', flush=True)

            # TODO: This doesn't measure the network time but the execution time
            t_start = time.time()
            code, _ = compose.exec('ndnpingserver', ['ndnping', '-c', '3', '-i', '10', ping_prefix], timeout=10)
            success = code == 0
            duration = (time.time() - t_start) * 1000
            result[host_name] = duration if success else None
            print(duration if success else 'fail', file=sys.stderr)

    return result


if __name__ == '__main__':
    status = {
        'timestamp': run_safe(get_timestamp),
        'revision': run_safe(get_revision),
        'services': run_safe(get_services),
        'nfd': run_safe(get_nfd),
        'nlsr': run_safe(get_nlsr),
        'ndnping': run_safe(get_ndnping),
    }

    print(json.dumps(status, indent=4))
