"""
Printer integration clients.

Usage:
    from services.integrations import get_printer_client
    client = get_printer_client("octoprint", base_url, api_key)
    status = client.get_status()
"""
from __future__ import annotations

from services.integrations.base import PrinterClient, get_printer_client

__all__ = ["PrinterClient", "get_printer_client"]
