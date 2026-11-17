from __future__ import annotations

import re
from pathlib import Path

import pysubs2


def _flatten(items: list) -> list[dict]:
    result = []
    for item in items:
        if "words" in item:
            result.extend(item["words"])
        elif "word" in item:
            result.append(item)
    return sorted(result, key=lambda x: float(x.get("start", 0)))


def generate_karaoke_ass_subtitles(words_or_segments: list, ass_output_path: Path,
                                   hook_overlay: str | None = None) -> dict:
    words = _flatten(words_or_segments)
    subtitles = pysubs2.SSAFile()
    subtitles.info["PlayResX"], subtitles.info["PlayResY"] = "1080", "1920"
    style = pysubs2.SSAStyle(fontname="Montserrat ExtraBold", fontsize=68, primarycolor=pysubs2.Color(255,255,255),
                            outlinecolor=pysubs2.Color(0,0,0), outline=4.5, shadow=2, alignment=2, marginv=350)
    subtitles.styles["ImpulsoKaraoke"] = style
    subtitles.styles["ImpulsoHook"] = pysubs2.SSAStyle(fontname="Montserrat ExtraBold", fontsize=74,
                                                        primarycolor=pysubs2.Color(255,255,255), outline=5,
                                                        shadow=2, alignment=5)
    early_words = [w for w in words if float(w.get("start", 0)) < 3.0]
    distinct_early = {re.sub(r"\W", "", str(w.get("word", "")).upper()) for w in early_words}
    use_hook = len(distinct_early) > 5
    if use_hook:
        hook_text = " ".join((hook_overlay or " ".join(str(w["word"]) for w in early_words[:5])).split()[:5])
        subtitles.events.append(pysubs2.SSAEvent(start=0, end=3000, text=hook_text, style="ImpulsoHook"))
        words = [w for w in words if float(w.get("end", 0)) > 3.0]
    # Group very short tokens until each event lasts at least 100ms.
    groups, current = [], []
    for word in words:
        current.append(word)
        start = float(current[0].get("start", 0))
        end = float(word.get("end", start + .1))
        if (end - start >= .1 and len(current) >= 1) or len(current) >= 4:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    for group in groups:
        start = max(float(group[0].get("start", 0)), 3.0 if use_hook else 0)
        end = max(start + .1, float(group[-1].get("end", start + .1)))
        parts = [str(w.get("word", "")).strip().upper() for w in group]
        text = " ".join(parts[:-1] + [r"{\c&H34C9FC&\fscx112\fscy112}" + parts[-1] +
                                      r"{\c&HFFFFFF&\fscx100\fscy100}"])
        subtitles.events.append(pysubs2.SSAEvent(start=round(start * 1000), end=round(end * 1000),
                                                 text=text, style="ImpulsoKaraoke"))
    out = Path(ass_output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    subtitles.save(str(out))
    return {"path": str(out), "events": len(subtitles.events),
            "frame_zero_words": min(5, len(distinct_early)), "mode": "hook_then_karaoke" if use_hook else "karaoke"}
