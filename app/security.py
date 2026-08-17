"""URL and request guards for the extractor.

The extractor fetches remote media on behalf of the user. These checks exist
to reduce SSRF risk (private networks, loopback, link-local, metadata hosts)
and to keep playlist / oversized jobs from running away.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

MAX_URL_LENGTH = 2048
ALLOWED_SCHEMES = {"http", "https"}
BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
    "metadata.google.internal",
    "metadata",
    "kubernetes.default",
    "kubernetes.default.svc",
}

# Hosts that often point at cloud instance metadata.
BLOCKED_HOSTNAME_SUFFIXES = (
    ".internal",
    ".local",
    ".localhost",
    ".lan",
    ".home",
    ".corp",
)


class UnsafeURLError(ValueError):
    """Raised when a URL is syntactically valid but not safe to fetch."""


def _is_blocked_hostname(hostname: str) -> bool:
    host = hostname.rstrip(".").lower()
    if host in BLOCKED_HOSTNAMES:
        return True
    return any(host.endswith(suffix) for suffix in BLOCKED_HOSTNAME_SUFFIXES)


def _is_unsafe_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    )


def _hostname_resolves_unsafely(hostname: str) -> bool:
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeURLError("Could not resolve that host.") from exc

    if not infos:
        raise UnsafeURLError("Could not resolve that host.")

    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if _is_unsafe_ip(ip):
            return True
    return False


def validate_media_url(raw_url: str) -> str:
    """Return a cleaned public http(s) URL, or raise UnsafeURLError."""
    if not raw_url or not raw_url.strip():
        raise UnsafeURLError("Paste a URL first.")

    url = raw_url.strip()
    if len(url) > MAX_URL_LENGTH:
        raise UnsafeURLError("That URL is too long.")
    if any(ch.isspace() for ch in url):
        raise UnsafeURLError("URLs cannot contain whitespace.")
    if "\\" in url:
        raise UnsafeURLError("That URL is not allowed.")

    parsed = urlparse(url)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeURLError("Only http and https URLs are allowed.")
    if parsed.username or parsed.password:
        raise UnsafeURLError("URLs with credentials are not allowed.")
    if not parsed.hostname:
        raise UnsafeURLError("That URL is missing a host.")
    if parsed.port in {0}:
        raise UnsafeURLError("That URL uses an invalid port.")

    hostname = parsed.hostname
    if _is_blocked_hostname(hostname):
        raise UnsafeURLError("That host is not allowed.")

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        ip = None

    if ip is not None and _is_unsafe_ip(ip):
        raise UnsafeURLError("That address is not allowed.")

    if ip is None and _hostname_resolves_unsafely(hostname):
        raise UnsafeURLError("That host resolves to a private address.")

    return url
