#!/usr/bin/env python3

import os
import sys
import json

import internal.conf as conf
import internal.compose as compose

if __name__ == '__main__':
    config = conf.get()

    # Read routers.json
    routers: dict[str, dict] = None
    with open(os.path.join(config.environment_path, 'dist', 'file-server', 'routers.json')) as stream:
        routers = json.load(stream)

    # Get status of each node
    for rn, router in routers.items():
        try:
            status_file = f"{router['prefix']}/file-server/status.json"
            code, stdout = compose.exec('ndnpingserver', ['ndncatchunks', '-q', status_file, '-r', '2', '-l', '1000'])
            if code == 0:
                router.update(json.loads(stdout))
                router['ndn-up'] = True
            else:
                raise Exception(f"ndncatchunks failed with {code}")
        except Exception as e:
            print(f"Error fetching status for {rn}: {e}", file=sys.stderr)
            router['ndn-up'] = False
            router['ws-tls'] = False

    print(json.dumps(routers, indent=4), file=sys.stdout)