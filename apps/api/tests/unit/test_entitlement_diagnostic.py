"""
Tests for describe_entitlement — the diagnostic that makes a bad tier claim visible.

resolve_tier fails closed by design: an unrecognised claim becomes essentials.
That is correct security and invisible debugging. These tests pin the thing that
matters operationally — that a paying customer seated in the wrong tier can be
told WHY, and specifically that the plan-id-instead-of-tier-name mistake is
named rather than left as a silent downgrade.
"""
import pytest

from services.core.tier_service import describe_entitlement


class TestAnonymous:
    def test_no_claims_is_guest(self):
        d = describe_entitlement(None)
        assert d["source"] == "anonymous"
        assert d["resolved_tier"] == "guest"
        assert d["claim_present"] is False

    def test_empty_claims_is_guest(self):
        assert describe_entitlement({})["resolved_tier"] == "guest"


class TestClaimAbsent:
    def test_authenticated_without_claim_says_the_contract_did_not_write_it(self):
        d = describe_entitlement({"sub": "u1", "email": "a@b.c"})
        assert d["source"] == "claim_absent"
        assert d["claim_present"] is False
        assert d["resolved_tier"] == "essentials"
        assert "dhanam" in d["detail"].lower()


class TestRecognisedClaims:
    @pytest.mark.parametrize("tier", ["guest", "essentials", "pro", "madfam"])
    def test_each_known_tier_round_trips(self, tier):
        d = describe_entitlement({"yantra4d_tier": tier})
        assert d["source"] == "claim"
        assert d["resolved_tier"] == tier
        assert d["raw_claim"] == tier
        assert "recognised" in d["detail"]


class TestTheSilentDowngrade:
    def test_plan_id_is_named_as_the_likely_mistake(self):
        # checkout sends plan=yantra4d_pro; the claim must carry 'pro'
        d = describe_entitlement({"yantra4d_tier": "yantra4d_pro"})
        assert d["source"] == "claim_unrecognised"
        assert d["raw_claim"] == "yantra4d_pro"
        assert d["resolved_tier"] == "essentials"
        assert "PLAN ID" in d["detail"]
        assert "'pro'" in d["detail"]

    def test_plan_id_for_madfam_too(self):
        d = describe_entitlement({"yantra4d_tier": "yantra4d_madfam"})
        assert "'madfam'" in d["detail"]

    def test_an_unrelated_yantra4d_prefix_gets_no_false_hint(self):
        d = describe_entitlement({"yantra4d_tier": "yantra4d_enterprise"})
        assert d["source"] == "claim_unrecognised"
        assert "PLAN ID" not in d["detail"]

    def test_arbitrary_garbage_lists_the_known_tiers(self):
        d = describe_entitlement({"yantra4d_tier": "platinum"})
        assert d["resolved_tier"] == "essentials"
        for tier in ("guest", "essentials", "pro", "madfam"):
            assert tier in d["detail"]

    def test_never_echoes_anything_but_the_tier_claim(self):
        d = describe_entitlement(
            {"yantra4d_tier": "pro", "sub": "secret-subject", "email": "a@b.c"}
        )
        blob = str(d)
        assert "secret-subject" not in blob
        assert "a@b.c" not in blob
