"""
ForgeSight Integration Client

BOM-to-cart pricing integration with ForgeSight Data Intelligence Platform.
Queries materials pricing, supplier stock, and lead times.

When FORGESIGHT_ENABLED=false (default), returns graceful error responses
so nothing breaks. Enable with FORGESIGHT_ENABLED=true + valid API credentials.

Usage:
    from services.integrations.forgesight import forgesight_client
    quote = forgesight_client.get_quote(bom_items)
"""
import logging
import os

import requests

from dataclasses import dataclass

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10  # seconds


@dataclass
class QuoteItem:
    """A single item in a manufacturing quote."""
    part_name: str
    quantity: int
    unit_price: float | None = None
    lead_time_days: int | None = None
    available: bool = False


@dataclass
class Quote:
    """Manufacturing quote response."""
    items: list[QuoteItem]
    total_price: float | None = None
    currency: str = "USD"
    valid_until: str | None = None
    error: str | None = None


class ForgeSightClient:
    """Client for ForgeSight Data Intelligence Platform API."""

    def __init__(self):
        self.api_url = os.getenv("FORGESIGHT_API_URL", "")
        self.api_key = os.getenv("FORGESIGHT_API_KEY", "")
        self._enabled = os.getenv("FORGESIGHT_ENABLED", "false").lower() == "true"

    @property
    def available(self) -> bool:
        """Check if ForgeSight integration is configured and enabled."""
        return self._enabled and bool(self.api_url) and bool(self.api_key)

    def get_quote(self, bom_items: list[dict]) -> Quote:
        """Request a manufacturing quote for BOM items.

        Args:
            bom_items: List of dicts with keys: part_name, quantity, material, specs

        Returns:
            Quote with pricing info, or Quote with error message on failure.
        """
        if not self.available:
            return Quote(
                items=[],
                error="ForgeSight integration not configured — set FORGESIGHT_ENABLED=true with valid credentials",
            )

        url = f"{self.api_url.rstrip('/')}/v1/quote"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                url,
                json={"items": bom_items},
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

            items = [
                QuoteItem(
                    part_name=item.get("part_name", "unknown"),
                    quantity=item.get("quantity", 1),
                    unit_price=item.get("unit_price"),
                    lead_time_days=item.get("lead_time_days"),
                    available=item.get("available", False),
                )
                for item in data.get("items", [])
            ]

            return Quote(
                items=items,
                total_price=data.get("total_price"),
                currency=data.get("currency", "USD"),
                valid_until=data.get("valid_until"),
            )

        except requests.Timeout:
            logger.warning("ForgeSight API timed out after %ds", REQUEST_TIMEOUT)
            return Quote(items=[], error="ForgeSight API request timed out")

        except requests.HTTPError as e:
            logger.warning("ForgeSight API HTTP error: %s", e)
            return Quote(items=[], error=f"ForgeSight API error: {e.response.status_code}")

        except requests.ConnectionError:
            logger.warning("ForgeSight API unreachable at %s", self.api_url)
            return Quote(items=[], error="ForgeSight API unreachable")

        except (ValueError, KeyError) as e:
            logger.warning("ForgeSight API returned invalid response: %s", e)
            return Quote(items=[], error="ForgeSight API returned invalid response")

    def get_material_pricing(self, material_slug: str) -> dict | None:
        """Query material pricing from ForgeSight catalog.

        Placeholder for Sprint 16 material-linking feature.
        Returns None until material catalog API is available.
        """
        if not self.available:
            return None
        # TODO: implement when ForgeSight material catalog API is versioned
        return None


# Global singleton
forgesight_client = ForgeSightClient()
