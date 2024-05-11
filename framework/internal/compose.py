import json
import subprocess
import sys

STATUS_CACHE = {}

def config() -> dict:
    """
    Get the global configuration for the docker compose
    """
    try:
        cmd = ['docker', 'compose', 'config', '--format', 'json']
        result = subprocess.run(cmd, stdout=subprocess.PIPE)
        return json.loads(result.stdout)
    except Exception as e:
        print(f"Failed to get compose config: {e}", file=sys.stderr)
        return {}

def status(service: str) -> dict:
    """
    Get the status JSON for a docker compose service
    """
    try:
        cmd = ['docker', 'compose', 'ps', '--format', 'json', service]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, timeout=5)
        return json.loads(result.stdout)
    except Exception:
        return {}

def is_running(status: dict) -> bool:
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
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, timeout=timeout)
        return result.returncode, result.stdout
    except Exception as e:
        print(f"Failed to run ${cmd}: {e}", file=sys.stderr)
        return -1, bytes()

def up(service: str) -> bool:
    """
    Start a docker compose service
    """
    try:
        cmd = ['docker', 'compose', 'up', '-d', service]
        subprocess.call(cmd, stdout=subprocess.PIPE, timeout=300)
        print(f"Started service {service}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"Failed to restart service {service}: {e}", file=sys.stderr)
        return False

def restart(service: str) -> bool:
    """
    Restart a docker compose service
    """
    try:
        cmd = ['docker', 'compose', 'restart', service]
        subprocess.call(cmd, stdout=subprocess.PIPE, timeout=300)
        print(f"Restarted service {service}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"Failed to restart service {service}: {e}", file=sys.stderr)
        return False

def info() -> dict:
    """
    Get information about host and docker
    """
    try:
        cmd = ['docker', 'info', '-f', 'json']
        result = subprocess.run(cmd, stdout=subprocess.PIPE, timeout=5)
        return json.loads(result.stdout)
    except Exception as e:
        print(f"Failed to get host info from docker: {e}", file=sys.stderr)
        return {}
