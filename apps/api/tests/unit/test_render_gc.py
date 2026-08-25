"""Tests for the render artifact garbage collector.

The static directory is an emptyDir with a hard sizeLimit; exceeding it gets the
whole pod evicted by the kubelet. Age-based expiry alone does not prevent that,
so these tests pin the size-reclamation behaviour.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.engine import render_gc


def _artifact(directory: Path, name: str, size: int, age_s: float = 0.0) -> Path:
    f = directory / name
    f.write_bytes(b"\x00" * size)
    if age_s:
        past = time.time() - age_s
        import os
        os.utime(f, (past, past))
    return f


class TestAgeExpiry:
    def test_removes_artifacts_past_max_age(self, tmp_path):
        old = _artifact(tmp_path, "old.stl", 10, age_s=100_000)
        fresh = _artifact(tmp_path, "fresh.stl", 10)
        removed = render_gc._gc_sweep(str(tmp_path), max_age=86_400)
        assert removed == 1
        assert not old.exists()
        assert fresh.exists()

    def test_ignores_non_artifact_extensions(self, tmp_path):
        keep = _artifact(tmp_path, "notes.txt", 10, age_s=100_000)
        render_gc._gc_sweep(str(tmp_path), max_age=86_400)
        assert keep.exists()


class TestSizeReclamation:
    def test_reclaims_when_over_high_water(self, tmp_path, monkeypatch):
        # 1 KiB volume; five 200-byte artifacts puts us at 1000/1024 = 97%.
        monkeypatch.setattr(render_gc, "VOLUME_LIMIT_BYTES", 1024)
        monkeypatch.setattr(render_gc, "HIGH_WATER", 0.75)
        monkeypatch.setattr(render_gc, "LOW_WATER", 0.50)
        for i in range(5):
            _artifact(tmp_path, f"a{i}.stl", 200, age_s=100 * (5 - i))

        removed = render_gc._gc_sweep(str(tmp_path), max_age=86_400)

        used, limit = render_gc.volume_usage(str(tmp_path))
        assert removed > 0, "nothing reclaimed while over the high-water mark"
        assert used <= limit * 0.50, f"still at {used}/{limit} after reclaim"

    def test_reclaims_oldest_first(self, tmp_path, monkeypatch):
        monkeypatch.setattr(render_gc, "VOLUME_LIMIT_BYTES", 1024)
        monkeypatch.setattr(render_gc, "HIGH_WATER", 0.75)
        monkeypatch.setattr(render_gc, "LOW_WATER", 0.50)
        oldest = _artifact(tmp_path, "oldest.stl", 400, age_s=500)
        newest = _artifact(tmp_path, "newest.stl", 400, age_s=1)

        render_gc._gc_sweep(str(tmp_path), max_age=86_400)

        assert not oldest.exists(), "oldest artifact should be reclaimed first"
        assert newest.exists(), "newest artifact should survive"

    def test_no_reclaim_below_high_water(self, tmp_path, monkeypatch):
        monkeypatch.setattr(render_gc, "VOLUME_LIMIT_BYTES", 1024)
        monkeypatch.setattr(render_gc, "HIGH_WATER", 0.75)
        f = _artifact(tmp_path, "small.stl", 100)
        removed = render_gc._gc_sweep(str(tmp_path), max_age=86_400)
        assert removed == 0
        assert f.exists()

    def test_age_and_size_passes_compose(self, tmp_path, monkeypatch):
        """A burst of fresh artifacts must still be reclaimed even though the
        age pass finds nothing to expire — this is the eviction that took the
        backend down on 2026-08-01 and 2026-08-04."""
        monkeypatch.setattr(render_gc, "VOLUME_LIMIT_BYTES", 1024)
        monkeypatch.setattr(render_gc, "HIGH_WATER", 0.75)
        monkeypatch.setattr(render_gc, "LOW_WATER", 0.50)
        for i in range(6):
            _artifact(tmp_path, f"burst{i}.stl", 170, age_s=i)  # all far below max_age

        removed = render_gc._gc_sweep(str(tmp_path), max_age=86_400)

        used, limit = render_gc.volume_usage(str(tmp_path))
        assert removed > 0
        assert used <= limit * 0.50


class TestVolumeUsage:
    def test_counts_every_file_not_just_artifacts(self, tmp_path):
        """kubelet sizeLimit accounting counts everything, so usage must too."""
        _artifact(tmp_path, "a.stl", 100)
        _artifact(tmp_path, "b.txt", 50)
        used, _ = render_gc.volume_usage(str(tmp_path))
        assert used == 150

    def test_missing_directory_is_not_fatal(self, tmp_path):
        used, limit = render_gc.volume_usage(str(tmp_path / "nope"))
        assert used == 0
        assert limit > 0
