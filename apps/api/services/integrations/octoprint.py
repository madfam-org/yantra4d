"""
OctoPrint REST API client.

Implements the PrinterClient interface for OctoPrint printers.
OctoPrint API docs: https://docs.octoprint.org/en/master/api/
"""
from __future__ import annotations

import logging

import requests

from services.integrations.base import UPLOAD_TIMEOUT, PrinterClient

logger = logging.getLogger(__name__)


class OctoPrintClient(PrinterClient):
    """OctoPrint printer client."""

    def get_status(self) -> dict:
        try:
            raw = self._get("/api/printer")

            temps = {}
            for key, val in raw.get("temperature", {}).items():
                temps[key] = {"actual": val.get("actual"), "target": val.get("target")}

            state = raw.get("state", {}).get("text", "Unknown")

            job = None
            try:
                job_raw = self._get("/api/job")
                progress = job_raw.get("progress", {})
                job = {
                    "file": job_raw.get("job", {}).get("file", {}).get("name", ""),
                    "progress_pct": progress.get("completion") or 0.0,
                    "time_elapsed_s": progress.get("printTime") or 0,
                    "time_remaining_s": progress.get("printTimeLeft"),
                }
            except Exception:
                pass

            return {"state": state, "temperatures": temps, "job": job}

        except requests.RequestException as e:
            logger.warning("OctoPrint get_status failed: %s", e)
            return {"state": "Offline", "temperatures": {}, "job": None, "error": str(e)}

    def upload_file(self, file_path: str) -> str:
        path = self._validate_file(file_path)
        with open(path, "rb") as f:
            try:
                r = self._post(
                    "/api/files/local",
                    files={"file": (path.name, f)},
                    data={"print": "false"},
                    timeout=UPLOAD_TIMEOUT,
                )
                remote = r.get("files", {}).get("local", {}).get("name", path.name)
                logger.info("Uploaded %s to OctoPrint as %s", path.name, remote)
                return remote
            except requests.RequestException as e:
                raise RuntimeError(f"OctoPrint upload failed: {e}") from e

    def start_print(self, remote_filename: str) -> None:
        try:
            self._post(
                f"/api/files/local/{remote_filename}",
                json={"command": "select", "print": True},
            )
            logger.info("OctoPrint print started: %s", remote_filename)
        except requests.RequestException as e:
            raise RuntimeError(f"OctoPrint start_print failed: {e}") from e

    def cancel_print(self) -> None:
        try:
            self._delete("/api/job")
            logger.info("OctoPrint print cancelled.")
        except requests.RequestException as e:
            raise RuntimeError(f"OctoPrint cancel_print failed: {e}") from e


# Backwards-compatible module-level functions
def _headers(api_key: str) -> dict:
    return {"X-Api-Key": api_key} if api_key else {}

def get_status(base_url: str, api_key: str) -> dict:
    return OctoPrintClient(base_url, api_key).get_status()

def upload_file(base_url: str, api_key: str, file_path: str) -> str:
    return OctoPrintClient(base_url, api_key).upload_file(file_path)

def start_print(base_url: str, api_key: str, remote_filename: str) -> None:
    OctoPrintClient(base_url, api_key).start_print(remote_filename)

def cancel_print(base_url: str, api_key: str) -> None:
    OctoPrintClient(base_url, api_key).cancel_print()
