import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import jinja2
import yaml

from internal import conf


ROOT = Path(__file__).resolve().parent.parent


class DeploymentTest(unittest.TestCase):
    def test_nfd_only_compose_needs_no_ndnd_secret(self):
        env = dict(os.environ, PWD=str(ROOT), MANAGED_HOST='AVEIRO', COMPOSE_PROFILES='')
        env.pop('VAR_NDND_ROOT_CA_SECRET', None)
        result = subprocess.run(
            ['docker', 'compose', '--env-file', '/dev/null', 'config', '--format', 'json'],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        services = json.loads(result.stdout)['services']
        self.assertIn('nfd', services)
        self.assertNotIn('ndnd-root-http-ca', services)

    def test_enabled_signer_still_rejects_an_empty_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'signer.yml'
            config.write_text(yaml.safe_dump({
                'global_prefix': '/ndnd', 'secret': '', 'hosts': {},
                'port': 0, 'signer_backend': 'ndnd-go',
            }))
            result = subprocess.run(
                [sys.executable, str(ROOT / 'framework/http-ca-server.py'), str(config)],
                env=dict(os.environ, NDND_ROOT_CA_SECRET=''),
                capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('NDNd HTTP CA secret must be configured', result.stderr)

    def test_root_services_follow_host_and_network_enablement(self):
        services = conf.get().services
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(conf, 'get', return_value=SimpleNamespace(host_vars_path=directory)):
                for host in ['UCLA', 'AVEIRO']:
                    for enabled in [True, False]:
                        Path(directory, host).write_text(yaml.safe_dump({'ndnd_enabled': enabled}))
                        for service in ['ndnd-root-ca', 'ndnd-root-http-ca']:
                            with self.subTest(host=host, enabled=enabled, service=service):
                                self.assertEqual(conf.service_enabled(services[service], host),
                                                 host == 'UCLA' and enabled)

    def test_disabled_root_site_has_no_ndnd_proxy_routes(self):
        config = conf.get()
        values = yaml.safe_load((ROOT / 'host_vars/UCLA').read_text())
        template = jinja2.Environment(undefined=jinja2.StrictUndefined).from_string(
            (ROOT / 'templates/caddy/Caddyfile.j2').read_text())
        for enabled in [True, False]:
            with self.subTest(enabled=enabled):
                rendered = template.render(**dict(values, **config.globals,
                                                  inventory_hostname='UCLA', ndnd_enabled=enabled))
                self.assertEqual('/ndnd-ca/*' in rendered, enabled)
                self.assertEqual('/ndnd-status/*' in rendered, enabled)
                self.assertIn('http://nfd:9696', rendered)


class RenewalTest(unittest.TestCase):
    def run_renewal(self, root, failure='', force=False, enabled=True):
        (root / 'scripts').mkdir()
        (root / 'bin').mkdir()
        (root / 'scripts/utils.sh').write_text(
            'HAS_FORCE=""\n[[ "$*" == *--force* ]] && HAS_FORCE=--force\n'
            'needs_renewal() { echo 1; }\n')
        services = {
            'ndncert': 'ndncert', 'nlsr': 'nlsr', 'ndn-python-repo': 'ndn-python-repo',
            'ndnd-repo': 'ndnd-repo', 'ndnd-merkle': 'ndnd-merkle',
            'ndnd-site-ca': 'ndnd-site-ca', 'ndnd-dv': 'ndnd-dv',
            'ndnd-network-repo': 'ndnd-network-repo',
            'ndnd-network-merkle': 'ndnd-network-merkle',
        }
        for service, folder in services.items():
            directory = root / 'dist' / folder
            directory.mkdir(parents=True)
            (directory / 'renew.sh').write_text(
                f'echo "renew {service} $*" >> "$CALL_LOG"\n'
                f'exit {23 if service == failure else 0}\n')
        for directory in ['ndncert', 'ndnd-repo', 'ndnd-merkle', 'ndnd-site-ca',
                          'ndnd-dv', 'ndnd-network-repo', 'ndnd-network-merkle']:
            path = root / 'dist' / directory
            path.mkdir(exist_ok=True)
            (path / '.security-changed').touch()
        stubs = {
            'python3': '#!/bin/bash\n'
                       'if [[ "$*" == *"--service ndnd-dv"* || "$*" == *"--service ndnd-site-ca"* || '
                       '"$*" == *"--service ndnd-network-"* ]]; then echo "$TEST_NDND_ENABLED"; '
                       'elif [[ "$*" == *--service* ]]; then echo 1; else echo ndnd; fi\n',
            'docker': '#!/bin/bash\necho "docker $*" >> "$CALL_LOG"\n'
                      '[[ "$*" == *" ps "* ]] && echo running-container\nexit 0\n',
        }
        for name, text in stubs.items():
            path = root / 'bin' / name
            path.write_text(text)
            path.chmod(0o700)
        script = root / 'scripts/cert-renew.sh'
        script.write_bytes((ROOT / 'scripts/cert-renew.sh').read_bytes())
        log = root / 'calls.log'
        result = subprocess.run(
            ['bash', str(script), *(['--force'] if force else [])], cwd=root,
            env=dict(os.environ, PATH=str(root / 'bin') + ':' + os.environ['PATH'],
                     CALL_LOG=str(log), TEST_NDND_ENABLED=str(int(enabled))),
            capture_output=True, text=True, timeout=15)
        return result, log.read_text().splitlines()

    def test_nfd_only_renewal_does_not_run_ndnd_services(self):
        with tempfile.TemporaryDirectory() as directory:
            result, calls = self.run_renewal(Path(directory), failure='ndnd-site-ca', enabled=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            for service in ['ndnd-site-ca', 'ndnd-dv', 'ndnd-network-repo', 'ndnd-network-merkle']:
                self.assertFalse(any(call.startswith('renew ' + service + ' ') for call in calls))
            self.assertIn('docker compose restart nlsr ndncert serve-certs ndn-python-repo', calls)

    def test_ndnd_failure_does_not_block_nfd_reloads(self):
        for failure, marker in [('ndnd-site-ca', 'ndnd-site-ca'),
                                ('ndnd-dv', 'ndnd-dv'),
                                ('ndnd-network-repo', 'ndnd-network-repo')]:
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                result, calls = self.run_renewal(root, failure=failure)
                self.assertEqual(result.returncode, 23, result.stderr)
                failed = next(i for i, call in enumerate(calls) if call.startswith('renew ' + failure + ' '))
                for command in ['docker compose restart nlsr ndncert serve-certs ndn-python-repo',
                                'docker compose restart ndnd-repo',
                                'docker compose restart ndnd-merkle']:
                    self.assertIn(command, calls)
                    self.assertLess(calls.index(command), failed)
                for service in ['ndncert', 'ndnd-repo', 'ndnd-merkle']:
                    self.assertFalse((root / 'dist' / service / '.security-changed').exists())
                self.assertTrue((root / 'dist' / marker / '.security-changed').exists())

    def test_nfd_renewal_does_not_force_ndnd_but_manual_force_does(self):
        for force in [False, True]:
            with self.subTest(force=force), tempfile.TemporaryDirectory() as directory:
                result, calls = self.run_renewal(Path(directory), force=force)
                self.assertEqual(result.returncode, 0, result.stderr)
                for service in ['ndnd-site-ca', 'ndnd-dv', 'ndnd-network-repo', 'ndnd-network-merkle']:
                    call = next(call for call in calls if call.startswith('renew ' + service + ' '))
                    self.assertEqual('--force' in call, force, call)


if __name__ == '__main__':
    unittest.main()
