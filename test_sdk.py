import sys
import os
sys.path.insert(0, os.path.abspath('apps/api'))

from services.openscad import build_openscad_command, run_render

scad_file = "projects/sdk-test/test.scad"
out_file = "projects/sdk-test/test.stl"

cmd = build_openscad_command(out_file, scad_file, {"render_mode": 0})
print(f"Command: {cmd}")

success, out = run_render(cmd, scad_file)
if success:
    print(f"✅ Successfully rendered SDK imported geometry to {out_file}")
else:
    print(f"❌ Failed to render SDK geometry:\n{out}")
    sys.exit(1)
