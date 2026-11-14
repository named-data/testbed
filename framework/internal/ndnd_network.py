"""Initialize BIER and the local NFD–NDNd gateway after service startup."""

import json
import os
from pathlib import Path
import re
import subprocess
import time

import yaml

from . import conf


def router_indices(hosts):
    routers = {}
    for name, host in hosts.items():
        if not host.get('ndnd_enabled', False):
            continue
        index = host.get('ndnd_bier_index')
        if type(index) is not int or index < 0:
            raise ValueError(f'{name}: ndnd_bier_index must be a non-negative integer')
        prefix = host['ndnd_router_prefix']
        if index in routers or prefix in routers.values():
            raise ValueError(f'{name}: duplicate NDNd router prefix or BIER index')
        routers[index] = prefix
    return routers


def run(args, check=True, timeout=30):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f'{args}: {result.stderr.strip()}')
    return result


def wait_ready(command):
    for _ in range(20):
        result = run(command, check=False)
        if result.returncode == 0:
            return
        time.sleep(1)
    raise RuntimeError(f'Service not ready: {command}: {result.stderr.strip()}')


def face_id(output, uri):
    for match in re.finditer(r'^faceid=(\d+) remote=(\S+)', output, re.MULTILINE):
        if match[2] == uri:
            return match[1]
    return None


def configure(containers, routers, network, port, previous):
    nfd, fw = containers['nfd'], containers['ndnd']
    networks = nfd['NetworkSettings']['Networks'].keys() & fw['NetworkSettings']['Networks'].keys()
    if len(networks) != 1:
        raise RuntimeError('NFD and NDNd must share exactly one Docker network')
    docker_network = next(iter(networks))
    to_nfd = 'udp4://' + nfd['NetworkSettings']['Networks'][docker_network]['IPAddress'] + ':6363'
    to_ndnd = 'udp4://' + fw['NetworkSettings']['Networks'][docker_network]['IPAddress'] + ':' + str(port)
    nfd_cmd = ['docker', 'exec', nfd['Id'], 'nfdc']
    ndnd_cmd = ['docker', 'exec', fw['Id'], '/ndnd']
    changed = previous.get('forwarder_started') != fw['State']['StartedAt']

    wait_ready(ndnd_cmd + ['fw', 'status'])
    wait_ready(nfd_cmd + ['status'])
    for index, prefix in sorted(routers.items()):
        run(ndnd_cmd + ['fw', 'bift-register', 'prefix=' + prefix, 'index=' + str(index)])
    run(ndnd_cmd + ['fw', 'bift-rebuild'])
    if changed or not containers['ndnd-dv']['State']['Running']:
        run(['docker', 'restart', containers['ndnd-dv']['Id']])
    wait_ready(ndnd_cmd + ['dv', 'status'])

    # Remove our previous bridge entries if Docker assigned a new peer address.
    if previous.get('to_nfd') not in (None, to_nfd) and not changed:
        old_face = face_id(run(ndnd_cmd + ['fw', 'face-list']).stdout, previous['to_nfd'])
        if old_face:
            run(ndnd_cmd + ['dv', 'prefix-withdraw', 'prefix=/ndn', 'face=' + old_face])
            run(ndnd_cmd + ['fw', 'pet-remove-nexthop', 'prefix=/ndn', 'face=' + old_face])
    if previous.get('to_ndnd') not in (None, to_ndnd):
        # A missing old face means NFD already removed its routes.
        if face_id(run(nfd_cmd + ['face', 'list']).stdout, previous['to_ndnd']):
            run(nfd_cmd + ['route', 'remove', network, previous['to_ndnd']])

    # nfdc updates existing on-demand faces too; NDNd's create-only CLI returns 409.
    # Mount only the socket directory; nfdc needs its own writable client keychain.
    socket_dir = next(m['Source'] for m in fw['Mounts'] if m['Destination'] == '/run/ndnd')
    run(['docker', 'run', '--rm', '--network', 'none',
         '--mount', 'type=bind,src=' + socket_dir + ',dst=/run/ndnd,readonly',
         '-e', 'NDN_CLIENT_TRANSPORT=unix:///run/ndnd/ndnd.sock',
         '--entrypoint', '/usr/bin/nfdc', nfd['Image'],
         'face', 'create', to_nfd, 'persistency', 'permanent'])
    run(nfd_cmd + ['face', 'create', to_ndnd, 'persistency', 'permanent'])
    # Exclude inherited application/default routes from the foreign namespace.
    run(nfd_cmd + ['route', 'add', network, to_ndnd, 'capture'])
    bridge_face = face_id(run(ndnd_cmd + ['fw', 'face-list']).stdout, to_nfd)
    if bridge_face is None:
        raise RuntimeError('NDNd bridge face was not created')
    run(ndnd_cmd + ['fw', 'pet-add-nexthop', 'prefix=/ndn', 'face=' + bridge_face])
    # Bind the announcement to the UDP face, not this short-lived CLI connection.
    run(ndnd_cmd + ['dv', 'prefix-announce', 'prefix=/ndn', 'face=' + bridge_face])
    run(ndnd_cmd + ['fw', 'bift-rebuild'])

    if changed:
        # These services keep registrations on the forwarder's Unix socket.
        dependents = ['ndnd-http-status-server', 'ndnd-site-ca', 'ndnd-root-ca',
                      'ndnd-network-repo', 'ndnd-network-merkle']
        restart = [containers[s]['Id'] for s in dependents
                   if s in containers and containers[s]['State']['Running']]
        if restart:
            run(['docker', 'restart', *restart], timeout=120)
    return {'forwarder_started': fw['State']['StartedAt'], 'to_nfd': to_nfd, 'to_ndnd': to_ndnd}


def reconcile(node):
    config = conf.get()
    hosts = {path.name: yaml.safe_load(path.read_text())
             for path in Path(config.host_vars_path).iterdir() if path.is_file()}
    if not hosts[node].get('ndnd_enabled', False):
        return
    routers = router_indices(hosts)
    os.environ['COMPOSE_PROFILES'] = conf.compose_profiles(node)
    ids = run(['docker', 'compose', 'ps', '-aq']).stdout.split()
    containers = {c['Config']['Labels']['com.docker.compose.service']: c
                  for c in json.loads(run(['docker', 'inspect', *ids]).stdout)} if ids else {}
    if 'ndnd-dv' not in containers:
        raise RuntimeError('ndnd-dv must be created before NDNd network initialization')
    for service in ['nfd', 'ndnd']:
        if service not in containers or not containers[service]['State']['Running']:
            raise RuntimeError(f'{service} must be running before NDNd network initialization')
    state_file = Path('dist/.ndnd-network-state.json')
    previous = json.loads(state_file.read_text()) if state_file.exists() else {}
    state = configure(containers, routers, config.globals['ndnd_dv_network'],
                      config.globals['ndnd_udp_port'], previous)
    temporary = state_file.with_suffix('.tmp')
    temporary.write_text(json.dumps(state))
    temporary.replace(state_file)
    print('NDNd BIER and symmetric NFD gateway initialized')
