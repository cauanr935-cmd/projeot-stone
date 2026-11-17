from src.core.progress import Reporter, stage_catalog
from src.renderer.reel_assembler import _plan_shots


def test_reporter_maps_stage_fraction_to_global_percent():
    events = []
    report = Reporter(events.append)
    report("voice", 0.0, "a")
    report("voice", 1.0, "b")
    assert events[0]["percent"] == 28 and events[1]["percent"] == 42
    assert events[1]["message"] == "b"


def test_reporter_swallows_callback_errors():
    def boom(_):
        raise RuntimeError("x")
    Reporter(boom)("render", 0.5)  # não deve levantar


def test_stage_catalog_is_contiguous_and_ends_at_100():
    stages = stage_catalog()
    assert stages[0]["start"] == 0 and stages[-1]["end"] == 100
    assert all(a["end"] == b["start"] for a, b in zip(stages, stages[1:]))


def _plan(rate=0.331):
    segs = [{"name": "a", "start": 0, "end": 5, "assets": ["i1"], "beat_aligned": False},
            {"name": "b", "start": 5, "end": 18, "assets": ["i2"], "beat_aligned": True}]
    return {"cut": {"target_cuts_per_sec": rate}, "segments": segs}


def test_shots_cover_timeline_without_gaps_and_open_with_three_states():
    assets = [{"id": "i1", "kind": "image", "path": "x"}, {"id": "i2", "kind": "image", "path": "y"}]
    beats = [round(k * 0.5, 3) for k in range(40)]
    shots = _plan_shots(_plan(), assets, beats, 0.5)
    assert shots[0]["start"] == 0 and shots[-1]["end"] == 18
    assert all(abs(a["end"] - b["start"]) < 1e-6 for a, b in zip(shots, shots[1:]))
    assert sum(1 for s in shots if s["start"] < 3.0) >= 3
    assert all(s["length"] >= 0.5 for s in shots)
    assert {s["zoom"] for s in shots} == {1.0, 1.08}
    # cortes do segmento alinhado à batida caem na grade
    for s in shots:
        if s["segment"] == "b" and s["start"] > 5:
            assert abs(s["start"] / 0.5 - round(s["start"] / 0.5)) < 1e-3
