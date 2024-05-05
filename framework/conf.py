import yaml

from dataclasses import dataclass
from typing import Any

CONFIG_FILE = 'config.yml'

@dataclass
class Config:
    environment_path: str
    host_vars_path: str
    services: dict[str, dict]
    globals: dict[str, Any]
    variables: dict[str, str]

def get() :
    with open(CONFIG_FILE) as stream:
        return Config(**yaml.safe_load(stream))
