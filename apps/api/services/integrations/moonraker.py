"""
Moonraker (Klipper) HTTP API client.

Implements the PrinterClient interface for Klipper/Moonraker printers.
Moonraker API docs: https://moonraker.readthedocs.io/en/latest/web_api/
"""
from __future__ import annotations

import logging

import requests

from services.integrations.base import PrinterClient, UPLOAD_TIMEOUT

logger = logging.getLogger(__name__)

# Klipper state -> OctoPrint-style state mapping
_STATE_MAP = {
    "standby": "Operational",
    "printing": "Printing",
    "paused": "Paused",
    "complete": "Operational",
    "error": "Error",
}


class MoonrakerClient(PrinterClient):
    """Moonraker (Klipper) printer client."""

    def get_status(self) -> dict:
        try:
            raw = self._get(
                "/printer/objects/query?extruder&heater_bed&print_stats&display_status"
            ).get("result", {}).get("status", {})

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

            klipper_state = print_stats.get("state", "standby")
            state = _STATE_MAP.get(klipper_state, klipper_state.capitalize())

            job = None
            filename = print_stats.get("filename", "")
            if filename:
                progress_pct = (display.get("progress", 0) or 0) * 100
                elapsed = print_stats.get("print_duration", 0)
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

    def upload_file(self, file_path: str) -> str:
        path = self._validate_file(file_path)
        with open(path, "rb") as f:
            try:
                r = self._post(
                    "/server/files/upload",
                    files={"file": (path.name, f)},
                    data={"root": "gcodes"},
                    timeout=UPLOAD_TIMEOUT,
                )
                remote = r.get("item", {}).get("path", path.name)
                logger.info("Uploaded %s to Moonraker as %s", path.name, remote)
                return remote
            except requests.RequestException as e:
                raise RuntimeError(f"Moonraker upload failed: {e}") from e

    def start_print(self, remote_filename: str) -> None:
        try:
            self._post(
                "/printer/print/start",
                json={"filename": remote_filename},
            )
            logger.info("Moonraker print started: %s", remote_filename)
        except requests.RequestException as e:
            raise RuntimeError(f"Moonraker start_print failed: {e}") from e

    def cancel_print(self) -> None:
        try:
            self._post("/printer/print/cancel")
            logger.info("Moonraker print cancelled.")
        except requests.RequestException as e:
            raise RuntimeError(f"Moonraker cancel_print failed: {e}") from e


# Backwards-compatible module-level functions
def _headers(api_key: str) -> dict:
    return {"X-Api-Key": api_key} if api_key else {}

def get_status(base_url: str, api_key: str) -> dict:
    return MoonrakerClient(base_url, api_key).get_status()

def upload_file(base_url: str, api_key: str, file_path: str) -> str:
    return MoonrakerClient(base_url, api_key).upload_file(file_path)

def start_print(base_url: str, api_key: str, remote_filename: str) -> None:
    MoonrakerClient(base_url, api_key).start_print(remote_filename)

def cancel_print(base_url: str, api_key: str) -> None:
    MoonrakerClient(base_url, api_key).cancel_print()
