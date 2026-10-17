import yaml
import shlex

from dataclasses import dataclass
from os import getenv
from pathlib import Path
from typing import Any

from .utils import read_dotenv

CONFIG_FILE = 'config.yml'

@dataclass
class Config:
    environment_path: str
    host_vars_path: str
    services: dict[str, dict]
    globals: dict[str, Any]
    variables: dict[str, str]

def get() -> Config:
    # Load main config file
    config = None
    with open(CONFIG_FILE) as stream:
        config = Config(**yaml.safe_load(stream))

    # Extend configuration with environment variables
    env = read_dotenv()
    for key, value in env.items():
        if key.startswith('VAR_'):
            rkey = key[4:]
            config.globals[rkey] = value

    return config


def service_enabled(service: dict, node: str) -> bool:
    if 'hosts' in service and node not in service['hosts']:
        return False
    enabled_by = service.get('enabled_by')
    if enabled_by is None:
        return True
    if not node:
        return False
    with open(Path(get().host_vars_path) / node) as stream:
        host_vars = yaml.safe_load(stream) or {}
    return bool(host_vars.get(enabled_by, False))


def compose_profiles(node: str = None) -> str:
    """Apply tracked host profiles without replacing operator-managed profiles."""
    env = read_dotenv()
    node = node or getenv('MANAGED_HOST', env.get('MANAGED_HOST'))
    services = get().services.values()
    managed = {service['profile'] for service in services if 'profile' in service}
    default_profiles = ''.join(shlex.split(env.get('COMPOSE_PROFILES', ''), comments=True))
    requested = [p.strip() for p in getenv('COMPOSE_PROFILES', default_profiles).split(',')]
    if '*' in requested:
        with open('docker-compose.yml') as stream:
            compose = yaml.safe_load(stream)
        requested = [p for service in compose['services'].values() for p in service.get('profiles', [])]
    profiles = [p for p in requested
                if p and p not in managed]
    profiles.extend(service['profile'] for service in services
                    if 'profile' in service and service_enabled(service, node))
    return ','.join(dict.fromkeys(profiles))
