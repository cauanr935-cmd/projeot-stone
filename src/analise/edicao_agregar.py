"""Agrega os padrões de edição (top 10% x controle) e gera o playbook: JSON, config/playbook_viral.yaml e docs/KNOWHOW_VIRAL.md."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.analise.edicao_padroes import BASE, CTAS, GANCHOS, SAIDA

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
MOLDES_GANCHO = {  # estrutura (não frase copiada) de cada tipo de gancho, para o roteirista adaptar ao negócio
    "pergunta": "Pergunta direta sobre a dor ou o desejo do cliente: «Você ainda [faz X] sem saber [consequência]?»",
    "numero_valor": "Número concreto no 1º segundo: «R$ [valor] / [N]% / [N] erros que [consequência]»",
    "erro_dor": "Erro ou perda que o público comete: «O erro que faz [público] perder [coisa] todo mês»",
    "promessa_como": "Promessa + método: «Como [resultado] em [prazo/passos], sem [obstáculo]»",
    "historia_prova": "Prova em 1ª pessoa: «Eu [estava mal] e [resultado] em [tempo]; veja o que mudou»",
    "segmentacao": "Chama o público pelo nome: «Se você é [perfil] e [situação], pare e veja isso»",
    "urgencia_novidade": "Novidade/urgência: «Mudou [coisa] e quase ninguém [agiu]»",
    "imperativo": "Comando curto: «Pare. [Instrução de 1 linha]»",
}


def _q(xs, p):
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and np.isnan(x))]
    return round(float(np.percentile(xs, p)), 2) if xs else None


def _resumo(xs):
    return {"p25": _q(xs, 25), "mediana": _q(xs, 50), "p75": _q(xs, 75)}


def _carregar() -> pd.DataFrame:
    linhas = [json.loads(f.read_text()) for f in SAIDA.glob("*.json") if f.name != "agregado.json"]
    df = pd.DataFrame(linhas)
    rank = pd.read_parquet(BASE / "base" / "ranking.parquet")[["post_id", "alto_desempenho", "score_relativo"]]
    posts = pd.read_parquet(BASE / "base" / "posts.parquet")[["post_id", "duracao_s", "legenda", "hashtags", "segmento", "username"]]
    df = df.merge(rank, left_on="shortcode", right_on="post_id").merge(posts, on="post_id")
    df["grupo"] = np.where(df["alto_desempenho"], "top", "controle")
    return df[df["duracao_analisada_s"] >= 5]


def _planos(df: pd.DataFrame) -> dict:
    out = {}
    for g, d in df.groupby("grupo"):
        n_pl = (d.planos_push_in + d.planos_pull_out + d.planos_estaticos).replace(0, np.nan)
        out[g] = {
            "n_videos": int(len(d)),
            "cortes_por_min": _resumo(d.cortes_por_min), "duracao_plano_s": _resumo(d.duracao_plano_mediana_s),
            "primeiro_corte_s": _resumo(d.primeiro_corte_s), "pct_com_corte_nos_3s": round(float((d.cortes_nos_3s > 0).mean()) * 100, 1),
            "pct_planos_push_in": round(float((d.planos_push_in / n_pl).mean(skipna=True)) * 100, 1),
            "pct_planos_pull_out": round(float((d.planos_pull_out / n_pl).mean(skipna=True)) * 100, 1),
            "punch_in_por_min": _resumo(d.punch_in_por_min), "movimento_3s": _resumo(d.movimento_3s),
            "duracao_s": _resumo(d.duracao_s),
            "perfil_cortes_decis_pct": [round(float(x), 1) for x in 100 * np.mean(
                [np.array(p) / max(sum(p), 1) for p in d.perfil_cortes_decis if sum(p) > 0], axis=0)],
        }
    return out


def _tabela_tipos(df: pd.DataFrame, col: str, chaves) -> dict:
    d = df[df.gancho_palavras > 0] if col == "gancho_tipos" else df[df.wpm.fillna(0) > 0]
    res = {}
    for k in chaves:
        s = {g: float(np.mean([k in t for t in x[col]])) * 100 if len(x) else 0.0 for g, x in d.groupby("grupo")}
        top, ctl = s.get("top", 0), s.get("controle", 0)
        res[k] = {"pct_top": round(top, 1), "pct_controle": round(ctl, 1), "lift": round(top / ctl, 2) if ctl else None}
    return res


def _hashtags_legenda(df: pd.DataFrame) -> dict:
    t = df[df.grupo == "top"]
    def contar(d, minimo):  # só hashtags usadas por >= `minimo` perfis distintos (descarta marca própria)
        por_perfil: dict[str, set] = {}
        for u, hs in zip(d.username, d.hashtags):
            for h in (hs if hs is not None else []):
                por_perfil.setdefault(h.lower(), set()).add(u)
        c = Counter({h: len(us) for h, us in por_perfil.items() if len(us) >= minimo})
        return [h for h, _ in c.most_common(15)]
    todos = contar(t, 3)
    por_seg = {str(seg): contar(d, 2) for seg, d in t.groupby("segmento")}
    leg = t.legenda.fillna("")
    primeira = leg.map(lambda s: s.strip().split("\n")[0] if s.strip() else "")
    return {
        "n_hashtags": _resumo([len(h) if h is not None else 0 for h in t.hashtags]),
        "caracteres_legenda": _resumo([len(s) for s in leg]),
        "pct_com_emoji": round(float(np.mean([bool(EMOJI.search(s)) for s in leg])) * 100, 1),
        "pct_primeira_linha_pergunta": round(float(np.mean(["?" in s for s in primeira])) * 100, 1),
        "pct_cta_na_legenda": round(float(np.mean([bool(re.search("|".join(CTAS[k] for k in CTAS), s.lower())) for s in leg])) * 100, 1),
        "palavras_primeira_linha": _resumo([len(s.split()) for s in primeira]),
        "hashtags_top": todos,
        "hashtags_por_segmento": por_seg,
    }


def agregar() -> dict:
    df = _carregar()
    ag = {"n_total": int(len(df)), "planos": _planos(df),
          "ganchos": _tabela_tipos(df, "gancho_tipos", GANCHOS), "ctas": _tabela_tipos(df, "cta_tipos", CTAS),
          "primeira_palavra_ate_0_5s_pct": {g: round(float((d.primeira_palavra_s.fillna(9) <= .5).mean()) * 100, 1) for g, d in df.groupby("grupo")},
          "legenda": _hashtags_legenda(df)}
    SAIDA.joinpath("agregado.json").write_text(json.dumps(ag, ensure_ascii=False, indent=1))
    _playbook(ag)
    _doc(ag)
    return ag


def _playbook(ag: dict) -> None:
    pt, pc = ag["planos"]["top"], ag["planos"]["controle"]
    ordem = sorted(((k, v) for k, v in ag["ganchos"].items() if v["pct_top"] >= 3), key=lambda kv: -kv[1]["pct_top"])
    cta = sorted(ag["ctas"].items(), key=lambda kv: -kv[1]["pct_top"])
    pb = {
        "fonte": f"{ag['n_total']} Reels da base (top 10% x controle); gerado por src/analise/edicao_padroes.py",
        "ritmo": {"cortes_por_min": pt["cortes_por_min"], "duracao_plano_s": pt["duracao_plano_s"],
                  "primeiro_corte_s": pt["primeiro_corte_s"], "pct_com_corte_nos_3s": pt["pct_com_corte_nos_3s"]},
        "camera": {"pct_planos_push_in": pt["pct_planos_push_in"], "pct_planos_pull_out": pt["pct_planos_pull_out"],
                   "punch_in_por_min": pt["punch_in_por_min"]},
        "ganchos_por_frequencia": [{"tipo": k, "pct_top": v["pct_top"], "lift_vs_controle": v["lift"], "molde": MOLDES_GANCHO[k]} for k, v in ordem],
        "gancho": {"primeira_palavra_ate_0_5s_pct_top": ag["primeira_palavra_ate_0_5s_pct"].get("top")},
        "ctas_por_frequencia": [{"tipo": k, "pct_top": v["pct_top"], "lift_vs_controle": v["lift"]} for k, v in cta],
        "legenda": {k: ag["legenda"][k] for k in ("n_hashtags", "caracteres_legenda", "pct_com_emoji",
                                                   "pct_primeira_linha_pergunta", "pct_cta_na_legenda", "palavras_primeira_linha")},
        "hashtags_top": ag["legenda"]["hashtags_top"], "hashtags_por_segmento": ag["legenda"]["hashtags_por_segmento"],
    }
    Path("config/playbook_viral.yaml").write_text(yaml.safe_dump(pb, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")


def _doc(ag: dict) -> None:
    pt, pc = ag["planos"]["top"], ag["planos"]["controle"]
    L = ["# Know-how de edição viral (extraído da base)", "",
         f"Gerado por `python -m src.analise.edicao_padroes extrair && ... agregar`. Base: {ag['n_total']} Reels "
         f"({pt['n_videos']} do top 10% x {pc['n_videos']} de controle). Análise automática de vídeo (OpenCV/ffmpeg); descreve padrões, não prova causa.", "",
         "## Ritmo e câmera", "", "| métrica | top 10% (p25 / mediana / p75) | controle (mediana) |", "|---|---|---|"]
    f3 = lambda r: f"{r['p25']} / **{r['mediana']}** / {r['p75']}"
    for nome, k in (("cortes por minuto", "cortes_por_min"), ("duração do plano (s)", "duracao_plano_s"), ("1º corte (s)", "primeiro_corte_s"),
                    ("punch-in por minuto", "punch_in_por_min"), ("movimento nos 3 s iniciais", "movimento_3s"), ("duração do Reel (s)", "duracao_s")):
        L.append(f"| {nome} | {f3(pt[k])} | {pc[k]['mediana']} |")
    L += [f"| Reels com corte nos 3 s | {pt['pct_com_corte_nos_3s']}% | {pc['pct_com_corte_nos_3s']}% |",
          f"| planos com push-in (aproximação) | {pt['pct_planos_push_in']}% | {pc['pct_planos_push_in']}% |",
          f"| planos com pull-out (afastamento) | {pt['pct_planos_pull_out']}% | {pc['pct_planos_pull_out']}% |", "",
          "### Onde caem os cortes (% por décimo da duração, top 10%)", "", "`" + " | ".join(f"{x}" for x in pt["perfil_cortes_decis_pct"]) + "`", "",
          "## Ganchos (primeiros 3 s da fala)", "", f"Reels do top cuja 1ª palavra começa em até 0,5 s: **{ag['primeira_palavra_ate_0_5s_pct_top'] if 'primeira_palavra_ate_0_5s_pct_top' in ag else ag['primeira_palavra_ate_0_5s_pct'].get('top')}%**.", "",
          "| tipo | % no top | % controle | lift | molde |", "|---|---|---|---|---|"]
    for k, v in sorted(ag["ganchos"].items(), key=lambda kv: -kv[1]["pct_top"]):
        L.append(f"| {k} | {v['pct_top']} | {v['pct_controle']} | {v['lift']} | {MOLDES_GANCHO[k]} |")
    L += ["", "## Chamadas para ação (último ~18% da fala)", "", "| tipo | % top | % controle | lift |", "|---|---|---|---|"]
    for k, v in sorted(ag["ctas"].items(), key=lambda kv: -kv[1]["pct_top"]):
        L.append(f"| {k} | {v['pct_top']} | {v['pct_controle']} | {v['lift']} |")
    lg = ag["legenda"]
    L += ["", "## Legenda e hashtags (top 10%)", "",
          f"- Hashtags por post: {f3(lg['n_hashtags'])}; caracteres da legenda: {f3(lg['caracteres_legenda'])}.",
          f"- Com emoji: {lg['pct_com_emoji']}%; 1ª linha é pergunta: {lg['pct_primeira_linha_pergunta']}%; tem CTA: {lg['pct_cta_na_legenda']}%.",
          f"- Hashtags mais frequentes: {', '.join('#' + h for h in lg['hashtags_top'][:15])}.", "",
          "Hashtags por segmento: ver `config/playbook_viral.yaml`.", "",
          "## Como o Claude usa isto", "",
          "`src/criativos/sessao_claude.py` injeta `config/playbook_viral.yaml` no prompt da edição; `src/analise/legenda_hashtags.py` gera `legenda.txt`."]
    Path("docs/KNOWHOW_VIRAL.md").write_text("\n".join(L) + "\n", encoding="utf-8")
