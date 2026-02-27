"""
apps/api/services/integrations/moonraker.py

Moonraker (Klipper) HTTP API client.
Provides the same interface as octoprint.py for drop-in substitutability.
All functions are stateless — the caller provides base_url and api_key.

Moonraker API docs: https://moonraker.readthedocs.io/en/latest/web_api/
"""

import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10  # seconds


def _headers(api_key: str) -> dict:
    """Moonraker uses X-Api-Key but many installs run without auth on LAN."""
    return {"X-Api-Key": api_key} if api_key else {}


def get_status(base_url: str, api_key: str) -> dict:
    """
    Fetch current printer state, temperatures, and job progress from Moonraker.

    Returns the same normalized structure as octoprint.get_status().
    """
    try:
        # Printer objects: extruder, heater_bed, print_stats
        r = requests.get(
            f"{base_url}/printer/objects/query"
            "?extruder&heater_bed&print_stats&display_status",
            headers=_headers(api_key),
            timeout=DEFAULT_TIMEOUT,
        )
        r.raise_for_status()
        raw = r.json().get("result", {}).get("status", {})

        extruder = raw.get("extruder", {})
        bed = raw.get("heater_bed", {})
        print_stats = raw.get("print_stats", {})
        display = raw.get("display_status", {})

        temps = {
            "tool0": {
                "actual": extruder.get("temperature"),
                "target": extruder.get("target"),
            },
            "bed": {
                "actual": bed.get("temperature"),
                "target": bed.get("target"),
            },
        }

        klipper_state = print_stats.get("state", "standby")  # standby/printing/paused/complete/error
        # Normalize to OctoPrint-style state names
        state_map = {
            "standby": "Operational",
            "printing": "Printing",
            "paused": "Paused",
            "complete": "Operational",
            "error": "Error",
        }
        state = state_map.get(klipper_state, klipper_state.capitalize())

        job = None
        filename = print_stats.get("filename", "")
        if filename:
            progress_pct = (display.get("progress", 0) or 0) * 100
            elapsed = print_stats.get("print_duration", 0)
            # Moonraker doesn't provide remaining time directly — estimate from progress
            if progress_pct and progress_pct < 100:
                remaining = (elapsed / (progress_pct / 100)) - elapsed
            else:
                remaining = None

            job = {
                "file": filename,
                "progress_pct": round(progress_pct, 1),
                "time_elapsed_s": int(elapsed),
                "time_remaining_s": int(remaining) if remaining else None,
            }

        return {"state": state, "temperatures": temps, "job": job}

    except requests.RequestException as e:
        logger.warning("Moonraker get_status failed: %s", e)
        return {"state": "Offline", "temperatures": {}, "job": None, "error": str(e)}


def upload_file(base_url: str, api_key: str, file_path: str) -> str:
    """
    Upload a local STL/3MF file to Moonraker's virtual_sdcard.

    Returns the remote filename on success, raises RuntimeError on failure.
    """
    path = Path(file_path)
    if not path.is_file():
        raise RuntimeError(f"File not found: {file_path}")

    with open(path, "rb") as f:
        try:
            r = requests.post(
                f"{base_url}/server/files/upload",
                headers=_headers(api_key),
                files={"file": (path.name, f)},
                data={"root": "gcodes"},
                timeout=60,
            )
            r.raise_for_status()
            remote = r.json().get("item", {}).get("path", path.name)
            logger.info("Uploaded %s to Moonraker as %s", path.name, remote)
            return remote
        except requests.RequestException as e:
            raise RuntimeError(f"Moonraker upload failed: {e}") from e


def start_print(base_url: str, api_key: str, remote_filename: str) -> None:
    """Instruct Moonraker to start printing the uploaded file."""
    try:
        r = requests.post(
            f"{base_url}/printer/print/start",
            headers={**_headers(api_key), "Content-Type": "application/json"},
            json={"filename": remote_filename},
            timeout=DEFAULT_TIMEOUT,
        )
        r.raise_for_status()
        logger.info("Moonraker print started: %s", remote_filename)
    except requests.RequestException as e:
        raise RuntimeError(f"Moonraker start_print failed: {e}") from e


def cancel_print(base_url: str, api_key: str) -> None:
    """Cancel the active print job via Moonraker's emergency stop + cancel."""
    try:
        r = requests.post(
            f"{base_url}/printer/print/cancel",
            headers=_headers(api_key),
            timeout=DEFAULT_TIMEOUT,
        )
        r.raise_for_status()
        logger.info("Moonraker print cancelled.")
    except requests.RequestException as e:
        raise RuntimeError(f"Moonraker cancel_print failed: {e}") from e
