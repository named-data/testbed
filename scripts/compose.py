import json
import subprocess

def status(service: str) -> dict:
    """
    Get the status JSON for a docker compose service
    """
    cmd = ['docker', 'compose', 'ps', '--format', 'json', service]
    result = subprocess.run(cmd, stdout=subprocess.PIPE)

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

def exec(service: str, command: list[str]):
    """
    Execute a command in a docker compose service
    """

    cmd = ['docker', 'compose', 'exec', service] + command
    result = subprocess.call(cmd, stdout=subprocess.PIPE)

    print(f"Executed command {cmd}")
    print(f"{result.stdout}")
