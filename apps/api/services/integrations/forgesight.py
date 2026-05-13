"""
ForgeSight Data Intelligence Platform Integration

Provides real-time 3D printing price benchmarks from forgesight.quest.
Uses OAuth2 authentication and caches benchmark data (1hr TTL) to stay
within the Starter tier rate limit (10 calls/hour).

When FORGESIGHT_ENABLED=false (default), all methods return graceful
fallback responses so the platform works without ForgeSight credentials.

Usage:
    from services.integrations.forgesight import forgesight_client
    benchmark = forgesight_client.get_material_benchmark("pla")
"""
import logging
import os
import time
from dataclasses import dataclass, field

import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10  # seconds
TOKEN_REFRESH_BUFFER = 60  # seconds before expiry to refresh
BENCHMARK_CACHE_TTL = 3600  # 1 hour

# Map Yantra4D material IDs to ForgeSight benchmark categories
MATERIAL_CATEGORY_MAP = {
    "pla": "FDM - PLA",
    "petg": "FDM - PETG",
    "abs": "FDM - ABS",
    "tpu": "FDM - TPU",
    "resin": "SLA - Standard Resin",
    "nylon": "SLS - Nylon PA12",
}

# Hardcoded fallback pricing (USD/kg) when ForgeSight is unavailable
DEFAULT_PRICING = {
    "pla": 20.0,
    "petg": 22.0,
    "abs": 18.0,
    "tpu": 35.0,
    "resin": 50.0,
    "nylon": 60.0,
}


@dataclass
class MaterialBenchmark:
    """Price benchmark for a material category from ForgeSight."""
    material: str
    category: str
    region: str
    p10_per_kg: float
    p50_per_kg: float
    p90_per_kg: float
    currency: str = "MXN"
    sample_count: int = 0
    updated_at: str = ""
    source: str = "forgesight"
    error: str | None = None
    market_verified: bool = False
    fallback_reason: str | None = None

    @property
    def provenance(self) -> dict:
        """Return explicit truth labels for callers and clients."""
        return {
            "provider": "forgesight" if self.source == "forgesight" else "yantra4d",
            "source": self.source,
            "market_verified": self.market_verified,
            "fallback_reason": self.fallback_reason,
            "sample_count": self.sample_count,
            "updated_at": self.updated_at,
        }


@dataclass
class QuoteItem:
    """A single item in a manufacturing quote."""
    part_name: str
    quantity: int
    unit_price: float | None = None
    lead_time_days: int | None = None
    available: bool = False
    source: str | None = None
    market_verified: bool = False
    fallback_reason: str | None = None


@dataclass
class Quote:
    """Manufacturing quote response."""
    items: list[QuoteItem] = field(default_factory=list)
    total_price: float | None = None
    currency: str = "USD"
    valid_until: str | None = None
    error: str | None = None
    source: str = "forgesight"
    market_verified: bool = False
    fallback_reason: str | None = None
    sample_count: int = 0

    @property
    def provenance(self) -> dict:
        """Return explicit truth labels for quote/cart responses."""
        return {
            "provider": "forgesight" if self.source == "forgesight" else "yantra4d",
            "source": self.source,
            "market_verified": self.market_verified,
            "fallback_reason": self.fallback_reason,
            "sample_count": self.sample_count,
        }


class ForgeSightClient:
    """Client for the ForgeSight Data Intelligence Platform (forgesight.quest)."""

    def __init__(self):
        self.api_url = os.getenv("FORGESIGHT_API_URL", "https://api.forgesight.quest")
        self._email = os.getenv("FORGESIGHT_EMAIL", "")
        self._password = os.getenv("FORGESIGHT_PASSWORD", "")
        self._enabled = os.getenv("FORGESIGHT_ENABLED", "false").lower() == "true"
        self._default_region = os.getenv("FORGESIGHT_REGION", "CDMX")

        # OAuth2 token cache
        self._token: str | None = None
        self._token_expires_at: float = 0

        # Benchmark cache: { "pla:CDMX": (MaterialBenchmark, timestamp) }
        self._benchmark_cache: dict[str, tuple[MaterialBenchmark, float]] = {}

    @property
    def available(self) -> bool:
        """Check if ForgeSight integration is configured and enabled."""
        return self._enabled and bool(self._email) and bool(self._password)

    # ── Authentication ────────────────────────────────────────────────────

    def _authenticate(self) -> str | None:
        """Obtain or refresh an OAuth2 access token. Returns token or None."""
        if self._token and time.time() < self._token_expires_at:
            return self._token

        try:
            resp = requests.post(
                f"{self.api_url}/api/v1/auth/login",
                data={"username": self._email, "password": self._password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data.get("access_token")
            # Default to 1 hour if no expiry info
            expires_in = data.get("expires_in", 3600)
            self._token_expires_at = time.time() + expires_in - TOKEN_REFRESH_BUFFER
            logger.info("ForgeSight: authenticated as %s", self._email)
            return self._token
        except requests.RequestException as e:
            logger.warning("ForgeSight auth failed: %s", e)
            self._token = None
            return None

    def _auth_headers(self) -> dict | None:
        """Return Authorization headers, or None if auth fails."""
        token = self._authenticate()
        if not token:
            return None
        return {"Authorization": f"Bearer {token}"}

    # ── Benchmark Pricing ─────────────────────────────────────────────────

    def get_material_benchmark(
        self, material_id: str, region: str | None = None
    ) -> MaterialBenchmark:
        """Get price benchmark for a material from ForgeSight.

        Returns cached data if available (1hr TTL). Falls back to
        hardcoded defaults when ForgeSight is unavailable.
        """
        region = region or self._default_region
        cache_key = f"{material_id}:{region}"

        # Check cache
        if cache_key in self._benchmark_cache:
            cached, timestamp = self._benchmark_cache[cache_key]
            if time.time() - timestamp < BENCHMARK_CACHE_TTL:
                return cached

        # Map to ForgeSight category
        category = MATERIAL_CATEGORY_MAP.get(material_id)
        if not category:
            return self._default_benchmark(material_id, region,
                                           error=f"Unknown material: {material_id}")

        if not self.available:
            return self._default_benchmark(material_id, region)

        headers = self._auth_headers()
        if not headers:
            return self._default_benchmark(material_id, region,
                                           error="ForgeSight authentication failed")

        try:
            resp = requests.get(
                f"{self.api_url}/api/v1/benchmarks",
                params={"category": category, "region": region, "time_window": 30},
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )

            if resp.status_code == 401:
                # Token expired, clear and retry once
                self._token = None
                headers = self._auth_headers()
                if not headers:
                    return self._default_benchmark(material_id, region,
                                                   error="ForgeSight re-auth failed")
                resp = requests.get(
                    f"{self.api_url}/api/v1/benchmarks",
                    params={"category": category, "region": region, "time_window": 30},
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )

            resp.raise_for_status()
            data = resp.json()

            sample_count = int(data.get("sample_count", data.get("count", 0)) or 0)
            updated_at = data.get("updated_at", "")
            p50_per_kg = data.get("p50", data.get("percentile_50", 0))

            benchmark = MaterialBenchmark(
                material=material_id,
                category=category,
                region=region,
                p10_per_kg=data.get("p10", data.get("percentile_10", 0)),
                p50_per_kg=p50_per_kg,
                p90_per_kg=data.get("p90", data.get("percentile_90", 0)),
                currency=data.get("currency", "MXN"),
                sample_count=sample_count,
                updated_at=updated_at,
                source="forgesight",
                market_verified=sample_count > 0 and bool(updated_at) and float(p50_per_kg or 0) > 0,
                fallback_reason=None,
            )

            self._benchmark_cache[cache_key] = (benchmark, time.time())
            logger.info("ForgeSight: cached benchmark for %s/%s (%d samples)",
                        material_id, region, benchmark.sample_count)
            return benchmark

        except requests.Timeout:
            logger.warning("ForgeSight benchmark request timed out")
            return self._default_benchmark(material_id, region,
                                           error="ForgeSight API timed out")

        except requests.HTTPError as e:
            logger.warning("ForgeSight benchmark HTTP error: %s", e)
            return self._default_benchmark(material_id, region,
                                           error=f"ForgeSight API error: {e.response.status_code}")

        except requests.ConnectionError:
            logger.warning("ForgeSight API unreachable at %s", self.api_url)
            return self._default_benchmark(material_id, region,
                                           error="ForgeSight API unreachable")

        except (ValueError, KeyError) as e:
            logger.warning("ForgeSight returned invalid benchmark data: %s", e)
            return self._default_benchmark(material_id, region,
                                           error="Invalid benchmark response")

    def _default_benchmark(
        self, material_id: str, region: str, error: str | None = None
    ) -> MaterialBenchmark:
        """Return hardcoded fallback benchmark when ForgeSight is unavailable."""
        default_cost = DEFAULT_PRICING.get(material_id, 20.0)
        fallback_reason = error or "ForgeSight integration not configured"
        return MaterialBenchmark(
            material=material_id,
            category=MATERIAL_CATEGORY_MAP.get(material_id, "unknown"),
            region=region,
            p10_per_kg=default_cost * 0.8,
            p50_per_kg=default_cost,
            p90_per_kg=default_cost * 1.3,
            currency="USD",
            source="hardcoded_default",
            error=error,
            market_verified=False,
            fallback_reason=fallback_reason,
        )

    def get_supported_materials(self) -> list[str]:
        """Return list of material IDs that have ForgeSight category mappings."""
        return list(MATERIAL_CATEGORY_MAP.keys())

    # ── BOM Quoting (Sprint 16 — uses /offers/) ──────────────────────────

    def get_quote(self, bom_items: list[dict]) -> Quote:
        """Request pricing for BOM items via ForgeSight offers.

        Currently queries the offers endpoint for price intelligence.
        Full BOM-to-cart workflow is Sprint 16 scope.
        """
        if not self.available:
            return Quote(
                error="ForgeSight integration not configured",
                source="unavailable",
                market_verified=False,
                fallback_reason="ForgeSight integration not configured",
            )

        headers = self._auth_headers()
        if not headers:
            return Quote(
                error="ForgeSight authentication failed",
                source="unavailable",
                market_verified=False,
                fallback_reason="ForgeSight authentication failed",
            )

        items = []
        for item in bom_items:
            items.append(QuoteItem(
                part_name=item.get("part_name", "unknown"),
                quantity=item.get("quantity", 1),
                source="forgesight_pending",
                market_verified=False,
                fallback_reason="ForgeSight offers quote integration not implemented",
            ))

        return Quote(
            items=items,
            error="BOM quoting via ForgeSight offers API — coming in Sprint 16",
            source="forgesight_pending",
            market_verified=False,
            fallback_reason="ForgeSight offers quote integration not implemented",
        )


# Global singleton
forgesight_client = ForgeSightClient()
