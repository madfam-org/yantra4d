import sys
import os
sys.path.insert(0, os.path.abspath('apps/api'))

from services.openscad import build_openscad_command, run_render

scad_file = "projects/custom-msh/box.scad"
out_file = "projects/custom-msh/box.stl"

cmd = build_openscad_command(out_file, scad_file, {"render_mode": 0})
print(f"Command: {cmd}")

success, out = run_render(cmd, scad_file)
if success:
    print(f"✅ Successfully rendered directly to {out_file}")
else:
    print(f"❌ Failed to render directly:\n{out}")
    sys.exit(1)
