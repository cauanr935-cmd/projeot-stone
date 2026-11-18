"""Etapa 3: transcrição (faster-whisper int8) + features de áudio/cortes/frames dos Reels do top 10%.

Uso:
    python -m src.analise.features [--manifesto dados/analise_top10/manifesto_midia.json]
        [--saida dados/analise_top10] [--modelo small] [--limite N]
Checkpoint por shortcode em <saida>/features/<shortcode>.json (reexecutar retoma de onde parou).
Tudo local, custo zero. Detector de rosto: YuNet (models/opencv, MIT) porque o OpenCV 5 não traz os Haar XML.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

from src.core.ffmpeg import ffprobe_json, resolve_binaries, run_ffmpeg
from src.core.logging import configure_logging

log = logging.getLogger(__name__)
YUNET = Path("models/opencv/face_detection_yunet_2023mar.onnx")
FRAME_PONTOS = (("t0_5", 0.5), ("t2_0", 2.0), ("p25", 0.25), ("p50", 0.50), ("p85", 0.85))
CHAVES_NUM = ("duration_sec", "word_count", "words_per_minute", "first_word_timestamp_sec", "silence_count",
              "speech_activity_ratio", "scene_cut_count", "cuts_per_minute", "face_detected_ratio",
              "max_face_area_pct", "optical_flow_25d_score", "subtitle_zone_contrast")


def _ffmpeg_stderr(args: list[str]) -> str:
    return run_ffmpeg(args, check=False).stderr


def silencio(video: Path, duracao: float, noise_db: int = -35, min_dur: float = 0.4) -> tuple[int, float]:
    err = _ffmpeg_stderr(["-vn", "-i", video, "-af", f"silencedetect=noise={noise_db}dB:d={min_dur}", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*(-?[\d.]+)", err)]
    if len(ends) < len(starts):
        ends.append(duracao)
    total = sum(max(0.0, e - max(s, 0.0)) for s, e in zip(starts, ends))
    return len(starts), round(max(0.0, min(1.0, 1 - total / duracao)), 4)


def cortes(video: Path, limiar: float = 0.3) -> int:
    err = _ffmpeg_stderr(["-i", video, "-an", "-vf", f"select='gt(scene,{limiar})',showinfo", "-f", "null", "-"])
    return len(re.findall(r"pts_time:", err))


def extrair_frames(video: Path, duracao: float, destino: Path) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    out = []
    for i, (nome, ponto) in enumerate(FRAME_PONTOS, start=1):
        t = min(ponto, duracao * 0.9) if nome.startswith("t") else duracao * ponto
        arq = destino / f"frame_{i}.jpg"
        run_ffmpeg(["-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", 1, "-vf", "scale=540:-2", "-q:v", 3, arq])
        if arq.exists() and arq.stat().st_size > 1000:
            out.append(arq)
    return out


def features_visuais(frames: list[Path], video: Path) -> dict:
    det = cv2.FaceDetectorYN.create(str(YUNET), "", (320, 320), 0.7) if YUNET.exists() else None
    com_rosto, area_max, contrastes = 0, 0.0, []
    for f in frames:
        img = cv2.imread(str(f))
        if img is None:
            continue
        h, w = img.shape[:2]
        if det is not None:
            det.setInputSize((w, h))
            _, faces = det.detect(img)
            if faces is not None and len(faces):
                com_rosto += 1
                area_max = max(area_max, max(float(r[2] * r[3]) for r in faces) / (w * h) * 100)
        banda = cv2.cvtColor(img[int(h * .60):int(h * .85)], cv2.COLOR_BGR2GRAY)
        contrastes.append(float((cv2.Canny(banda, 100, 200) > 0).mean()))
    return {"face_detected_ratio": round(com_rosto / max(len(frames), 1), 4), "max_face_area_pct": round(area_max, 3),
            "optical_flow_25d_score": fluxo(video),
            "subtitle_zone_contrast": round(float(np.mean(contrastes)) if contrastes else 0.0, 5)}


def fluxo(video: Path, segundos: float = 3.0, fps: int = 5) -> float:
    """Magnitude média do fluxo óptico Farneback nos primeiros segundos (proxy de movimento/parallax)."""
    cap = cv2.VideoCapture(str(video))
    passo = max(int(round((cap.get(cv2.CAP_PROP_FPS) or 30) / fps)), 1)
    prev, mags, i = None, [], 0
    while i < segundos * fps * passo:
        ok, fr = cap.read()
        if not ok:
            break
        if i % passo == 0:
            g = cv2.cvtColor(cv2.resize(fr, (144, 256)), cv2.COLOR_BGR2GRAY)
            if prev is not None:
                mags.append(float(np.linalg.norm(cv2.calcOpticalFlowFarneback(prev, g, None, .5, 2, 9, 2, 5, 1.1, 0), axis=2).mean()))
            prev = g
        i += 1
    cap.release()
    return round(float(np.mean(mags)) if mags else 0.0, 4)


def tem_audio(video: Path) -> bool:
    return bool(ffprobe_json(video).get("streams")) and any(
        st.get("codec_type") == "audio" for st in ffprobe_json(video)["streams"])


def decodificar_audio(video: Path) -> np.ndarray:
    """PCM float32 mono 16 kHz via ffmpeg (evita o decode_audio do faster-whisper, que exige um `av` mais novo)."""
    proc = subprocess.run([resolve_binaries()["ffmpeg"], "-hide_banner", "-nostats", "-loglevel", "error", "-i", str(video),
                           "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True)
    return np.frombuffer(proc.stdout, dtype=np.float32)


def transcrever(model, video: Path) -> dict:
    audio = decodificar_audio(video)
    if audio.size < 16000:
        return {"transcript_text": "", "words": []}
    segs, _ = model.transcribe(audio, language="pt", beam_size=5, vad_filter=True, word_timestamps=True)
    palavras, textos = [], []
    for s in segs:
        textos.append(s.text.strip())
        palavras += [(w.start, w.end, w.word) for w in (s.words or [])]
    return {"transcript_text": " ".join(textos).strip(), "words": palavras}


def processar(item: dict, model, saida: Path) -> dict:
    video = Path(item["video_path"])
    sc = item["shortcode"]
    dur = float(item["duration_sec"])
    tr = transcrever(model, video)
    palavras = tr["words"]
    n = len(palavras)
    fala = (palavras[-1][1] - palavras[0][0]) if n else 0.0
    audio = tem_audio(video)
    n_sil, ratio = silencio(video, dur) if audio else (0, 0.0)
    n_cortes = cortes(video)
    frames = extrair_frames(video, dur, saida / "frames" / sc)
    feats = {
        "shortcode": sc, "profile": item["profile"], "has_audio": audio, "frames_ok": len(frames), "duration_sec": dur,
        "transcript_text": tr["transcript_text"], "word_count": n,
        "words_per_minute": round(n / fala * 60, 2) if fala > 0 else 0.0,
        "first_word_timestamp_sec": round(palavras[0][0], 3) if n else None,
        "hook_transcript_3s": " ".join(w[2].strip() for w in palavras if w[0] < 3.0),
        "silence_count": n_sil, "speech_activity_ratio": ratio,
        "scene_cut_count": n_cortes, "cuts_per_minute": round(n_cortes / dur * 60, 2),
        **features_visuais(frames, video),
    }
    return feats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifesto", default="dados/analise_top10/manifesto_midia.json")
    ap.add_argument("--saida", default="dados/analise_top10")
    ap.add_argument("--modelo", default="small")
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--inicio", type=int, default=0, help="índice inicial (para rodar faixas em paralelo)")
    ap.add_argument("--threads", type=int, default=8)
    args = ap.parse_args(argv)
    configure_logging()
    from faster_whisper import WhisperModel

    saida = Path(args.saida)
    (saida / "features").mkdir(parents=True, exist_ok=True)
    itens = json.loads(Path(args.manifesto).read_text())["itens"]
    itens = itens[args.inicio:] + itens[: args.inicio]  # processa a partir de `inicio`, depois o resto
    if args.limite:
        itens = itens[: args.limite]
    model = WhisperModel(args.modelo, device="cpu", compute_type="int8", cpu_threads=args.threads)
    falhas = 0
    for i, it in enumerate(itens, start=1):
        cp = saida / "features" / f"{it['shortcode']}.json"
        if cp.exists():
            continue
        try:
            cp.write_text(json.dumps(processar(it, model, saida), ensure_ascii=False))
        except Exception as e:  # noqa: BLE001
            falhas += 1
            log.error("falhou %s: %s", it["shortcode"], e)
        print(f"{i}/{len(itens)} {it['shortcode']}", flush=True)
    todos = [json.loads(p.read_text()) for p in sorted((saida / "features").glob("*.json"))]
    (saida / "multimodal_features.json").write_text(json.dumps(todos, ensure_ascii=False, indent=1))
    print(f"consolidado: {len(todos)} Reels; falhas={falhas}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
