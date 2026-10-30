"""Reconcile the local NDNd network after Compose or certificate updates."""

import fcntl
import os
from pathlib import Path

from internal.ndnd_network import reconcile


if __name__ == '__main__':
    Path('dist').mkdir(exist_ok=True)
    with open('dist/.ndnd-network.lock', 'w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('NDNd network initialization already running')
        else:
            reconcile(os.environ['MANAGED_HOST'])
