from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from src.core.config import ROOT, common
from src.core.ffmpeg import ffprobe_json, run_ffmpeg
from src.core.progress import make_reporter
from src.director.edit_plan import EditPlan
from src.editing.music import generate_procedural_music
from src.editing.beat_sync import duck_music_under_voice, extract_beats, select_high_energy_start
from src.editing.subtitles_ass import generate_karaoke_ass_subtitles
from src.router.cascade_router import ZeroCostCascadeRouter
from src.router.license_guard import validate_commercial_sources


def _audit(video: Path, format_id: int) -> dict:
    test_path = ROOT / "tests" / "verify_final_reel.py"
    spec = importlib.util.spec_from_file_location("verify_final_reel", test_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("não foi possível carregar auditoria de Reel")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.audit_reel(video, format_id)


def _plan_shots(plan: dict, assets: list[dict], beats: list[float], beat_period: float) -> list[dict]:
    """Divide cada segmento do formato em planos curtos na frequência de cortes da pesquisa.

    - nº de cortes por segmento = target_cuts_per_sec × duração (config/formats.yaml);
    - nos primeiros `swipe_zone_s` segundos há ao menos `swipe_zone_min_states` estados visuais
      (corte + punch-in), para vencer a Swipe Zone;
    - segmentos `beat_aligned` têm os cortes encaixados na grade de batidas da trilha;
    - planos consecutivos alternam zoom (punch_in_zoom) e avançam na fonte sem repetir trecho.
    """
    from src.core.config import common
    from src.editing.beat_sync import snap_to_beats
    from src.vision.hook_finder import best_hook_window

    cfg = common()
    hook_cfg = cfg.get("hook", {})
    zoom_lo, zoom_hi = cfg["punch_in_zoom"]
    rate = float(plan["cut"]["target_cuts_per_sec"])
    swipe_s = float(hook_cfg.get("swipe_zone_s", 3.0))
    min_states = int(hook_cfg.get("swipe_zone_min_states", 3))
    min_shot = float(hook_cfg.get("min_shot_s", 0.6))
    asset_by_id = {a["id"]: a for a in assets}
    playable = [a for a in assets if a["kind"] in {"video", "image"}]
    cursors: dict[str, float] = {}
    shots: list[dict] = []
    flip = False
    # Orçamento de planos: total = cortes planejados + 1. O gancho (1º segmento) tem prioridade;
    # o restante é repartido entre os demais segmentos sem estourar o orçamento.
    segs = plan["segments"]
    counts = [max(1, round(rate * (float(sg["end"]) - float(sg["start"])))) for sg in segs]
    counts[0] = max(counts[0], min_states)
    target = int(plan["cut"].get("planned_cuts", sum(counts) - 1)) + 1
    while sum(counts) > target and any(c > 1 for c in counts[1:]):
        k = max(range(1, len(counts)), key=lambda x: counts[x] / (float(segs[x]["end"]) - float(segs[x]["start"])))
        counts[k] -= 1
    while sum(counts) < target:
        k = max(range(len(counts)), key=lambda x: (float(segs[x]["end"]) - float(segs[x]["start"])) / counts[x])
        counts[k] += 1
    for i, segment in enumerate(segs):
        start, end = float(segment["start"]), float(segment["end"])
        length = end - start
        n = counts[i]
        if i == 0:
            step = swipe_s / min_states
            edges = [start + k * step for k in range(min_states)]
            rest = n - min_states
            span_left = end - (start + swipe_s)
            if rest > 0 and span_left > 0:
                edges += [start + swipe_s + span_left * k / (rest + 1) for k in range(1, rest + 1)]
        else:
            edges = [start + length * k / n for k in range(n)]
        if segment.get("beat_aligned") and beats and len(edges) > 1:
            snapped = snap_to_beats(edges[1:], beats, max_shift_s=beat_period / 2)
            edges = [edges[0]] + [min(max(t, edges[0] + min_shot), end - min_shot) for t in snapped]
        edges = sorted(dict.fromkeys(round(t, 3) for t in edges))
        cleaned = [edges[0]]
        for t in edges[1:]:
            if t - cleaned[-1] >= min_shot and end - t >= min_shot:
                cleaned.append(t)
        edges = cleaned + [end]
        base = asset_by_id.get((segment.get("assets") or [""])[0]) or playable[i % len(playable)]
        pool_start = playable.index(base) if base in playable else 0
        for j in range(len(edges) - 1):
            asset = playable[(pool_start + j) % len(playable)] if j else base
            seg_len = edges[j + 1] - edges[j]
            offset = 0.0
            if asset["kind"] == "video":
                dur = float(asset.get("duration_s") or 0)
                if i == 0 and j == 0 and dur > seg_len + 0.5:
                    offset = float(best_hook_window(asset["path"], window_s=min(seg_len + 0.2, 5.0))["start"])
                    cursors[asset["id"]] = offset + seg_len
                else:
                    offset = cursors.get(asset["id"], 0.0)
                    if dur and offset + seg_len > dur:
                        offset = 0.0
                    cursors[asset["id"]] = offset + seg_len
            flip = not flip
            shots.append({"segment": segment["name"], "asset": asset, "start": edges[j], "end": edges[j + 1],
                          "length": seg_len, "offset": offset, "zoom": zoom_hi if flip else zoom_lo})
    return shots


def _run_ffmpeg_with_progress(command: list[str], total_s: float, report) -> None:
    """Executa o ffmpeg lendo `-progress` para informar a porcentagem real do render."""
    import tempfile
    with tempfile.TemporaryFile("w+") as err:
        proc = subprocess.Popen(command[:1] + ["-progress", "pipe:1"] + command[1:], stdout=subprocess.PIPE,
                                stderr=err, text=True)
        assert proc.stdout is not None
        for line in proc.stdout:
            key, _, value = line.strip().partition("=")
            if key in {"out_time_us", "out_time_ms"} and value.lstrip("-").isdigit():
                done = min(1.0, max(0.0, int(value) / 1_000_000 / total_s))
                report("render", done, f"Renderizando o Reel: {int(done * 100)}%")
        proc.wait()
        if proc.returncode:
            err.seek(0)
            raise RuntimeError(f"render ffmpeg falhou: {err.read()[-5000:]}")


def assemble_and_render_reel(edit_plan: dict, output_path: Path, commercial: bool | None = None,
                             keep_source_audio: bool = False, progress=None,
                             music_path: Path | None = None) -> dict:
    started = time.monotonic()
    report_progress = make_reporter(progress)
    report_progress("plan", 0.8, "Validando o plano e as licenças")
    plan = EditPlan.model_validate(edit_plan).model_dump()
    commercial = os.getenv("REELS_COMMERCIAL", "1") != "0" if commercial is None else commercial
    assets = plan["assets"]
    for asset in assets:
        if not Path(asset["path"]).is_file():
            raise FileNotFoundError(f"asset inexistente: {asset['path']}")
    fmt_id = int(plan["format"]["id"])
    duration = float(plan["duration"]["target"])
    job_id = plan["job_id"]
    audio_settings = plan.get("audio", {})
    speech_enabled = bool(audio_settings.get("speech_enabled", True))
    music_enabled = bool(audio_settings.get("music_enabled", plan.get("music", {}).get("enabled", True)))
    custom_music = Path(music_path).resolve() if music_path else None
    if custom_music is not None and not custom_music.is_file():
        raise FileNotFoundError(f"trilha sonora inexistente: {custom_music}")
    keep_source_audio = keep_source_audio or bool(audio_settings.get("keep_source_audio", False))
    if not speech_enabled and not music_enabled and not keep_source_audio:
        raise ValueError("Ative a locução, a música ou o áudio original dos vídeos.")
    output = Path(output_path).resolve()
    if output.exists():
        raise FileExistsError(f"saída já existe: {output}")
    if output.parent.exists() and not os.access(output.parent, os.W_OK):
        raise PermissionError(f"diretório sem permissão de escrita: {output.parent}")

    # Fail the legal preflight before producing media or invoking FFmpeg.
    router = ZeroCostCascadeRouter()
    expected_tts = router.effective_tts_engine if speech_enabled else "disabled"
    license_keys = ["ffmpeg"]
    if music_enabled and custom_music is None:
        license_keys.append("procedural-music")
    if speech_enabled:
        license_keys.extend(["pysubs2", "dejavu", expected_tts])
    license_warnings = validate_commercial_sources(license_keys, commercial=commercial)
    if commercial and music_enabled and custom_music is not None:
        license_warnings.append({
            "source": "user_uploaded_track",
            "license": "user-responsibility",
            "status": "confirm_usage_rights",
        })

    job_dir = Path(os.getenv("REELS_WORKSPACE", "./workspace")) / "jobs" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)

    text = plan["script"]["full_text"]
    voice = job_dir / "voiceover.mp3"
    voice_srt = job_dir / "voiceover.srt"
    voice_duration = 0.0
    if speech_enabled:
        report_progress("voice", 0.05, "Gerando a locução em português")
        tts_result = __import__("asyncio").run(router.synthesize_ptbr_voiceover(
            text, voice, voice_srt, plan["tts"]["voice"], plan["tts"].get("rate", "+0%")))
        voice_duration = float(ffprobe_json(voice)["format"].get("duration", 0) or 0)
        report_progress("voice", 1.0, f"Locução pronta ({tts_result['engine']}, {voice_duration:.1f}s)")
    else:
        tts_result = {"engine": "disabled", "tier": 0}
        report_progress("voice", 1.0, "Locução desligada")
    if speech_enabled and tts_result["engine"] != expected_tts:
        license_keys.append(tts_result["engine"])
        license_warnings.extend(validate_commercial_sources([tts_result["engine"]], commercial=commercial))
    music_start = 0.0
    if music_enabled and custom_music is not None:
        music_duration = float(ffprobe_json(custom_music).get("format", {}).get("duration", 0) or 0)
        if music_duration <= 0:
            raise ValueError("A trilha enviada não tem duração válida.")
        music_start = select_high_energy_start(custom_music, min(duration, music_duration))
        beat_info = extract_beats(custom_music)
        bpm = float(beat_info["bpm"])
        source_beats = beat_info["downbeats"] if plan["music"].get("beat_sync") == "downbeats" else beat_info["beats"]
        if plan["music"].get("beat_sync") == "none":
            beats = []
        elif music_duration < duration:
            beats = sorted(
                loop * music_duration + beat
                for loop in range(int(duration / music_duration) + 1)
                for beat in source_beats
                if loop * music_duration + beat < duration
            )
        else:
            beats = [beat - music_start for beat in source_beats
                     if music_start <= beat < music_start + duration]
    else:
        bpm = 100 if fmt_id == 3 else 120
        beats = [round(k * (60.0 / bpm), 4) for k in range(int(duration / (60.0 / bpm)) + 1)]
        if plan["music"].get("beat_sync") == "downbeats":
            beats = beats[::4]
        elif plan["music"].get("beat_sync") == "none":
            beats = []
    beat_period = 60.0 / bpm
    if music_enabled:
        report_progress("music", 0.1,
                        f"Analisando a trilha enviada a {bpm:.0f} BPM" if custom_music
                        else f"Criando trilha a {bpm} BPM")
        music = job_dir / "music.wav"
        if custom_music is not None:
            fade_start = max(0.0, duration - min(1.0, duration / 4))
            run_ffmpeg(["-stream_loop", "-1", "-ss", f"{music_start:.3f}", "-i", str(custom_music),
                        "-t", f"{duration:.3f}", "-af",
                        f"aresample=48000,apad,atrim=duration={duration:.3f},"
                        f"afade=t=out:st={fade_start:.3f}:d={duration - fade_start:.3f}",
                        "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", str(music)])
        else:
            generate_procedural_music(music, bpm=bpm, duration_s=duration, seed=fmt_id)
        if speech_enabled:
            report_progress("music", 0.6, "Abaixando a trilha sob a voz (ducking)")
            ducked_music = job_dir / "music_ducked.wav"
            duck_music_under_voice(music, voice, ducked_music, plan["music"].get("ducking_db", -14))
        else:
            ducked_music = music
    report_progress("music", 1.0, "Trilha e grade de batidas prontas")
    word_list = []
    subs = job_dir / "subs.ass"
    words_per_second = 0.0
    if speech_enabled:
        report_progress("subtitles", 0.2, "Sincronizando legendas com a duração real da voz")
        tokens = text.split()
        # Tempo de cada palavra proporcional ao nº de letras, dentro da duração real da locução.
        span = min(duration, voice_duration or duration * .5)
        weights = [max(2, len(t)) for t in tokens]
        total_w = sum(weights) or 1
        cursor = 0.0
        for word, weight in zip(tokens, weights):
            width = span * weight / total_w
            word_list.append({"word": word, "start": cursor, "end": min(duration, cursor + width)})
            cursor += width
        words_per_second = len(tokens) / max(span, 0.1)
        generate_karaoke_ass_subtitles(word_list, subs, plan["subtitles"]["hook_overlay"])
        report_progress("subtitles", 1.0, f"Legendas prontas ({words_per_second:.1f} palavras/s)")
    else:
        report_progress("subtitles", 1.0, "Legendas desligadas")
    plan_file = job_dir / "edit_plan.json"
    plan_file.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    asset_by_id = {a["id"]: a for a in assets}
    playable = [a for a in assets if a["kind"] in {"video", "image"}]
    if not playable:
        raise ValueError("plano sem vídeo ou imagem para montar")
    report_progress("render", 0.0, "Escolhendo o melhor gancho e planejando os cortes")
    shots = _plan_shots(plan, assets, beats, beat_period)
    media_inputs: list[str] = []
    timeline_filters = []
    video_indices: list[int] = []
    for i, shot in enumerate(shots):
        asset, part_duration, zoom = shot["asset"], shot["length"], shot["zoom"]
        input_index = len(video_indices)
        path = str(Path(asset["path"]).resolve())
        if asset["kind"] == "video":
            media_inputs.extend(["-stream_loop", "-1", "-ss", f"{shot['offset']:.3f}",
                                 "-t", f"{part_duration + .2:.3f}", "-i", path])
            video_filter = ("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
                            f"scale=iw*{zoom}:ih*{zoom},crop=1080:1920,setsar=1,fps=30")
        else:
            frames = max(1, round(part_duration * 30))
            step = (zoom - 1.0) / frames if zoom > 1.0 else 0.0004
            media_inputs.extend(["-loop", "1", "-framerate", "30", "-t", f"{part_duration + .2:.3f}",
                                 "-i", path])
            video_filter = ("scale=1080:1920:force_original_aspect_ratio=decrease,"
                            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,"
                            f"zoompan=z='min({max(zoom, 1.04):.3f},1+on*{step:.6f})':d=1:s=1080x1920:fps=30")
        video_indices.append(input_index)
        timeline_filters.append(
            f"[{input_index}:v]{video_filter},trim=duration={part_duration:.3f},"
            f"setpts=PTS-STARTPTS,format=yuv420p[v{i}]")
    concat_inputs = "".join(f"[v{i}]" for i in range(len(timeline_filters)))
    timeline_filters.append(f"{concat_inputs}concat=n={len(timeline_filters)}:v=1:a=0[vbase]")
    engines = {"asr": "none", "tts": tts_result["engine"], "llm": "template_engine",
               "vlm": "heuristic_only",
               "music": ("user_uploaded_track" if custom_music else "procedural_generator")
               if music_enabled else "disabled",
               "depth": "geometric",
               "subject_detection": "opencv_saliency"}
    license_keys += ["opencv", "scenedetect"]
    has_source_audio = keep_source_audio
    if keep_source_audio:
        audio_parts, any_audio = [], False
        for idx, shot in enumerate(shots):
            asset, length = shot["asset"], shot["length"]
            has_audio = asset.get("kind") == "video" and any(
                st.get("codec_type") == "audio" for st in ffprobe_json(asset["path"]).get("streams", []))
            if has_audio:
                any_audio = True
                timeline_filters.append(
                    f"[{idx}:a]atrim=duration={length:.3f},apad=whole_dur={length:.3f},asetpts=PTS-STARTPTS,"
                    f"aresample=48000,aformat=channel_layouts=stereo[sa{idx}]")
            else:
                timeline_filters.append(f"anullsrc=r=48000:cl=stereo:d={length:.3f}[sa{idx}]")
            audio_parts.append(f"[sa{idx}]")
        if not any_audio:
            raise ValueError("Não encontrei faixa de áudio nos vídeos selecionados para manter o som original.")
        timeline_filters.append(f"{''.join(audio_parts)}concat=n={len(audio_parts)}:v=0:a=1,volume=0.125[source_audio]")
    if speech_enabled:
        ass_path = str(subs).replace("\\", "\\\\").replace(":", "\\:")
        fonts_dir = str(ROOT / "assets" / "fonts").replace("\\", "\\\\").replace(":", "\\:")
        timeline_filters.append(f"[vbase]ass='{ass_path}':fontsdir='{fonts_dir}'[v]")
    else:
        timeline_filters.append("[vbase]null[v]")
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    audio_inputs: list[str] = []
    audio_labels: list[str] = []
    next_input = len(video_indices)
    if speech_enabled:
        audio_inputs.extend(["-i", str(voice)])
        timeline_filters.append(f"[{next_input}:a]volume=0.7[voice]")
        audio_labels.append("[voice]")
        next_input += 1
    if music_enabled:
        audio_inputs.extend(["-i", str(ducked_music)])
        timeline_filters.append(f"[{next_input}:a]volume=0.20[music]")
        audio_labels.append("[music]")
        next_input += 1
    if has_source_audio:
        audio_labels.append("[source_audio]")
    if not audio_labels:
        raise ValueError("Não há nenhuma faixa de áudio habilitada para o Reel.")
    if len(audio_labels) == 1:
        audio_graph = f"{audio_labels[0]}loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    else:
        audio_graph = ("".join(audio_labels) +
                       f"amix=inputs={len(audio_labels)}:duration=longest:dropout_transition=0,"
                       "loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    command = [ffmpeg, "-hide_banner", "-nostats", "-y", *media_inputs, *audio_inputs,
               "-filter_complex", ";".join(timeline_filters) + ";" + audio_graph,
               "-map", "[v]", "-map", "[a]", "-t", f"{duration:.3f}",
               "-r", "30", "-fps_mode", "cfr", "-c:v", "libx264", "-preset", "veryfast",
               "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
               "-c:a", "aac", "-ar", "48000", "-b:a", "192k", str(output)]
    report_progress("render", 0.02, f"Renderizando {len(shots)} planos em 1080×1920")
    _run_ffmpeg_with_progress(command, duration, report_progress)
    report_progress("audit", 0.2, "Conferindo resolução, codec, loudness e taxa de quadros")
    audit = _audit(output, fmt_id)
    report_progress("audit", 1.0, "Auditoria técnica aprovada" if audit.get("passed") else "Auditoria encontrou problemas")
    report = {"job_id": job_id, "format_id": fmt_id, "output": str(output),
              "duration_s": audit.get("duration_s"), "engines": engines,
              "license_keys": list(dict.fromkeys(license_keys)),
              "license_warnings": license_warnings, "degraded": ["degraded_voice"]
              if speech_enabled and tts_result["engine"] == "placeholder_tone" else [],
              "commercial": commercial, "cuts": {"planned": plan["cut"]["planned_cuts"],
                                                      "timeline": len(shots) - 1},
              "viral": {"shots": len(shots), "voice_duration_s": round(voice_duration, 2),
                        "words_per_second": round(words_per_second, 2),
                        "first_3s_states": sum(1 for sh in shots if sh["start"] < 3.0),
                        "beat_grid": plan["music"].get("beat_sync"),
                        "music_source": "user_upload" if custom_music else "procedural",
                        "music_start_s": round(music_start, 2)},
              "audit": audit, "elapsed_s": round(time.monotonic() - started, 2)}
    try:
        from src.analise.score_viral import pontuar_video
        report["potencial_viral"] = pontuar_video(output, com_fala=False)
    except Exception as exc:  # indicador é auxiliar: nunca derruba o render
        report["potencial_viral"] = {"nota": None, "erro": str(exc)[:200]}
    (job_dir / "render_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                                encoding="utf-8")
    if not audit["passed"]:
        raise RuntimeError(f"auditoria do render falhou: {[c for c in audit['checks'] if not c['ok']]}")
    return report
