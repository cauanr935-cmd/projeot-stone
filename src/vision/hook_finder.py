def find_hooks(duration_s: float, count: int = 3) -> list[dict]:
    hooks = []
    for i in range(count):
        start = duration_s * i / max(count, 1)
        end = min(duration_s, start + 3.2)
        if end - start >= 2.5:
            hooks.append({"start": start, "end": end, "score": max(.4, .9 - i * .1),
                          "components": {"A": .8, "F": .8, "E": .8, "L": .8, "V": .8}})
    return hooks


def best_hook_window(video_path, window_s: float = 3.2, samples_per_window: int = 6,
                     max_windows: int = 40) -> dict:
    """Pontua janelas de um vídeo real para escolher o melhor gancho (Frame Zero).

    Score = 0,45·movimento + 0,35·rosto/ponto focal no 1º frame − 0,20·complexidade de fundo,
    todos normalizados em 0..1. Baixa entropia visual + movimento dinâmico (pesquisa, seção
    "Ciência da Retenção"). Roda só com OpenCV; qualquer falha devolve início do vídeo.
    """
    import cv2
    import numpy as np

    fallback = {"start": 0.0, "end": window_s, "score": 0.0, "components": {}}
    cap = cv2.VideoCapture(str(video_path))
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        duration = total / fps if total else 0.0
        if duration <= window_s + 0.5:
            return fallback | {"end": max(duration, 0.1)}
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        step = max(1.0, (duration - window_s) / max_windows)
        best = fallback
        t = 0.0
        while t + window_s <= duration:
            grays = []
            for k in range(samples_per_window):
                cap.set(cv2.CAP_PROP_POS_MSEC, (t + k * window_s / samples_per_window) * 1000)
                ok, frame = cap.read()
                if not ok:
                    break
                small = cv2.resize(frame, (160, 284))
                grays.append(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY))
            if len(grays) >= 2:
                motion = float(np.mean([np.mean(cv2.absdiff(a, b)) for a, b in zip(grays, grays[1:])]) / 40.0)
                first = grays[0]
                faces = face_cascade.detectMultiScale(first, 1.2, 4, minSize=(24, 24))
                focal = 1.0 if len(faces) else 0.0
                clutter = float(np.mean(cv2.Canny(first, 80, 160)) / 255.0 * 4)
                comp = {"motion": min(1.0, motion), "focal": focal, "clutter": min(1.0, clutter)}
                score = 0.45 * comp["motion"] + 0.35 * comp["focal"] - 0.20 * comp["clutter"]
                if score > best["score"] or best is fallback:
                    best = {"start": round(t, 2), "end": round(t + window_s, 2),
                            "score": round(score, 4), "components": comp}
            t += step
        return best
    except Exception:
        return fallback
    finally:
        cap.release()
