"""Padrões de execução dos Shorts virais de YouTube dos nichos de MPE (mesmas features do top 10% do Instagram).

Uso:
    python -m src.analise.youtube_padroes [--selecionados dados/youtube_selecionados.csv] [--modelo small]

Para cada vídeo baixado: transcrição local (faster-whisper), gancho dos 3 s, palavras/min, cortes/min, rosto, movimento,
legenda. Marca `foco_mpe` quando a fala/título trata de VENDER, DIVULGAR ou OPERAR um pequeno negócio (e não de curiosidade
ou conteúdo pessoal). Saídas em dados/analise_youtube/: features.parquet, padroes_por_nicho.csv, RELATORIO.md.
Tudo local; nenhum vídeo sai da máquina.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

# Sinais de que o vídeo fala do dia a dia comercial de um pequeno negócio.
SINAIS_MPE = (
    "vender", "venda", "vendas", "vendo", "vendi", "cliente", "clientes", "preco", "cobrar", "cobro", "lucro", "faturamento",
    "faturar", "divulgar", "divulgacao", "atrair", "agenda", "encomenda", "encomendas", "whatsapp", "negocio", "empreender",
    "empreendedor", "marketing", "estrategia", "abrir", "mei", "seu servico", "meu servico", "orcamento", "fidelizar", "reels",
    "instagram", "marmitaria", "salao", "loja", "oficina", "atendimento", "pedido", "pedidos", "por dia", "por mes", "reais",
)
MIN_SINAIS = 2
MIN_PALAVRAS_FALA = 12   # abaixo disso não há fala a medir (palavras/min, gancho, idioma)


def _norm(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")


def sinais_mpe(titulo: str, transcricao: str) -> list[str]:
    txt = _norm(f"{titulo} {transcricao}")
    return sorted({s for s in SINAIS_MPE if re.search(rf"\b{re.escape(s)}\b", txt)})


def detectar_idioma(wm, video: Path) -> tuple[str, float]:
    """Idioma falado pelos primeiros 30 s do áudio (com VAD). Sem fala detectável devolve ('?', 0)."""
    from src.analise import features as F

    try:
        audio = F.decodificar_audio(video)
        if audio.size < 16000:
            return "?", 0.0
        lang, prob, _ = wm.detect_language(audio[: 30 * 16000], vad_filter=True)
        return lang, round(float(prob), 3)
    except Exception:  # noqa: BLE001 - sem fala/VAD vazio: idioma desconhecido, não derruba o lote
        return "?", 0.0


def analisar(sel: pd.DataFrame, midia: Path, saida: Path, modelo: str) -> pd.DataFrame:
    from faster_whisper import WhisperModel

    from src.analise import features as F
    from src.analise.formato_copy import classificar_formato

    saida.mkdir(parents=True, exist_ok=True)
    wm = WhisperModel(modelo, device="cpu", compute_type="int8")
    linhas = []
    for _, r in sel.iterrows():
        video = midia / f"{r['video_id']}.mp4"
        if not video.exists():
            continue
        item = {"video_path": str(video), "shortcode": r["video_id"], "profile": r["canal"],
                "duration_sec": r["duracao_s"]}
        cache = saida / "cache" / f"{r['video_id']}.json"
        if cache.exists():
            f = json.loads(cache.read_text())
        else:
            try:
                f = F.processar(item, wm, saida)
            except Exception as e:  # noqa: BLE001 - um vídeo ruim não derruba o lote
                print(f"falha em {r['video_id']}: {e}")
                continue
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(f, default=float, ensure_ascii=False))
        if "idioma" not in f:  # o Whisper roda forçado em pt (traduz espanhol): o idioma real vem do áudio
            f["idioma"], f["idioma_prob"] = detectar_idioma(wm, video)
            cache.write_text(json.dumps(f, default=float, ensure_ascii=False))
        # sem fala (música/trilha) o detector devolve ruído: o rótulo honesto é "sem_fala", não "en"
        idioma = f["idioma"] if f.get("word_count", 0) >= MIN_PALAVRAS_FALA else "sem_fala"
        pt = idioma == "pt"
        s = sinais_mpe(r["titulo"], f.get("transcript_text", "") if pt else "")
        formato, _, conf, evid = classificar_formato(r["titulo"], f.get("transcript_text", ""), f)
        linhas.append({"nicho": r["nicho"], "video_id": r["video_id"], "titulo": r["titulo"], "canal": r["canal"],
                       "views": r["views"], "score_viral": r["score_viral"], "url": r["url"],
                       "sinais_mpe": ", ".join(s), "n_sinais_mpe": len(s), "idioma_pt": pt, "idioma_falado": idioma,
                       "foco_mpe": len(s) >= MIN_SINAIS and pt, "formato": formato, "confianca_formato": conf,
                       "evidencias_formato": ", ".join(evid), **f})
        print(f"{r['nicho']:<20} {len(s):>2} sinais  {r['titulo'][:50]}")
    return pd.DataFrame(linhas)


NUM = ["duration_sec", "words_per_minute", "cuts_per_minute", "speech_activity_ratio", "face_detected_ratio",
       "max_face_area_pct", "optical_flow_25d_score", "first_word_timestamp_sec"]


def relatorio(df: pd.DataFrame) -> str:
    def med(d: pd.DataFrame) -> str:
        m = d[[c for c in NUM if c in d]].median().round(2)
        gancho = d["hook_transcript_3s"].fillna("").str.split().str.len().median()
        return "\n".join(f"- {k}: **{v}**" for k, v in m.items()) + f"\n- palavras no gancho (3 s): **{gancho:g}**"

    mpe = df[df["foco_mpe"]]
    out = [f"# Padrões dos Shorts virais de MPE (YouTube)\n",
           f"{len(df)} vídeos analisados; **{len(mpe)} com foco em MPE** (≥ {MIN_SINAIS} sinais comerciais na fala/título, "
           f"idioma falado = pt). Idioma falado (detectado pelo áudio): {df['idioma_falado'].value_counts().to_dict()}.\n",
           "## Medianas — foco em MPE\n", med(mpe) if len(mpe) else "(nenhum)",
           "\n## Medianas — fora de foco (curiosidade/pessoal)\n", med(df[~df["foco_mpe"]]) if (~df["foco_mpe"]).any() else "(nenhum)",
           "\n## Por nicho (foco em MPE)\n", "| nicho | vídeos | mediana views | duração | palavras/min | cortes/min |", "|---|---|---|---|---|---|"]
    for n, g in mpe.groupby("nicho"):
        out.append(f"| {n} | {len(g)} | {int(g['views'].median()):,} | {g['duration_sec'].median():.0f}s | "
                   f"{g['words_per_minute'].median():.0f} | {g['cuts_per_minute'].median():.1f} |")
    out += ["\n## Por formato da pesquisa (foco em MPE)\n",
            "| formato | vídeos | mediana views | duração | palavras/min | cortes/min | rosto | gancho (palavras) |",
            "|---|---|---|---|---|---|---|---|"]
    claros = mpe[mpe["confianca_formato"] != "baixa"]
    for n, g in claros.groupby("formato"):
        gk = g["hook_transcript_3s"].fillna("").str.split().str.len().median()
        out.append(f"| {n} | {len(g)} | {int(g['views'].median()):,} | {g['duration_sec'].median():.0f}s | "
                   f"{g['words_per_minute'].median():.0f} | {g['cuts_per_minute'].median():.1f} | "
                   f"{g['face_detected_ratio'].median():.0%} | {gk:g} |")
    out.append(f"\n{len(mpe) - len(claros)} dos {len(mpe)} vídeos com foco em MPE não mostram um movimento retórico claro "
               f"(confiança baixa) e ficam fora da tabela: são explicações diretas, sem estrutura de copy identificável.")
    out.append("\n## Ganchos (3 primeiros segundos) dos vídeos com foco em MPE\n")
    for _, r in mpe.sort_values("score_viral", ascending=False).iterrows():
        out.append(f"- **{r['nicho']}** ({int(r['views']):,} views): “{(r['hook_transcript_3s'] or '').strip()}” — {r['url']}")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selecionados", nargs="+", default=["dados/youtube_selecionados.csv", "dados/youtube_selecionados_comercial.csv"])
    ap.add_argument("--midia", default="dados/midia/youtube")
    ap.add_argument("--saida", default="dados/analise_youtube")
    ap.add_argument("--modelo", default="small")
    args = ap.parse_args(argv)

    saida = Path(args.saida)
    df = analisar(pd.concat([pd.read_csv(c) for c in args.selecionados if Path(c).exists()]).drop_duplicates("video_id"), Path(args.midia), saida, args.modelo)
    if df.empty:
        print("nada analisado")
        return 1
    df.drop(columns=[c for c in df if df[c].map(lambda v: isinstance(v, (list, dict))).any()]).to_parquet(
        saida / "features.parquet", index=False)
    (saida / "RELATORIO.md").write_text(relatorio(df), encoding="utf-8")
    print(f"\n{len(df)} analisados, {int(df['foco_mpe'].sum())} com foco em MPE → {saida / 'RELATORIO.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
