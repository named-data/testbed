import base64
from pathlib import Path
import unittest

import jinja2
import yaml
from ndn.app_support.light_versec import Checker, compile_lvs

from internal import conf
from internal.render import JINJA_FUNCTIONS


class TestNdndStatusTrust(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = conf.get()
        cls.hostvars = {}
        for path in Path(cls.config.host_vars_path).iterdir():
            if path.is_file():
                cls.hostvars[path.name] = {
                    **yaml.safe_load(path.read_text()),
                    **cls.config.globals,
                    'inventory_hostname': path.name,
                }
        cls.environment = jinja2.Environment(
            loader=jinja2.FileSystemLoader(cls.config.environment_path),
            undefined=jinja2.StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template, host):
        return self.environment.get_template(template).render(
            **self.hostvars[host], hostvars=self.hostvars, **JINJA_FUNCTIONS)

    def test_router_and_status_authorization(self):
        root = self.config.globals['ndnd_dv_network']
        root_cert = root + '/KEY/root/self/v=1'
        for host, values in self.hostvars.items():
            if not values.get('ndnd_enabled'):
                continue
            with self.subTest(host=host):
                routing = self.render('templates/ndnd-dv/dv-schema.lvs.j2', host)
                status = self.render('templates/ndnd-http-status-server/dv-schema.lvs.j2', host)
                model = compile_lvs(routing)
                self.assertEqual(0x00011000, model.version)
                self.assertEqual(bytes(model.encode()), bytes(compile_lvs(status).encode()))
                published = self.render('templates/file-server/ndnd/dv-schema.lvs.j2', host)
                self.assertEqual(bytes(model.encode()), bytes(compile_lvs(published).encode()))
                checker = Checker(model, {})
                router = values['ndnd_router_prefix']
                cert = router + '/32=DV/KEY/router/root/v=1'
                self.assertTrue(checker.check(cert, root_cert))
                for name in [router + '/32=DV/32=STATUS',
                             '/localhop' + router + '/32=DV/32=ADV/v=1',
                             root + '/32=DV/32=PSD' + router + '/t=1/seq=1']:
                    self.assertTrue(checker.check(name, cert), name)
                    self.assertFalse(checker.check(name, root_cert), name)
                    self.assertFalse(checker.check(name, router + '/g/user/KEY/key/site/v=1'), name)
                    for peer, peer_values in self.hostvars.items():
                        if peer != host and peer_values.get('ndnd_enabled'):
                            peer_cert = peer_values['ndnd_router_prefix'] + '/32=DV/KEY/router/root/v=1'
                            self.assertFalse(checker.check(name, peer_cert), name)
                outsider = root + '/unlisted/32=DV'
                self.assertFalse(checker.check(outsider + '/KEY/router/root/v=1', root_cert))
                self.assertFalse(checker.check(outsider + '/32=STATUS', cert))

                dv = yaml.safe_load(self.render('templates/ndnd-dv/dv.yml.j2', host))['dv']
                self.assertEqual('/config/dv-schema.tlv', dv['trust_schema'])
                fw = yaml.safe_load(self.render('templates/ndnd/yanfd.yml.j2', host))
                self.assertEqual(router, fw['fw']['router_name'])

    def test_public_status_anchor_matches_pin(self):
        for host, values in self.hostvars.items():
            if values.get('ndnd_enabled'):
                with self.subTest(host=host):
                    pem = self.render('templates/ndnd-http-status-server/root.cert.pem.j2', host)
                    wire = base64.b64decode(''.join(pem.splitlines()[1:-1]), validate=True)
                    pinned = base64.b64decode(''.join(Path(values['ndnd_root_anchor_path']).read_text().split()), validate=True)
                    self.assertEqual(pinned, wire)


if __name__ == '__main__':
    unittest.main()
