"""Padrões de EDIÇÃO dos Reels da base: tempos de corte, zoom in/out, punch-in, ritmo e gancho.

Uso:
    python -m src.analise.edicao_padroes extrair [--limite N] [--workers 10]   # checkpoint por vídeo
    python -m src.analise.edicao_padroes agregar                              # top 10% x controle -> JSON
Tudo local (ffmpeg + OpenCV), custo zero. Vídeos só para análise interna (docs/base_de_dados.md, seção 1).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
cv2.setNumThreads(1)
import numpy as np

BASE = Path("dados")
SAIDA = BASE / "analise_edicao"
FPS, LW, LH, MAX_S = 8, 96, 170, 75


def amostrar(video: Path) -> np.ndarray:
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-loglevel", "error", "-t", str(MAX_S), "-i", str(video), "-an",
           "-vf", f"fps={FPS},scale={LW}:{LH}", "-pix_fmt", "gray", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    n = len(raw) // (LW * LH)
    return np.frombuffer(raw[: n * LW * LH], np.uint8).reshape(n, LH, LW)


def _hist(f: np.ndarray) -> np.ndarray:
    h = cv2.calcHist([f], [0], None, [32], [0, 256])
    return cv2.normalize(h, h).flatten()


def detectar_cortes(q: np.ndarray) -> list[int]:
    cortes = []
    hs = [_hist(f) for f in q]
    for i in range(1, len(q)):
        d = float(np.mean(cv2.absdiff(q[i], q[i - 1])))
        corr = cv2.compareHist(hs[i - 1], hs[i], cv2.HISTCMP_CORREL)
        if (corr < 0.6 and d > 14) or d > 48:
            if not cortes or i - cortes[-1] >= 3:  # no mínimo ~0,4 s entre cortes
                cortes.append(i)
    return cortes


def zoom_do_plano(q: np.ndarray, a: int, b: int) -> float:
    """Variação logarítmica de escala do plano [a,b): >0 aproxima (push-in), <0 afasta (pull-out)."""
    if b - a < 4:
        return 0.0
    yy, xx = np.mgrid[0:LH, 0:LW].astype(np.float32)
    dx, dy = xx - LW / 2, yy - LH / 2
    r2 = dx * dx + dy * dy
    m = r2 > 15 ** 2
    total = 0.0
    for i in range(a + 1, b):
        fl = cv2.calcOpticalFlowFarneback(q[i - 1], q[i], None, 0.5, 2, 9, 2, 5, 1.1, 0)
        total += float(np.mean(((fl[..., 0] * dx + fl[..., 1] * dy)[m]) / r2[m]))
    return total


def _escala(frame: np.ndarray, s: float) -> np.ndarray:
    h, w = frame.shape
    ch, cw = int(h / s), int(w / s)
    y0, x0 = (h - ch) // 2, (w - cw) // 2
    return cv2.resize(frame[y0:y0 + ch, x0:x0 + cw], (w, h))


def punch_no_corte(antes: np.ndarray, depois: np.ndarray) -> bool:
    """Corte 'de ajuste': mesmo enquadramento, ampliado ~10-40% (punch-in) ou reduzido."""
    def corr(x, y):
        return float(cv2.matchTemplate(x, y, cv2.TM_CCOEFF_NORMED)[0][0])
    base = corr(antes, depois)
    melhor = max([corr(_escala(antes, s), depois) for s in (1.1, 1.2, 1.3, 1.45)]
                 + [corr(antes, _escala(depois, s)) for s in (1.1, 1.2, 1.3, 1.45)])
    return melhor > 0.55 and melhor > base + 0.15


GANCHOS = {
    "pergunta": r"\?|^(você|vc|quem|qual|quanto|como|por que|por quê|será|já)\b",
    "numero_valor": r"\d|r\$|\bmil\b|milh[aã]o|%|\bzero\b",
    "erro_dor": r"\b(erro|errad[oa]|pare de|nunca|jamais|n[aã]o fa[cç]a|ningu[eé]m (te )?(conta|fala)|cuidado|perde[nr]?|preju[ií]zo|quebr|armadilha|problema)\b",
    "promessa_como": r"\b(como (eu|voc[eê]|fazer|ganhar|vender|lucrar|precificar|criar)|passo a passo|aprenda|descubra|vou (te )?(mostrar|ensinar)|segredo|m[eé]todo|dica)\b",
    "historia_prova": r"\b(eu (era|fui|tinha|comecei|faturei|quebrei|perdi)|minha hist[oó]ria|h[aá] \w+ anos|quando eu|aconteceu)\b",
    "segmentacao": r"\b(se voc[eê] (é|e|tem|vende|quer|trabalha)|mei\b|empreendedor|dono de|microempreendedor|aut[oô]nomo)\b",
    "urgencia_novidade": r"\b(aten[cç][aã]o|urgente|novidade|novo|agora|hoje|acabou de|mudou|olha isso|importante)\b",
    "imperativo": r"^(pare|olha|olhe|escuta|presta|veja|assista|salva|guarda|espera)\b",
}
CTAS = {
    "comente": r"\b(coment[ae]|deixa (nos )?coment)",
    "siga": r"\b(segue|siga|seguir)\b",
    "link_bio": r"link na bio|link (da|na) (bio|descri)",
    "direct_whats": r"\b(direct|whats|chama|me chama|manda (uma )?mensagem|fale com)",
    "salve_compartilhe": r"\b(salva|salve|compartilh|manda pra)",
}


def classificar(texto: str, tabela: dict[str, str]) -> list[str]:
    t = (texto or "").lower().strip()
    return [k for k, rx in tabela.items() if re.search(rx, t)]


def analisar(shortcode: str, video: Path, feat: dict | None) -> dict:
    q = amostrar(video)
    n = len(q)
    dur = n / FPS
    cortes = detectar_cortes(q)
    lim = [0, *cortes, n]
    planos = [(lim[i], lim[i + 1]) for i in range(len(lim) - 1) if lim[i + 1] - lim[i] >= 2]
    zooms = [zoom_do_plano(q, a, b) for a, b in planos]
    cls = ["push_in" if z > .05 else "pull_out" if z < -.05 else "estatico" for z in zooms]
    punches = [i for i in cortes if 0 < i < n and punch_no_corte(q[i - 1], q[i])]
    movimento = float(np.mean([np.mean(cv2.absdiff(q[i], q[i - 1])) for i in range(1, min(n, 3 * FPS))])) if n > 2 else 0.0
    bins = np.zeros(10)
    for c in cortes:
        bins[min(9, int(10 * c / max(n, 1)))] += 1
    texto = (feat or {}).get("transcript_text") or ""
    gancho = (feat or {}).get("hook_transcript_3s") or ""
    cauda = texto[int(len(texto) * .82):]
    return {
        "shortcode": shortcode, "duracao_analisada_s": round(dur, 1), "n_cortes": len(cortes),
        "tempos_corte_s": [round(c / FPS, 2) for c in cortes], "n_planos": len(planos),
        "duracao_plano_mediana_s": round(float(np.median([(b - a) / FPS for a, b in planos])), 2) if planos else dur,
        "primeiro_corte_s": round(cortes[0] / FPS, 2) if cortes else None,
        "cortes_nos_3s": sum(1 for c in cortes if c / FPS <= 3), "cortes_por_min": round(len(cortes) / dur * 60, 2),
        "planos_push_in": cls.count("push_in"), "planos_pull_out": cls.count("pull_out"), "planos_estaticos": cls.count("estatico"),
        "punch_in_cortes": len(punches), "punch_in_por_min": round(len(punches) / dur * 60, 2),
        "movimento_3s": round(movimento, 2), "perfil_cortes_decis": bins.astype(int).tolist(),
        "gancho_tipos": classificar(gancho, GANCHOS), "gancho_palavras": len(gancho.split()),
        "primeira_palavra_s": (feat or {}).get("first_word_timestamp_sec"), "cta_tipos": classificar(cauda, CTAS),
        "wpm": (feat or {}).get("words_per_minute"),
    }


def _job(args):
    sc, video, feat, saida = args
    out = Path(saida) / f"{sc}.json"
    if out.exists():
        return sc, True
    try:
        out.write_text(json.dumps(analisar(sc, Path(video), feat), ensure_ascii=False))
        return sc, True
    except Exception as exc:  # vídeo corrompido não derruba o lote
        return sc, f"{type(exc).__name__}: {exc}"[:120]


def _features() -> dict[str, dict]:
    feats = {}
    for d in ("analise_top10", "analise_controle"):
        for f in (BASE / d / "features").glob("*.json"):
            feats[f.stem] = json.loads(f.read_text())
    return feats


def extrair(limite: int | None, workers: int) -> None:
    import pandas as pd
    rank = pd.read_parquet(BASE / "base" / "ranking.parquet").set_index("post_id")
    feats = _features()
    SAIDA.mkdir(parents=True, exist_ok=True)
    itens = [(p.parent.name, str(p), feats.get(p.parent.name), str(SAIDA))
             for p in sorted((BASE / "midia" / "instagram").glob("*/video.mp4")) if p.parent.name in rank.index]
    if limite:
        itens = itens[:limite]
    erros = 0
    with ProcessPoolExecutor(workers) as ex:
        for i, (sc, r) in enumerate(ex.map(_job, itens), 1):
            if r is not True:
                erros += 1
                print("ERRO", sc, r)
            if i % 25 == 0:
                print(f"{i}/{len(itens)}", flush=True)
    print(f"feito: {len(itens)} vídeos, {erros} erros")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extrair")
    e.add_argument("--limite", type=int)
    e.add_argument("--workers", type=int, default=10)
    sub.add_parser("agregar")
    a = ap.parse_args(argv)
    if a.cmd == "extrair":
        extrair(a.limite, a.workers)
    else:
        from src.analise.edicao_agregar import agregar
        agregar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
