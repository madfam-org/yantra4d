"""
Base printer client ABC with shared HTTP logic.

All printer integrations implement this interface so the route layer
can work with any printer type without branching.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10  # seconds
UPLOAD_TIMEOUT = 60  # seconds


class PrinterClient(ABC):
    """Abstract base class for printer API clients."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict:
        return {"X-Api-Key": self.api_key} if self.api_key else {}

    def _get(self, path: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
        """HTTP GET with standard error handling."""
        r = requests.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            timeout=timeout,
        )
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, *, json: dict | None = None,
              files: dict | None = None, data: dict | None = None,
              timeout: int = DEFAULT_TIMEOUT) -> dict:
        """HTTP POST with standard error handling."""
        headers = self._headers()
        if json is not None and files is None:
            headers["Content-Type"] = "application/json"
        r = requests.post(
            f"{self.base_url}{path}",
            headers=headers,
            json=json,
            files=files,
            data=data,
            timeout=timeout,
        )
        r.raise_for_status()
        return r.json() if r.content else {}

    def _delete(self, path: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        """HTTP DELETE with standard error handling."""
        r = requests.delete(
            f"{self.base_url}{path}",
            headers=self._headers(),
            timeout=timeout,
        )
        r.raise_for_status()

    def _validate_file(self, file_path: str) -> Path:
        """Validate a local file path exists."""
        path = Path(file_path)
        if not path.is_file():
            raise RuntimeError(f"File not found: {file_path}")
        return path

    @abstractmethod
    def get_status(self) -> dict:
        """Fetch current printer state, temperatures, and job progress.

        Returns a normalized dict:
            {
              "state": "Operational" | "Printing" | "Offline" | ...,
              "temperatures": {
                "tool0": {"actual": float, "target": float},
                "bed":   {"actual": float, "target": float},
              },
              "job": {
                "file": str,
                "progress_pct": float (0-100),
                "time_elapsed_s": int,
                "time_remaining_s": int | None,
              } | None
            }
        """

    @abstractmethod
    def upload_file(self, file_path: str) -> str:
        """Upload a local file to the printer. Returns remote filename."""

    @abstractmethod
    def start_print(self, remote_filename: str) -> None:
        """Start printing a previously uploaded file."""

    @abstractmethod
    def cancel_print(self) -> None:
        """Cancel the active print job."""


def get_printer_client(printer_type: str, base_url: str, api_key: str) -> PrinterClient:
    """Factory function to create the appropriate printer client."""
    from services.integrations.octoprint import OctoPrintClient
    from services.integrations.moonraker import MoonrakerClient

    clients = {
        "octoprint": OctoPrintClient,
        "moonraker": MoonrakerClient,
    }
    cls = clients.get(printer_type)
    if cls is None:
        raise ValueError(f"Unknown printer type: {printer_type}. Supported: {sorted(clients)}")
    return cls(base_url, api_key)
