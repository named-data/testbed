import json
import subprocess
import sys

STATUS_CACHE = {}

def config() -> dict:
    """
    Get the global configuration for the docker compose
    """
    cmd = ['docker', 'compose', 'config', '--format', 'json']
    result = subprocess.run(cmd, stdout=subprocess.PIPE)
    return json.loads(result.stdout)

def status(service: str) -> dict:
    """
    Get the status JSON for a docker compose service
    """
    cmd = ['docker', 'compose', 'ps', '--format', 'json', service]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, timeout=5)

    try:
        return json.loads(result.stdout)
    except json.decoder.JSONDecodeError:
        return {}

def is_running(status: dict):
    """
    Arguments:
    - status: output of container_status
    """

    return 'State' in status and status['State'] == "running"

def exec(service: str, command: list[str], timeout: int = 120) -> tuple[int, bytes]:
    """
    Execute a command in a docker compose service
    """

    # Due to a bug in docker compose, we need to use docker exec in cron jobs
    # So we need to get the name of the container first
    if not STATUS_CACHE.get(service, None):
        STATUS_CACHE.update({service: status(service)})
    container = STATUS_CACHE.get(service, {}).get('Name', None)
    if container is None:
        return 1, b''

    cmd = ['docker', 'exec', container] + command
    result = subprocess.run(cmd, stdout=subprocess.PIPE, timeout=timeout)
    return result.returncode, result.stdout

def up(service: str):
    """
    Start a docker compose service
    """

    cmd = ['docker', 'compose', 'up', '-d', service]
    subprocess.call(cmd, stdout=subprocess.PIPE, timeout=300)
    print(f"Started service {service}")

def restart(service: str):
    """
    Restart a docker compose service
    """

    cmd = ['docker', 'compose', 'restart', service]
    subprocess.call(cmd, stdout=subprocess.PIPE, timeout=300)
    print(f"Restarted service {service}")

def info() -> dict:
    """
    Get information about host and docker
    """
    cmd = ['docker', 'info', '-f', 'json']
    result = subprocess.run(cmd, stdout=subprocess.PIPE, timeout=5)

    try:
        return json.loads(result.stdout)
    except json.decoder.JSONDecodeError:
        return {}
