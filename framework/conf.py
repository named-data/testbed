import yaml

from dataclasses import dataclass
from typing import Any

CONFIG_FILE = 'config.yml'

@dataclass
class Config:
    environment_path: str
    host_vars_path: str
    secret_config: str
    services: dict[str, dict]
    globals: dict[str, Any]
    variables: dict[str, str]

def get() -> Config:
    config = None
    with open(CONFIG_FILE) as stream:
        config = Config(**yaml.safe_load(stream))

    # Read and extend with secret config if specified
    if config.secret_config:
        with open(config.secret_config) as stream:
            secret = yaml.safe_load(stream)
            config.globals.update(secret.get('globals', {}))

    return config
