import subprocess
import unittest
from unittest.mock import patch

import jinja2
import yaml

from internal import ndnd_network
from internal import conf


class NetworkInitTest(unittest.TestCase):
    def setUp(self):
        self.commands = []
        self.containers = {}
        for service, ip in [('nfd', '172.20.0.2'), ('ndnd', '172.20.0.3'),
                            ('ndnd-dv', ''), ('ndnd-network-repo', ''),
                            ('ndnd-site-ca', ''), ('ndnd-repo', ''), ('nlsr', '')]:
            self.containers[service] = {
                'Id': service, 'Image': 'nfd-image',
                'Mounts': [{'Source': '/run/ndnd', 'Destination': '/run/ndnd'},
                           {'Source': '/read-only/config', 'Destination': '/config'}],
                'State': {'Running': True, 'StartedAt': 'start-1'},
                'NetworkSettings': {'Networks': {'default': {'IPAddress': ip}}},
            }
        self.previous = {'forwarder_started': 'start-1',
                         'to_nfd': 'udp4://172.20.0.2:6363',
                         'to_ndnd': 'udp4://172.20.0.3:6364'}

    def run_command(self, args, check=True, **kwargs):
        self.commands.append(args)
        output = ''
        if args[-2:] == ['fw', 'face-list']:
            output = 'faceid=42 remote=udp4://172.20.0.2:6363\nfaceid=43 remote=udp4://172.20.0.9:6363\n'
        elif args[-2:] == ['face', 'list']:
            output = 'faceid=70 remote=udp4://172.20.0.8:6364\n'
        return subprocess.CompletedProcess(args, 0, output, '')

    def configure(self, previous=None):
        with patch.object(ndnd_network, 'run', side_effect=self.run_command):
            return ndnd_network.configure(self.containers, {0: '/ndnd/a', 1: '/ndnd/b'},
                                          '/ndnd', 6364, self.previous if previous is None else previous)

    def test_announcement_uses_persistent_udp_face(self):
        state = self.configure()
        self.assertIn(['docker', 'exec', 'ndnd', '/ndnd', 'dv', 'prefix-announce',
                       'prefix=/ndn', 'face=42'], self.commands)
        self.assertEqual(state, self.previous)
        self.assertIn(['docker', 'exec', 'nfd', 'nfdc', 'route', 'add',
                       '/ndnd', self.previous['to_ndnd'], 'capture'], self.commands)
        self.assertTrue(any(c[:3] == ['docker', 'run', '--rm'] and
                            'type=bind,src=/run/ndnd,dst=/run/ndnd,readonly' in c and
                            '--volumes-from' not in c and c[-4:] == ['create', self.previous['to_nfd'],
                                                        'persistency', 'permanent']
                            for c in self.commands))

    def test_repeated_initialization_does_not_restart_services(self):
        self.configure()
        self.assertFalse(any(command[1] == 'restart' for command in self.commands))

    def test_forwarder_restart_restores_only_its_dependents(self):
        self.configure({})
        restarted = [command[2:] for command in self.commands if command[1] == 'restart']
        self.assertEqual(restarted, [['ndnd-dv'], ['ndnd-site-ca', 'ndnd-network-repo']])
        self.assertEqual(sum('bift-register' in command for command in self.commands), 2)

    def test_peer_address_change_removes_old_bridge_routes(self):
        previous = dict(self.previous, to_nfd='udp4://172.20.0.9:6363',
                        to_ndnd='udp4://172.20.0.8:6364')
        self.configure(previous)
        self.assertIn(['docker', 'exec', 'ndnd', '/ndnd', 'dv', 'prefix-withdraw',
                       'prefix=/ndn', 'face=43'], self.commands)
        self.assertIn(['docker', 'exec', 'nfd', 'nfdc', 'route', 'remove',
                       '/ndnd', previous['to_ndnd']], self.commands)

    def test_stopped_dv_restarts_without_restarting_producers(self):
        self.containers['ndnd-dv']['State']['Running'] = False
        self.configure()
        self.assertEqual([c[2:] for c in self.commands if c[1] == 'restart'], [['ndnd-dv']])

    def test_duplicate_indices_rejected(self):
        hosts = {'A': {'ndnd_enabled': True, 'ndnd_bier_index': 0, 'ndnd_router_prefix': '/ndnd/a'},
                 'B': {'ndnd_enabled': True, 'ndnd_bier_index': 0, 'ndnd_router_prefix': '/ndnd/b'}}
        with self.assertRaises(ValueError):
            ndnd_network.router_indices(hosts)

    def test_invalid_index_rejected(self):
        for index in [None, -1, True, 1.5]:
            with self.subTest(index=index), self.assertRaises(ValueError):
                ndnd_network.router_indices({'A': {'ndnd_enabled': True, 'ndnd_bier_index': index}})

    def test_enabled_hosts_have_stable_unique_indices_and_bridge_advertisements(self):
        from pathlib import Path
        config = conf.get()
        hosts = {p.name: yaml.safe_load(p.read_text())
                 for p in Path(config.host_vars_path).iterdir() if p.is_file()}
        indices = ndnd_network.router_indices(hosts)
        self.assertEqual(len(indices), 6)
        env = jinja2.Environment(loader=jinja2.FileSystemLoader('.'), undefined=jinja2.StrictUndefined)
        for host in hosts.values():
            context = dict(host, **config.globals)
            context['hostvars'] = {n: dict(h, **config.globals) for n, h in hosts.items()}
            rendered = env.get_template('templates/nlsr/nlsr.conf.j2').render(**context)
            advertising = rendered.split('advertising\n{', 1)[1].split('}', 1)[0]
            self.assertEqual('/ndnd 0' in advertising, bool(host.get('ndnd_enabled')))
            if host.get('ndnd_enabled'):
                fw = yaml.safe_load(env.get_template('templates/ndnd/yanfd.yml.j2').render(**context))
                self.assertEqual(indices[fw['fw']['bier_index']], host['ndnd_router_prefix'])


if __name__ == '__main__':
    unittest.main()
