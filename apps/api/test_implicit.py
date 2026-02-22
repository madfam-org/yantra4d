import os
from services.core.implicit_engine import run_render

config = {
    "topology": "gyroid",
    "base_frequency": 5.0,
    "resolution": 48,
    "size": 20.0
}

params = {
    "topology_type": 0,
    "frequency": 3.0,
    "mat_shrinkage_x": 0.95,
    "tda_euler_characteristic": -300,
    "simulated_energy": 120.0,
    "thermo_glass_transition_temp": 80.0
}

output = "test_implicit_output.stl"
success, err = run_render(output, config, params)
if success:
    print(f"Success! Mesh generated at {output} ({os.path.getsize(output)} bytes)")
else:
    print(f"Failed: {err}")
