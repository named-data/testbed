#!/usr/bin/env python3
"""Create and publish the persistent Go NDNd root CA identity."""

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from ndn.app_support.security_v2 import parse_certificate
from ndn.encoding import Name


CA_HOME = Path("/ca")
PUBLIC_DIR = Path("/public")
CA_CONFIG = Path("/config/ca.json")
CA_IMAGE = os.environ["NDND_CA_IMAGE"]
CA_HOME_HOST = os.environ["NDND_CA_HOST_DIR"]
ROOT_CERT_URL = os.environ["NDND_ROOT_CERT_URL"]


def run_ndnd(args: list[str], input_data: bytes | None = None, mount_ca: bool = False) -> bytes:
    command = ["docker", "run", "--rm"]
    if input_data is not None:
        command.append("-i")
    if mount_ca:
        command.extend(["-v", f"{CA_HOME_HOST}:/ca:ro"])
    command.extend([CA_IMAGE, *args])
    result = subprocess.run(command, input=input_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode(errors="replace").strip() or "NDNd CLI failed")
    return result.stdout


def atomic_write(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> None:
    CA_HOME.mkdir(mode=0o700, parents=True, exist_ok=True)
    key_path = CA_HOME / "ca.key.pem"
    cert_path = CA_HOME / "ca.cert.pem"

    if not key_path.exists() and not cert_path.exists():
        key = run_ndnd(["sec", "keygen", "/ndn/edu", "ed25519"])
        atomic_write(key_path, key, 0o600)
    elif not key_path.exists():
        raise RuntimeError("CA certificate exists without its private key; refusing to rotate the root")

    if not cert_path.exists():
        cert = run_ndnd(["sec", "sign-cert", "/ca/ca.key.pem"], key_path.read_bytes(), mount_ca=True)
        atomic_write(cert_path, cert, 0o644)

    cert_wire = run_ndnd(["sec", "pem-decode"], cert_path.read_bytes())
    cert = parse_certificate(cert_wire)
    with CA_CONFIG.open() as stream:
        config = json.load(stream)

    ca_prefix = Name.normalize(config["ca-prefix"])
    if cert.name[:len(ca_prefix)] != ca_prefix:
        raise RuntimeError("CA certificate identity is outside configured CA prefix")

    cert_name = Name.to_str(cert.name)
    cert_digest = hashlib.sha256(cert_wire).hexdigest()
    atomic_write(PUBLIC_DIR / "ndnd-root.ndncert", cert_wire, 0o644)

    profile = {
        "schema_version": 1,
        "ca_prefix": config["ca-prefix"],
        "ca_info": config.get("ca-info", ""),
        "max_validity_period_seconds": int(config["max-validity-period"]),
        "probe_parameters": [],
        "supported_challenges": [item["challenge"] for item in config["supported-challenges"]],
        "root_certificate_url": ROOT_CERT_URL,
        "root_certificate_name": cert_name,
        "root_certificate_sha256": cert_digest,
    }
    atomic_write(
        PUBLIC_DIR / "ndnd-ca-profile.json",
        (json.dumps(profile, indent=2) + "\n").encode(),
        0o644,
    )
    print(f"Prepared Go CA identity {cert_name}")


if __name__ == "__main__":
    main()
