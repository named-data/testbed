#!/usr/bin/env python3

import datetime
import sys
import urllib.request
import yaml
import json
import time
import subprocess
import re
import ssl
import socket
import os

from internal.utils import get_files, run_safe
import internal.compose as compose
import internal.conf as conf

def get_timestamp():
    print('Getting timestamp', file=sys.stderr)
    return int(time.time())

def get_revision():
    print('Getting git revision', file=sys.stderr)
    cmd = ['git', 'describe', '--dirty', '--always']
    return subprocess.check_output(cmd, timeout=5).decode('utf-8').strip()

def get_revision_commit():
    print('Getting git revision commit', file=sys.stderr)
    cmd = ['git', 'rev-parse', 'HEAD']
    return subprocess.check_output(cmd, timeout=5).decode('utf-8').strip()

def get_host_info():
    print('Getting host info', file=sys.stderr)
    info = compose.info()
    return {
        'kernel': info.get('KernelVersion', 'N/A'),
        'os': info.get('OperatingSystem', 'N/A'),
        'arch': info.get('Architecture', 'N/A'),
        'docker_version': info.get('ServerVersion', 'N/A'),
    }

def get_services():
    services = {}
    for service in compose.config().get('services', {}):
        print(f"Getting status for {service}", file=sys.stderr)
        compose_status = compose.status(service)
        services[service] = {
            'image': compose_status.get('Image', 'N/A'),
            'status': compose_status.get('Status', 'N/A'),
            'running': compose_status.get('State', False) == 'running',
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

def get_ndnping(routers: dict[str, dict]):
    result = {}
    for host in routers.values():
        host_name: str = host['shortname']
        ping_prefix: str = host['prefix']

        if ping_prefix:
            print(f'ndnping {host_name} with prefix {ping_prefix} -> ', file=sys.stderr, end='', flush=True)

            code, stdout = compose.exec('ndnpingserver', ['ndnping', '-c', '3', '-i', '10', ping_prefix], timeout=10)
            success = code == 0
            if success:
                # Parse duration from ndnping output
                # content from /ndn/ca/utoronto: seq=4544900493281171156 time=91.6838 ms
                durations = []
                for line in stdout.decode('utf-8').splitlines():
                    match = re.search(r'time=([\d.]+)', line)
                    if match:
                        durations.append(float(match.group(1)))

                duration = round(sum(durations) / len(durations), 3) if durations else -1
                result[host_name] = duration
                print(duration, file=sys.stderr)
            else:
                result[host_name] = False
                print('fail', file=sys.stderr)

    return result

def get_tls_expiry(hostname: str, port: int) -> int:
    context = ssl.create_default_context()
    with socket.create_connection((hostname, port), timeout=5) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            cert = ssock.getpeercert()
            expiry_date_str = cert['notAfter']
            expiry_date = datetime.datetime.strptime(expiry_date_str, '%b %d %H:%M:%S %Y %Z')
            return int(expiry_date.timestamp())

def get_tls_status(host: dict):
    print('Getting TLS status', file=sys.stderr)
    result = { 'expiry': None, 'error': None }
    try:
        result['expiry'] = get_tls_expiry(host['ansible_host'], 443)
    except Exception as e:
        result['error'] = str(e)
    return result

def get_ws_tls_status(host: dict) -> bool:
    print('Getting websocket status', file=sys.stderr)
    url = f"https://{host['ansible_host']}/ws/"
    try:
        with urllib.request.urlopen(url, timeout=3):
            return False # got 2xx
    except urllib.request.HTTPError as response:
        return response.code == 426

if __name__ == '__main__':
    config = conf.get()

    # Read host_vars YAML for current host
    host = None
    with open(os.path.join(config.host_vars_path, os.getenv('MANAGED_HOST'))) as stream:
        host = yaml.safe_load(stream)

    # Read routers.json
    routers: dict[str, dict] = None
    with open(os.path.join(config.environment_path, 'dist', 'file-server', 'routers.json')) as stream:
        routers = json.load(stream)

    # Construct status
    status = {
        'timestamp': run_safe(get_timestamp),
        'revision': run_safe(get_revision),
        'revision_commit': run_safe(get_revision_commit),
        'host_info': run_safe(get_host_info),
        'tls': run_safe(get_tls_status, host),
        'ws-tls': run_safe(get_ws_tls_status, host),
        'services': run_safe(get_services),
        'nfd': run_safe(get_nfd),
        'nlsr': run_safe(get_nlsr),
        'ndnping': run_safe(get_ndnping, routers),
    }

    print(json.dumps(status, indent=4), file=sys.stdout)
