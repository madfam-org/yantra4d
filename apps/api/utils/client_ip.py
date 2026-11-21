"""The visitor's address, for keying anonymous rate limits and quotas.

Public traffic reaches the API through the Cloudflare tunnel (enclii.yaml
`ingress: [cloudflare-tunnel]`), so ``request.remote_addr`` is the tunnel's
address for EVERY visitor: keyed on it, all anonymous visitors share one
bucket. Cloudflare puts the visitor's address in ``CF-Connecting-IP`` and
overwrites any value a visitor sends, so behind the tunnel the header is the
visitor.

Trust boundary: the API cannot tell the tunnel from any other caller inside
the cluster, and an in-cluster caller can set the header to anything. That is
accepted here because those callers are our own services, and the worst they
can do is pick which anonymous bucket they count against. A value that is not
an IP address is ignored rather than trusted as a free-form key.

IPv6 visitors are keyed by their /64: one subscriber is normally handed a
whole /64, so keying by the full address would let a single visitor rotate
through 2^64 buckets.
"""
from __future__ import annotations

import ipaddress

from flask import request

CF_CONNECTING_IP = "CF-Connecting-IP"
IPV6_PREFIX = 64


def _normalise(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        address = ipaddress.ip_address(raw.strip())
    except ValueError:
        return None
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped is not None:
            return str(address.ipv4_mapped)
        return str(ipaddress.ip_network(f"{address}/{IPV6_PREFIX}", strict=False))
    return str(address)


def client_ip() -> str:
    """The key for an anonymous caller: Cloudflare's visitor address, else the socket's."""
    return (
        _normalise(request.headers.get(CF_CONNECTING_IP))
        or _normalise(request.remote_addr)
        or (request.remote_addr or "unknown")
    )
