"""
apps/api/services/integrations/octoprint.py

OctoPrint REST API client.
Provides a minimal interface for file upload, print dispatch, status polling,
and job cancellation. All functions are stateless — the caller provides the
base_url and api_key from the printer.json configuration.

OctoPrint API docs: https://docs.octoprint.org/en/master/api/
"""

import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10  # seconds


def _headers(api_key: str) -> dict:
    h = {"X-Api-Key": api_key} if api_key else {}
    return h


def get_status(base_url: str, api_key: str) -> dict:
    """
    Fetch current printer state, temperatures, and job progress.

    Returns a normalized dict:
        {
          "state": "Operational" | "Printing" | "Offline" | ...,
          "temperatures": {
            "tool0": {"actual": float, "target": float},
            "bed":   {"actual": float, "target": float},
          },
          "job": {
            "file": str,
            "progress_pct": float (0–100),
            "time_elapsed_s": int,
            "time_remaining_s": int | None,
          } | None
        }
    """
    try:
        r = requests.get(
            f"{base_url}/api/printer",
            headers=_headers(api_key),
            timeout=DEFAULT_TIMEOUT,
        )
        r.raise_for_status()
        raw = r.json()

        temps = {}
        for key, val in raw.get("temperature", {}).items():
            temps[key] = {"actual": val.get("actual"), "target": val.get("target")}

        state = raw.get("state", {}).get("text", "Unknown")

        job = None
        try:
            jr = requests.get(
                f"{base_url}/api/job",
                headers=_headers(api_key),
                timeout=DEFAULT_TIMEOUT,
            )
            jr.raise_for_status()
            job_raw = jr.json()
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


def upload_file(base_url: str, api_key: str, file_path: str) -> str:
    """
    Upload a local STL/3MF file to OctoPrint's local storage.

    Returns the remote filename on success, raises RuntimeError on failure.
    """
    path = Path(file_path)
    if not path.is_file():
        raise RuntimeError(f"File not found: {file_path}")

    with open(path, "rb") as f:
        try:
            r = requests.post(
                f"{base_url}/api/files/local",
                headers=_headers(api_key),
                files={"file": (path.name, f)},
                data={"print": "false"},
                timeout=60,
            )
            r.raise_for_status()
            remote = r.json().get("files", {}).get("local", {}).get("name", path.name)
            logger.info("Uploaded %s to OctoPrint as %s", path.name, remote)
            return remote
        except requests.RequestException as e:
            raise RuntimeError(f"OctoPrint upload failed: {e}") from e


def start_print(base_url: str, api_key: str, remote_filename: str) -> None:
    """Start printing a previously uploaded file."""
    try:
        r = requests.post(
            f"{base_url}/api/files/local/{remote_filename}",
            headers={**_headers(api_key), "Content-Type": "application/json"},
            json={"command": "select", "print": True},
            timeout=DEFAULT_TIMEOUT,
        )
        r.raise_for_status()
        logger.info("OctoPrint print started: %s", remote_filename)
    except requests.RequestException as e:
        raise RuntimeError(f"OctoPrint start_print failed: {e}") from e


def cancel_print(base_url: str, api_key: str) -> None:
    """Cancel the active print job."""
    try:
        r = requests.delete(
            f"{base_url}/api/job",
            headers=_headers(api_key),
            timeout=DEFAULT_TIMEOUT,
        )
        r.raise_for_status()
        logger.info("OctoPrint print cancelled.")
    except requests.RequestException as e:
        raise RuntimeError(f"OctoPrint cancel_print failed: {e}") from e
