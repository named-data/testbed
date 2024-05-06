import yaml

from dataclasses import dataclass
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
