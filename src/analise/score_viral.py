"""Indicador de potencial viral: quão parecido o Reel gerado é com o top 10% da base (250 Reels de alto desempenho).

Não é uma previsão de views: é a aderência do vídeo ao *perfil de execução* dos Reels que performaram bem
(ritmo de cortes, fala, rosto, movimento, legibilidade). Cada feature vale 100 dentro da faixa P25–P75 do top 10%,
cai linearmente até 40 em P5/P95 e até 0 além disso. A nota final é a média ponderada; o percentil mostra onde o
vídeo ficaria entre os 250 de referência.

Uso: python -m src.analise.score_viral VIDEO [--formato pas] [--sem-fala] [--referencia dados/analise_top10]
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

REFERENCIA = Path("dados/analise_top10")
# (feature, peso, rótulo, dica quando abaixo, dica quando acima). Peso 0 = só informativo.
FEATURES = (
    ("duration_sec", 1.0, "duração", "Reel curto demais frente ao top 10%: desenvolva mais a história.", "Reel mais longo que o top 10%: corte o que não sustenta atenção."),
    ("cuts_per_minute", 2.0, "cortes por minuto", "Poucos cortes: troque de plano com mais frequência.", "Cortes demais: dê respiro entre os planos."),
    ("words_per_minute", 1.5, "palavras por minuto", "Fala lenta: enxugue o roteiro ou acelere a locução.", "Fala rápida demais: reduza palavras para ficar legível."),
    ("speech_activity_ratio", 1.0, "fala ativa", "Muito silêncio: preencha com narração ou música.", "Sem pausas: deixe respirar."),
    ("face_detected_ratio", 1.5, "presença de rosto", "Pouco rosto: abra ou feche com uma pessoa em quadro.", "Rosto o tempo todo: inclua planos de produto."),
    ("max_face_area_pct", 1.0, "tamanho do rosto", "Rosto pequeno: aproxime o enquadramento.", "Rosto grande demais: afaste um pouco."),
    ("optical_flow_25d_score", 1.5, "movimento nos 3s iniciais", "Início parado: acrescente movimento/zoom nos 3 primeiros segundos.", "Movimento excessivo no início."),
    ("subtitle_zone_contrast", 1.0, "contraste da legenda", "Legenda com pouco contraste: use fundo/contorno.", "Contraste da zona da legenda fora do padrão."),
)
RECORTE_MIN_AMOSTRAS = 25


def carregar_referencia(pasta: Path = REFERENCIA, formato: str | None = None) -> list[dict]:
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((pasta / "features").glob("*.json"))]
    if formato:
        cls = pasta / "format_classification.json"
        if cls.exists():
            fmt = {i["shortcode"]: i.get("formato") for i in json.loads(cls.read_text(encoding="utf-8"))}
            sub = [r for r in rows if fmt.get(r["shortcode"]) == formato]
            if len(sub) >= RECORTE_MIN_AMOSTRAS:
                return sub
    return rows


def _nota_feature(valor: float, ref: np.ndarray) -> float:
    p5, p25, p75, p95 = np.percentile(ref, [5, 25, 75, 95])
    if p25 <= valor <= p75:
        return 100.0
    if valor < p25:
        folga = max(p25 - p5, 1e-9)
        return float(np.interp(valor, [p5 - folga, p5, p25], [0, 40, 100]))
    folga = max(p95 - p75, 1e-9)
    return float(np.interp(valor, [p75, p95, p95 + folga], [100, 40, 0]))


def pontuar(feats: dict, referencia: list[dict]) -> dict:
    detalhes, dicas, soma, peso_total = [], [], 0.0, 0.0
    for chave, peso, rotulo, dica_baixo, dica_alto in FEATURES:
        v = feats.get(chave)
        ref = np.array([r[chave] for r in referencia if r.get(chave) is not None], float)
        if v is None or len(ref) < 10:
            continue
        nota = _nota_feature(float(v), ref)
        p25, med, p75 = np.percentile(ref, [25, 50, 75])
        detalhes.append({"feature": chave, "rotulo": rotulo, "valor": round(float(v), 3), "nota": round(nota),
                         "faixa_top10": [round(float(p25), 3), round(float(med), 3), round(float(p75), 3)]})
        soma += nota * peso
        peso_total += peso
        if nota < 70:
            dicas.append((nota, dica_baixo if v < p25 else dica_alto))
    nota = round(soma / peso_total) if peso_total else None
    # percentil: fração dos Reels de referência cuja própria nota é menor ou igual
    notas_ref = []
    for r in referencia:
        s = p = 0.0
        for chave, peso, *_ in FEATURES:
            if r.get(chave) is None:
                continue
            ref = np.array([x[chave] for x in referencia if x.get(chave) is not None], float)
            s += _nota_feature(float(r[chave]), ref) * peso
            p += peso
        if p:
            notas_ref.append(s / p)
    percentil = round(100 * float(np.mean(np.array(notas_ref) <= (soma / peso_total)))) if notas_ref and peso_total else None
    faixa = None if nota is None else "alto" if nota >= 75 else "médio" if nota >= 55 else "baixo"
    return {"nota": nota, "faixa": faixa, "percentil_vs_top10": percentil, "n_referencia": len(referencia),
            "detalhes": detalhes, "melhorias": [d for _, d in sorted(dicas)][:4],
            "aviso": "Aderência ao padrão dos Reels de alto desempenho; não garante viralização."}


def extrair_features(video: Path, com_fala: bool = True, modelo: str = "small") -> dict:
    from src.analise import features as F
    from src.core.ffmpeg import ffprobe_json

    dur = float(ffprobe_json(video)["format"]["duration"])
    with tempfile.TemporaryDirectory() as tmp:
        frames = F.extrair_frames(video, dur, Path(tmp))
        feats = {"duration_sec": dur, "cuts_per_minute": round(F.cortes(video) / dur * 60, 2), **F.features_visuais(frames, video)}
    if F.tem_audio(video):
        n_sil, ratio = F.silencio(video, dur)
        feats["silence_count"], feats["speech_activity_ratio"] = n_sil, ratio
        if com_fala:
            try:
                from faster_whisper import WhisperModel

                palavras = F.transcrever(WhisperModel(modelo, device="cpu", compute_type="int8"), video)["words"]
                fala = (palavras[-1][1] - palavras[0][0]) if palavras else 0.0
                feats["words_per_minute"] = round(len(palavras) / fala * 60, 2) if fala > 0 else 0.0
            except Exception:  # sem faster-whisper/pesos: a nota ignora a feature
                pass
    return feats


def pontuar_video(video: Path, formato: str | None = None, com_fala: bool = True,
                  pasta_ref: Path = REFERENCIA) -> dict:
    ref = carregar_referencia(pasta_ref, formato)
    res = pontuar(extrair_features(Path(video), com_fala), ref)
    res["formato_referencia"] = formato
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--formato", default=None, help="bab | product_demo_pas | ugc_testimonial | pas | aida")
    ap.add_argument("--sem-fala", action="store_true")
    ap.add_argument("--referencia", default=str(REFERENCIA))
    a = ap.parse_args(argv)
    print(json.dumps(pontuar_video(Path(a.video), a.formato, not a.sem_fala, Path(a.referencia)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
