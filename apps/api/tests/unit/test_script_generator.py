"""
Unit tests for services/simulation/script_generator.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def test_generate_ppf_script_returns_string():
    from services.simulation.script_generator import generate_ppf_script
    parts = [{"id": "housing"}, {"id": "flexure"}]
    kinematics = {"housing": {"pinned": True}, "flexure": {"pinned": False, "flex_modulus": 90}}
    script = generate_ppf_script("test-project", parts, kinematics)
    assert isinstance(script, str)
    assert len(script) > 50


def test_generate_ppf_script_contains_slug():
    from services.simulation.script_generator import generate_ppf_script
    parts = [{"id": "body"}]
    kinematics = {}
    script = generate_ppf_script("sentinel-gripper", parts, kinematics)
    assert "sentinel-gripper" in script


def test_generate_ppf_script_contains_part_ids():
    from services.simulation.script_generator import generate_ppf_script
    parts = [{"id": "housing"}, {"id": "skeleton"}]
    kinematics = {}
    script = generate_ppf_script("demo", parts, kinematics)
    assert "housing" in script
    assert "skeleton" in script


def test_generate_ppf_script_applies_strain_limit_for_flexible():
    """Parts with low flex_modulus should get strain-limit 0.20 (TPU)."""
    from services.simulation.script_generator import generate_ppf_script
    parts = [{'id': 'flexure'}]
    kinematics = {'flexure': {'pinned': False, 'flex_modulus': 90}}
    script = generate_ppf_script('demo', parts, kinematics)
    assert 'strain-limit' in script
    assert '0.2' in script  # 0.20 from the modulus < 2000 branch


def test_generate_ppf_script_pins_rigid_parts():
    """Parts marked pinned in kinematics should include .pin() call."""
    from services.simulation.script_generator import generate_ppf_script
    parts = [{'id': 'housing'}]
    kinematics = {'housing': {'pinned': True}}
    script = generate_ppf_script('demo', parts, kinematics)
    # The pin call is indented inside the 'if os.path.exists' block
    assert '.pin()' in script


def test_generate_ppf_script_skips_parts_without_id():
    """Parts with no id key should be silently skipped."""
    from services.simulation.script_generator import generate_ppf_script
    parts = [{'name': 'orphan'}]  # no 'id' key
    kinematics = {}
    script = generate_ppf_script('demo', parts, kinematics)
    assert 'orphan' not in script


def test_generate_ppf_script_empty_parts():
    """Empty parts list should still produce a valid (stubbed) script."""
    from services.simulation.script_generator import generate_ppf_script
    script = generate_ppf_script('demo', [], {})
    assert isinstance(script, str)
    assert 'App.create' in script
