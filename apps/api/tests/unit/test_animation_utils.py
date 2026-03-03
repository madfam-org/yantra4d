"""Unit tests for animation utility functions (_ease, _interpolate_params)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from routes.projects.animations import _ease, _interpolate_params


class TestEase:
    def test_linear_midpoint(self):
        assert _ease(0.5, "linear") == 0.5

    def test_linear_endpoints(self):
        assert _ease(0.0, "linear") == 0.0
        assert _ease(1.0, "linear") == 1.0

    def test_ease_in_endpoints(self):
        assert _ease(0.0, "ease-in") == 0.0
        assert _ease(1.0, "ease-in") == 1.0

    def test_ease_in_midpoint_slower(self):
        # ease-in is t^2, so at 0.5 should be 0.25
        assert _ease(0.5, "ease-in") == pytest.approx(0.25)

    def test_ease_out_endpoints(self):
        assert _ease(0.0, "ease-out") == 0.0
        assert _ease(1.0, "ease-out") == 1.0

    def test_ease_out_midpoint_faster(self):
        # ease-out: 1 - (1-t)^2, at 0.5 should be 0.75
        assert _ease(0.5, "ease-out") == pytest.approx(0.75)

    def test_ease_in_out_endpoints(self):
        assert _ease(0.0, "ease-in-out") == 0.0
        assert _ease(1.0, "ease-in-out") == 1.0

    def test_ease_in_out_midpoint(self):
        # smoothstep: t^2 * (3 - 2t), at 0.5 = 0.5
        assert _ease(0.5, "ease-in-out") == pytest.approx(0.5)

    def test_unknown_easing_defaults_to_linear(self):
        assert _ease(0.5, "unknown") == 0.5


class TestInterpolateParams:
    def test_numeric_lerp(self):
        result = _interpolate_params({"x": 0.0}, {"x": 10.0}, 0.5)
        assert result["x"] == pytest.approx(5.0)

    def test_numeric_endpoints(self):
        assert _interpolate_params({"x": 0.0}, {"x": 10.0}, 0.0)["x"] == pytest.approx(0.0)
        assert _interpolate_params({"x": 0.0}, {"x": 10.0}, 1.0)["x"] == pytest.approx(10.0)

    def test_int_preservation(self):
        result = _interpolate_params({"x": 0}, {"x": 10}, 0.5)
        assert result["x"] == 5
        assert isinstance(result["x"], int)

    def test_string_snap_at_half(self):
        result_before = _interpolate_params({"s": "a"}, {"s": "b"}, 0.49)
        assert result_before["s"] == "a"

        result_after = _interpolate_params({"s": "a"}, {"s": "b"}, 0.5)
        assert result_after["s"] == "b"

    def test_missing_key_in_from(self):
        result = _interpolate_params({}, {"x": 10}, 0.5)
        assert result["x"] == 10

    def test_missing_key_in_to(self):
        result = _interpolate_params({"x": 10}, {}, 0.5)
        assert result["x"] == 10

    def test_multiple_params(self):
        result = _interpolate_params(
            {"a": 0, "b": 100, "c": "red"},
            {"a": 10, "b": 200, "c": "blue"},
            0.5,
        )
        assert result["a"] == 5
        assert result["b"] == 150
        assert result["c"] == "blue"
