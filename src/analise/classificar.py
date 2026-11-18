"""Etapa 4: classifica os Reels do top 10% nos 5 formatos (config/formats.yaml) e mede desempenho por formato.

Uso:
    python -m src.analise.classificar [--dir dados/analise_top10] [--base dados/base] [--ollama llama3.2:3b]

Classificador determinístico (léxico de cues narrativos na legenda + transcrição, com um pequeno peso de
features visuais) com 100% de cobertura offline. Com --ollama, um LLM local (custo zero) refina o rótulo
via saída estruturada; sem daemon disponível cai silenciosamente no determinístico.
Os 5 formatos são frameworks de copy (BAB, Demo+PAS, UGC, PAS, AIDA): o rótulo é uma estimativa da
estrutura retórica dominante, não uma verdade de campo. Ver limitações no relatório gerado.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

from src.core.config import load_formats

log = logging.getLogger(__name__)

# cue -> peso. Texto é normalizado (minúsculo, sem acento).
LEXICO: dict[str, dict[str, float]] = {
    "bab": {r"\bantes\b": 1.5, r"\bdepois\b": 1.5, r"\bagora\b": .7, r"transform": 2, r"\bmudou\b": 1.2,
            r"\bhoje\b": .3, r"de \w+ para \w+": 1.2, r"\bresultado\b": .8, r"\bevolu": 1},
    "product_demo_pas": {r"passo a passo": 2, r"\bveja\b": 1, r"\bapp\b": 1, r"\bsistema\b": 1, r"plataforma": 1,
                         r"como funciona": 2, r"\btela\b": 1, r"\bferramenta": 1.2, r"\bplanilha\b": 1.2,
                         r"\bmostrar\b": 1, r"\bcalcul": 1.2, r"\bemitir\b": 1, r"\bmaquininha\b": 1.5, r"\bconta\b": .4},
    "ugc_testimonial": {r"\beu\b": .5, r"\bminha\b": .8, r"\bmeu\b": .8, r"\bdepoimento": 2.5, r"\bcliente": 1,
                        r"\bhistoria\b": 1.5, r"\bexperiencia\b": 1.2, r"\bcomecei\b": 1.5, r"\bconquist": 1.2,
                        r"\bcase\b": 1.5, r"\bvivi\b": 1, r"\baprendi\b": 1, r"\bfaturei\b": 1.5, r"\bsonho\b": 1},
    "pas": {r"\berro": 1.5, r"\bmulta": 2, r"\bperder\b|\bperdendo\b|\bperde\b": 1.5, r"\bcuidado\b": 1.5,
            r"\bproblema": 1.5, r"\bpare de\b": 1.5, r"\bnunca\b": .6, r"\bnao faca\b": 1.5, r"\bprejuizo": 2,
            r"\bdivida": 1.2, r"\brisco": 1.2, r"\bdor\b": 1, r"\bsolucao": 1.5, r"\bevite\b": 1.5, r"\batencao\b": 1},
    "aida": {r"voce sabia": 2, r"\bdescubra\b": 1.5, r"\bsegredo": 1.5, r"\bdica": 1.2, r"\baprenda\b": 1.5,
             r"link na bio": 2, r"\bcomente\b": 1.5, r"\bsalve\b": 1, r"\bcurso\b": 1.5, r"\bmentoria\b": 1.5,
             r"\binscri": 1.5, r"\bgratuit": 1.5, r"\bwhatsapp\b": 1.2, r"\bchama\b": 1, r"\bquer saber\b": 1.5,
             r"\bgaranta\b": 1.5, r"\baproveite\b": 1.5, r"\bclique\b": 1.2, r"\bsiga\b": 1},
}


def normalizar(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def pontuar(texto: str, f: dict) -> dict[str, float]:
    t = normalizar(texto)
    sc = {k: sum(w * min(len(re.findall(p, t)), 3) for p, w in cues.items()) for k, cues in LEXICO.items()}
    # sinais visuais: fala em primeira pessoa com rosto grande favorece UGC; passos/telas sem rosto favorecem demo
    if f.get("face_detected_ratio", 0) >= .6 and f.get("max_face_area_pct", 0) >= 8:
        sc["ugc_testimonial"] += 1.0
    if f.get("face_detected_ratio", 1) <= .2 and f.get("subtitle_zone_contrast", 0) > .02:
        sc["product_demo_pas"] += .8
    return sc


def classificar_regras(texto: str, f: dict) -> tuple[str, dict[str, float], str]:
    sc = pontuar(texto, f)
    melhor = max(sc, key=sc.get)
    if sc[melhor] < 1.0:  # sem evidência textual (ex.: sem áudio e sem legenda informativa): CTA genérico = AIDA
        return "aida", sc, "baixa"
    ordem = sorted(sc.values(), reverse=True)
    return melhor, sc, "alta" if ordem[0] - ordem[1] >= 1.5 else "media"


def refinar_ollama(modelo: str, texto: str, chaves: list[str]) -> str | None:
    import httpx
    schema = {"type": "object", "properties": {"formato": {"type": "string", "enum": chaves}}, "required": ["formato"]}
    prompt = ("Classifique a estrutura de copy deste Reel de Instagram (PT-BR) em um framework: "
              "bab (antes-depois-ponte), product_demo_pas (demonstração de produto/ferramenta + problema), "
              "ugc_testimonial (depoimento em primeira pessoa/cliente), pas (problema-agitação-solução), "
              "aida (atenção-interesse-desejo-ação, chamada para ação). Texto:\n" + texto[:1800])
    try:
        r = httpx.post("http://localhost:11434/api/generate", timeout=120, json={
            "model": modelo, "prompt": prompt, "stream": False, "format": schema, "options": {"temperature": 0}})
        return json.loads(r.json()["response"])["formato"]
    except Exception as e:  # noqa: BLE001
        log.info("ollama indisponível (%s); mantendo regras", e)
        return None


def resumo(df: pd.DataFrame, col: str = "formato") -> pd.DataFrame:
    rng = np.random.default_rng(42)

    def ic(x: pd.Series) -> str:
        x = x.dropna().to_numpy()
        if len(x) < 3:
            return "n/d"
        m = [np.median(rng.choice(x, len(x))) for _ in range(2000)]
        return f"[{np.percentile(m, 2.5):.2f}; {np.percentile(m, 97.5):.2f}]"

    linhas = []
    for k, g in df.groupby(col):
        s = g["score_relativo"]
        linhas.append({"formato": k, "n": len(g), "pct": round(len(g) / len(df) * 100, 1),
                       "score_mediana": round(s.median(), 2), "score_media": round(s.mean(), 2),
                       "score_iqr": round(s.quantile(.75) - s.quantile(.25), 2), "score_mediana_IC95": ic(s),
                       "taxa_eng_mediana": round(g["taxa_eng"].median(), 4),
                       "duracao_mediana_s": round(g["duration_sec"].median(), 1),
                       "wpm_mediana": round(g.loc[g.has_audio, "words_per_minute"].median(), 1) if g.has_audio.any() else None,
                       "cortes_min_mediana": round(g["cuts_per_minute"].median(), 1)})
    return pd.DataFrame(linhas)


def md(df: pd.DataFrame) -> str:
    cab = "| " + " | ".join(df.columns) + " |\n|" + "---|" * len(df.columns) + "\n"
    return cab + "\n".join("| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |" for r in df.itertuples(index=False))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default="dados/analise_top10")
    ap.add_argument("--base", default="dados/base")
    ap.add_argument("--ollama", default="")
    args = ap.parse_args(argv)
    d, base = Path(args.dir), Path(args.base)
    chaves = [f["key"] for f in load_formats()]
    feats = {x["shortcode"]: x for x in json.loads((d / "multimodal_features.json").read_text())}
    man = {i["shortcode"]: i for i in json.loads((d / "manifesto_midia.json").read_text())["itens"]}
    posts = pd.read_parquet(base / "posts.parquet").set_index("post_id")
    rows = []
    for sc, f in feats.items():
        p = posts.loc[sc]
        texto = f"{p['legenda'] or ''}\n{f['transcript_text']}"
        fmt, scores, conf = classificar_regras(texto, f)
        origem = "regras"
        if args.ollama:
            r = refinar_ollama(args.ollama, texto, chaves)
            if r in chaves:
                fmt, origem = r, f"ollama:{args.ollama}"
        rows.append({**{k: f[k] for k in ("shortcode", "profile", "duration_sec", "has_audio", "words_per_minute",
                                          "cuts_per_minute", "face_detected_ratio")},
                     "formato": fmt, "confianca_regras": conf, "origem": origem, "scores_regras": scores,
                     "is_consensus_80": man[sc]["is_consensus_80"], "score_relativo": man[sc]["score_relativo"],
                     "taxa_eng": man[sc]["taxa_eng"], "tamanho": p["tamanho"], "segmento": p["segmento"]})
    df = pd.DataFrame(rows)
    (d / "format_classification.json").write_text(df.to_json(orient="records", force_ascii=False, indent=1))
    df["conta"] = np.where(df.tamanho == "grande", "grande", "pequena/media")
    df["nicho"] = np.where(df.segmento.str.startswith("contabilidade"), "contabilidade", "demais")
    partes = ["# Desempenho por formato — top 10% de Reels (MPE)\n",
              f"> Gerado por `python -m src.analise.classificar`. Classificação por regras léxicas "
              f"(origem: {', '.join(sorted(df.origem.unique()))}); confiança baixa em "
              f"{(df.confianca_regras == 'baixa').sum()} de {len(df)} Reels. {(~df.has_audio).sum()} Reels não têm áudio.\n",
              f"## Top 10% completo (n = {len(df)})\n", md(resumo(df)),
              f"\n## Núcleo de consenso (n = {int(df.is_consensus_80.sum())})\n", md(resumo(df[df.is_consensus_80])),
              "\n## Estratificado por porte da conta\n"]
    for k, g in df.groupby("conta"):
        partes += [f"### {k} (n = {len(g)})\n", md(resumo(g)), ""]
    partes.append("\n## Estratificado por nicho\n")
    for k, g in df.groupby("nicho"):
        partes += [f"### {k} (n = {len(g)})\n", md(resumo(g)), ""]
    (d / "format_performance_summary.md").write_text("\n".join(partes))
    print(df.formato.value_counts().to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
