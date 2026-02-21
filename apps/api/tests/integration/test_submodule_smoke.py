"""Smoke tests verifying submodule include paths resolve correctly."""
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

# Real libs directory at repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
LIBS_DIR = REPO_ROOT / "libs"
BOSL2_DIR = LIBS_DIR / "BOSL2"


class TestBOSL2Smoke:
    """Verify BOSL2 submodule is checked out and usable."""

    def test_bosl2_directory_exists(self):
        assert BOSL2_DIR.is_dir(), f"BOSL2 not found at {BOSL2_DIR} — run: git submodule update --init --recursive"

    def test_bosl2_std_scad_exists(self):
        std_scad = BOSL2_DIR / "std.scad"
        assert std_scad.is_file(), "BOSL2/std.scad missing — submodule may be empty"

    @pytest.mark.skipif(not shutil.which("openscad"), reason="OpenSCAD not installed")
    def test_bosl2_renders_with_openscad(self):
        """Actually render a minimal SCAD file that uses BOSL2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scad_file = Path(tmpdir) / "smoke.scad"
            scad_file.write_text('use <BOSL2/std.scad>;\ncube(1);')
            output_file = Path(tmpdir) / "smoke.stl"

            result = subprocess.run(
                [
                    shutil.which("openscad"),
                    "-o", str(output_file),
                    str(scad_file),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                env={
                    "PATH": shutil.os.environ.get("PATH", ""),
                    "OPENSCADPATH": str(LIBS_DIR),
                },
            )
            assert result.returncode == 0, f"OpenSCAD failed:\nstderr: {result.stderr}"
            assert output_file.exists() and output_file.stat().st_size > 0
