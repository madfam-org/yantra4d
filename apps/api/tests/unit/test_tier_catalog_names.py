"""Dhanam catalog tier names resolve to the tier the customer bought.

Owner ruling 2026-10-14: Dhanam's catalog sells yantra4d as creator / pro /
studio, and checkout plan ids are ``yantra4d_<slug>``. If ``studio`` reached the
``yantra4d_tier`` claim unmapped, a paying Studio customer would fail closed to
essentials with no error anywhere. These names are current, not deprecated, so
they resolve without a deprecation notice.
"""
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.core.tier_service import (
    CATALOG_TIER_MAP,
    TIER_HIERARCHY,
    describe_entitlement,
    has_tier,
    reset_alias_deprecation_notices,
    resolve_tier,
)


@pytest.mark.parametrize(
    "catalog_slug, tier",
    [("creator", "essentials"), ("pro", "pro"), ("studio", "premium")],
)
def test_each_catalog_slug_seats_its_tier(catalog_slug, tier):
    assert resolve_tier({"yantra4d_tier": catalog_slug}) == tier


def test_a_studio_claim_is_not_a_silent_downgrade():
    assert resolve_tier({"yantra4d_tier": "studio"}) != "essentials"
    assert has_tier("studio", "pro") is True


def test_catalog_names_map_only_to_real_tiers():
    for tier in CATALOG_TIER_MAP.values():
        assert tier in TIER_HIERARCHY


def test_catalog_names_resolve_without_a_deprecation_notice(caplog):
    reset_alias_deprecation_notices()
    with caplog.at_level(logging.WARNING):
        resolve_tier({"yantra4d_tier": "studio"})
    assert "Deprecated tier name" not in caplog.text


def test_the_studio_plan_id_gets_the_plan_id_hint():
    detail = describe_entitlement({"yantra4d_tier": "yantra4d_studio"})["detail"]
    assert "'premium'" in detail and "PLAN ID" in detail
