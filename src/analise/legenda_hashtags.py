"""Legenda + hashtags do Reel, calibradas pelo playbook da base (config/playbook_viral.yaml).

Uso: python -m src.analise.legenda_hashtags --negocio "Doce Sonho" --ramo confeitaria --oferta "bolo de pote por R$ 12"
        [--gancho "..."] [--cta "Peça no Direct"] [--cidade "Santos"] [--saida pasta/legenda.txt]
Estrutura: 1ª linha = gancho (curto, em ~10 palavras); corpo = benefício + oferta; CTA; hashtags = nicho do ramo +
amplas de MPE que o top 10% da base mais usa (usadas por vários perfis, nunca de marca própria).
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

import yaml

PLAYBOOK = Path("config/playbook_viral.yaml")
AMPLAS_PADRAO = ["empreendedorismo", "pequenosnegocios", "mei", "marketingdigital", "vendas"]
CTA_TEXTO = {"comente": "Comenta «QUERO» que eu te respondo 👇", "siga": "Segue o perfil pra ver mais dicas assim ➕",
             "link_bio": "Link na bio 🔗", "direct_whats": "Chama no direct ou no WhatsApp 📲",
             "salve_compartilhe": "Salva e manda pra quem precisa 💾"}


def _slug(txt: str) -> str:
    t = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", t)


def _playbook() -> dict:
    try:
        return yaml.safe_load(PLAYBOOK.read_text(encoding="utf-8")) or {}
    except OSError:
        return {}


def gerar(negocio: str, ramo: str, oferta: str, gancho: str | None = None, cta: str | None = None, cidade: str | None = None) -> dict:
    pb = _playbook()
    qtd = int(((pb.get("legenda") or {}).get("n_hashtags") or {}).get("mediana") or 6)
    qtd = max(5, min(qtd, 10))
    linha1 = (gancho or f"{oferta.strip().capitalize()}? Olha isso").strip()
    linha1 = " ".join(linha1.split()[:12])
    corpo = f"{negocio} tem {oferta.strip()}. Feito com capricho pra você."
    cta_tipo = ((pb.get("ctas_por_frequencia") or [{}])[0]).get("tipo", "direct_whats")
    chamada = cta.strip() if cta else CTA_TEXTO.get(cta_tipo, CTA_TEXTO["direct_whats"])
    nicho = [_slug(ramo), _slug(negocio), _slug(oferta.split(" por ")[0])[:30]]
    if cidade:
        nicho += [_slug(ramo) + _slug(cidade), _slug(cidade)]
    amplas = [h for h in (pb.get("hashtags_top") or AMPLAS_PADRAO) if h in AMPLAS_PADRAO + (pb.get("hashtags_top") or [])][:6]
    tags: list[str] = []
    for h in [*nicho[:3], *nicho[3:], *amplas, *AMPLAS_PADRAO]:  # local antes das amplas
        if h and h not in tags and len(h) > 2:
            tags.append(h)
    tags = tags[:qtd]
    hashtags = " ".join("#" + h for h in tags)
    texto = f"{linha1}\n\n{corpo}\n\n{chamada}\n\n{hashtags}"
    return {"legenda": texto, "hashtags": tags, "gancho_linha": linha1}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--negocio", required=True)
    ap.add_argument("--ramo", required=True)
    ap.add_argument("--oferta", required=True)
    ap.add_argument("--gancho")
    ap.add_argument("--cta")
    ap.add_argument("--cidade")
    ap.add_argument("--saida")
    a = ap.parse_args(argv)
    r = gerar(a.negocio, a.ramo, a.oferta, a.gancho, a.cta, a.cidade)
    if a.saida:
        Path(a.saida).write_text(r["legenda"] + "\n", encoding="utf-8")
    print(r["legenda"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
