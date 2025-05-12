import base64
import sys
from datetime import datetime, timedelta

from ndn.app_support.security_v2 import parse_certificate

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <cert_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    with open(file_path, 'r') as f:
        b64_data = f.read()
    text = ''.join(b64_data.split())

    try:
        cert_data = base64.standard_b64decode(text)
        cert = parse_certificate(cert_data)
    except (ValueError, IndexError):
        print("Malformed certificate", file_path)
        exit(1)

    date_template = "%Y%m%dT%H%M%S"
    not_before = bytes(cert.signature_info.validity_period.not_before).decode()
    not_before = datetime.strptime(not_before, date_template)
    not_after = bytes(cert.signature_info.validity_period.not_after).decode()
    not_after = datetime.strptime(not_after, date_template)

    print("Cert Status", file_path, not_before, not_after)

    now = datetime.now()
    if not_before <= now <= not_after - timedelta(days=91):
        exit(0)
    else:
        print("Certificate is expired or will expire in less than 91 days")
        exit(1)

if __name__ == "__main__":
    main()
