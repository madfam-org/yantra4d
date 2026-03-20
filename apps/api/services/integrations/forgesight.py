"""
ForgeSight Integration Client (STUB)

BOM-to-cart pricing integration with ForgeSight manufacturing platform.
Currently a stub — actual integration blocked on ForgeSight API availability.

Usage:
    from services.integrations.forgesight import forgesight_client
    quote = forgesight_client.get_quote(bom_items)
"""
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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
    """Client for ForgeSight manufacturing API.

    Currently returns mock data. Will be connected to the real API
    when the ForgeSight dependency is available.
    """

    def __init__(self, api_url: str = "", api_key: str = ""):
        self.api_url = api_url
        self.api_key = api_key
        self._available = False

    @property
    def available(self) -> bool:
        """Check if ForgeSight integration is configured and reachable."""
        return self._available and bool(self.api_url)

    def get_quote(self, bom_items: list[dict]) -> Quote:
        """Request a manufacturing quote for BOM items.

        Args:
            bom_items: List of dicts with keys: part_name, quantity, material, specs

        Returns:
            Quote with pricing info (mock data in stub mode)
        """
        if not self.available:
            return Quote(
                items=[],
                error="ForgeSight integration not configured",
            )

        # STUB: return mock data for development
        logger.info("ForgeSight quote requested for %d items (stub mode)", len(bom_items))
        items = [
            QuoteItem(
                part_name=item.get("part_name", "unknown"),
                quantity=item.get("quantity", 1),
                unit_price=None,
                available=False,
            )
            for item in bom_items
        ]
        return Quote(
            items=items,
            error="ForgeSight API not yet available — integration pending",
        )


# Global singleton
forgesight_client = ForgeSightClient()
