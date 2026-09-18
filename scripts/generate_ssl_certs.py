#!/usr/bin/env python3
"""
WebGIS SSL Certificate Authority (CA) & Server Certificate Generator.

Generates:
1. Root CA (rootCA.crt, rootCA.key) — Trusted Certificate Authority for Office LAN.
2. Server Certificate (seismicatlas.crt, seismicatlas.key) — Signed by Root CA for 'seismicatlas.local', 'localhost', '127.0.0.1', and host LAN IPs.
"""

import datetime
import ipaddress
import os
import socket
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def get_lan_ip_addresses() -> list[str]:
    """Discover all IPv4 LAN addresses of the host."""
    ips = ["127.0.0.1"]
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    return ips


def generate_certificates(output_dir: Path | str | None = None):
    if output_dir is None:
        # Default to WebGIS/certs relative to script location
        script_dir = Path(__file__).resolve().parent
        out_path = script_dir.parent / "certs"
    else:
        out_path = Path(output_dir)

    out_path.mkdir(parents=True, exist_ok=True)

    root_key_file = out_path / "rootCA.key"
    root_cert_file = out_path / "rootCA.crt"
    server_key_file = out_path / "seismicatlas.key"
    server_cert_file = out_path / "seismicatlas.crt"

    print("========================================================")
    print("  WebGIS Internal CA & SSL Certificate Generator")
    print("========================================================")
    print(f"Output directory: {out_path.resolve()}\n")

    # -------------------------------------------------------------------------
    # 1. Generate Root CA Key & Certificate
    # -------------------------------------------------------------------------
    print("[1/3] Generating Root Certificate Authority (Root CA)...")
    root_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
        backend=default_backend(),
    )

    root_subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "VN"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Hanoi"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Hanoi"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "WebGIS Seismic Systems"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Internal Root CA"),
            x509.NameAttribute(NameOID.COMMON_NAME, "WebGIS Internal Root CA"),
        ]
    )

    root_cert = (
        x509.CertificateBuilder()
        .subject_name(root_subject)
        .issuer_name(root_subject)
        .public_key(root_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3650))  # 10 years
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(root_key.public_key()),
            critical=False,
        )
        .sign(root_key, hashes.SHA256(), default_backend())
    )

    # Save Root CA
    root_key_file.write_bytes(
        root_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    root_cert_file.write_bytes(root_cert.public_bytes(serialization.Encoding.PEM))
    print(f"  [OK] Root CA Key:  {root_key_file.name}")
    print(f"  [OK] Root CA Cert: {root_cert_file.name}")

    # -------------------------------------------------------------------------
    # 2. Generate Server Key & Certificate signed by Root CA
    # -------------------------------------------------------------------------
    print("\n[2/3] Generating Server Certificate for 'seismicatlas.local'...")
    server_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    server_subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "VN"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Hanoi"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Hanoi"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "WebGIS Seismic Systems"),
            x509.NameAttribute(NameOID.COMMON_NAME, "seismicatlas.local"),
        ]
    )

    # Build SAN (Subject Alternative Names)
    lan_ips = get_lan_ip_addresses()
    san_list: list[x509.GeneralName] = [
        x509.DNSName("seismicatlas.local"),
        x509.DNSName("*.seismicatlas.local"),
        x509.DNSName("localhost"),
        x509.DNSName("webgis.local"),
    ]

    for ip_str in lan_ips:
        try:
            san_list.append(x509.IPAddress(ipaddress.ip_address(ip_str)))
        except ValueError:
            pass

    print("  Configured Domains & IPs in SAN:")
    for san in san_list:
        print(f"    - {san.value}")

    server_cert = (
        x509.CertificateBuilder()
        .subject_name(server_subject)
        .issuer_name(root_subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1825))  # 5 years
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage(
                [
                    ExtendedKeyUsageOID.SERVER_AUTH,
                    ExtendedKeyUsageOID.CLIENT_AUTH,
                ]
            ),
            critical=False,
        )
        .add_extension(
            x509.SubjectAlternativeName(san_list),
            critical=False,
        )
        .sign(root_key, hashes.SHA256(), default_backend())
    )

    # Save Server Certificate & Key
    server_key_file.write_bytes(
        server_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    server_cert_file.write_bytes(server_cert.public_bytes(serialization.Encoding.PEM))
    print(f"  [OK] Server Key:   {server_key_file.name}")
    print(f"  [OK] Server Cert:  {server_cert_file.name}")

    print("\n[3/3] Certificates generated successfully!")
    print("========================================================")
    print("To trust this Root CA on Windows clients:")
    print("  Run script: scripts\\install_root_ca.bat")
    print("To setup local domain mapping:")
    print("  Run script: scripts\\setup_hosts.bat")
    print("========================================================\n")



if __name__ == "__main__":
    generate_certificates()
