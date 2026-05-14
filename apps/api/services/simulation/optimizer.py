"""
Topology Optimizer Engine

Deterministic heuristic optimizer used by simulation tasks when full PDE-backed
optimization is not yet provisioned.
"""
import logging
import math
from typing import Any

logger = logging.getLogger(__name__)


def _coerce_numeric(value: Any) -> float:
    try:
        if isinstance(value, bool):
            raise TypeError
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _pick_parameter_name(params: dict[str, Any]) -> str:
    numeric_keys = [key for key, value in params.items() if isinstance(value, int | float)]
    if not numeric_keys:
        return "blade_thickness"

    preferred = [key for key in numeric_keys if "thickness" in key.lower()]
    if preferred:
        return sorted(preferred)[0]

    return sorted(numeric_keys)[0]


def _infer_bounds(parameter_name: str, value: float) -> tuple[float, float]:
    lo = max(0.1, value * 0.5) if value > 0 else 0.2
    hi = max(lo + 0.5, value * 2.5 + 1.0) if value > 0 else 6.0

    lower = lo
    upper = hi
    if "thickness" in parameter_name.lower():
        lower = max(0.5, lo)
        upper = max(8.0, lo + 2.5)

    return float(lower), float(upper)


class TopologyOptimizer:
    def __init__(self, slug: str, original_params: dict):
        self.slug = slug
        self.original_params = original_params.copy()
        self.current_params = original_params.copy()
        self.best_params = original_params.copy()

        self.primary_param = _pick_parameter_name(self.original_params)
        self.primary_param_value = _coerce_numeric(self.original_params.get(self.primary_param, 0.0))
        self.param_min, self.param_max = _infer_bounds(self.primary_param, self.primary_param_value)
        self.param_target = self.param_min + 0.72 * (self.param_max - self.param_min)

        # Example: we want to minimize stress (max_sigma) over N iterations
        self.best_sigma = float("inf")
        self.current_iteration = 0
        self.best_iteration = 0

        if not (self.param_min <= self.primary_param_value <= self.param_max):
            clamped = min(max(self.primary_param_value, self.param_min), self.param_max)
            self.current_params[self.primary_param] = float(clamped)
            self.original_params[self.primary_param] = float(clamped)
            self.primary_param_value = float(clamped)

    def step(self, iteration: int) -> dict:
        """
        Executes a single generational step.

        In production this should:
        1. Write candidate params to transient store.
        2. Trigger render generation.
        3. Submit results to simulation tasks.
        4. Read sigma objective and evolve toward a best candidate.
        """
        self.current_iteration = max(1, int(iteration))

        current_value = _coerce_numeric(
            self.current_params.get(self.primary_param, self.primary_param_value)
        )
        self.current_params[self.primary_param] = current_value

        span = self.param_max - self.param_min
        normalized_progress = min(1.0, self.current_iteration / 15.0)
        oscillation = 0.08 * math.cos(self.current_iteration * 0.85) * (1.0 - normalized_progress)

        # Proportional controller toward the target with damped oscillation.
        delta = -0.42 * (current_value - self.param_target) + (span * oscillation)
        new_value = current_value + delta
        new_value = max(self.param_min, min(self.param_max, new_value))

        if abs(new_value - current_value) < 1e-6 and span > 0:
            adjustment = 0.03 if (self.current_iteration % 2) else -0.03
            new_value = max(self.param_min, min(self.param_max, current_value + adjustment))

        rounded_value = float(round(new_value, 4))
        test_params = self.current_params.copy()
        test_params[self.primary_param] = rounded_value
        self.current_params = test_params.copy()

        distance = abs(rounded_value - self.param_target)
        curvature_penalty = (self.current_iteration ** 2) * 0.0004
        current_sigma = round(28.0 + (distance * 14.0) + curvature_penalty + (0.02 * self.current_iteration), 6)

        if current_sigma < self.best_sigma:
            self.best_sigma = current_sigma
            self.best_iteration = self.current_iteration
            self.best_params = test_params.copy()

        return {
            "iteration": self.current_iteration,
            "current_sigma": current_sigma,
            "best_sigma": self.best_sigma,
            "testing_params": test_params,
            "metadata": {
                "parameter": self.primary_param,
                "target": self.param_target,
                "bounds": [self.param_min, self.param_max],
                "last_delta": round(delta, 6),
                "span": round(span, 6),
                "algorithm": "deterministic_damped_descent",
                "best_iteration": self.best_iteration,
            },
        }
