"""Busca e baixa FOTOS de apoio (b-roll) da web para o Reel, a pedido do Claude durante a edição.

Cascata (usa a primeira fonte que responder; ausência de chave nunca é erro):
  1. Pixabay  (API oficial; PIXABAY_API_KEY, grátis)  — Pixabay Content License: uso comercial, sem atribuição
  2. Pexels   (API oficial; PEXELS_API_KEY, grátis)   — Pexels License: uso comercial, sem atribuição
  3. Wikimedia Commons (API aberta, sem chave)        — só CC0 / domínio público
Não raspa o HTML do Pixabay/Pexels: os termos deles pedem a API (e o site bloqueia robôs).
As fotos vão para workspace/imagens_web/<consulta>/ com <arquivo>.json (origem, autor, licença, página); o MCP enxerga essa pasta.

    python -m src.editing.imagens_web buscar "brigadeiro" --en "chocolate truffle"
    python -m src.editing.imagens_web baixar "brownie de chocolate" --en "chocolate brownie" -n 3
`--en` é a mesma busca em inglês (Pexels e Commons funcionam melhor assim). Pixabay usa o texto em português.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from src.core.config import ROOT

SAIDA = ROOT / "workspace" / "imagens_web"
UA = "ImpulsoReels-imagens/1.0 (edicao de video local; uso pessoal)"
MIN_LARGURA = 800
MAX_BYTES = 12_000_000
_ULTIMA = [0.0]


def _chave(nome: str) -> str:
    if not os.getenv(nome):
        try:
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env")
        except ImportError:
            pass
    return os.getenv(nome, "").strip()


def _get(url: str, headers: dict | None = None, limite: int = MAX_BYTES) -> bytes:
    espera = 0.8 - (time.time() - _ULTIMA[0])
    if espera > 0:
        time.sleep(espera)
    _ULTIMA[0] = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=40) as r:
        dados = r.read(limite + 1)
    if len(dados) > limite:
        raise ValueError("arquivo grande demais")
    return dados


def _pixabay(q: str, n: int) -> list[dict]:
    k = _chave("PIXABAY_API_KEY")
    if not k:
        return []
    p = urllib.parse.urlencode({"key": k, "q": q[:100], "lang": "pt", "image_type": "photo", "orientation": "vertical",
                                "safesearch": "true", "min_width": 720, "per_page": max(n, 3), "order": "popular"})
    js = json.loads(_get("https://pixabay.com/api/?" + p))
    return [{"provedor": "pixabay", "id": str(h["id"]), "url": h.get("largeImageURL") or h["webformatURL"],
             "pagina": h["pageURL"], "autor": h.get("user", ""), "licenca": "Pixabay Content License",
             "license_key": "pixabay-content", "largura": h.get("imageWidth")} for h in js.get("hits", [])]


def _pexels(q: str, n: int) -> list[dict]:
    k = _chave("PEXELS_API_KEY")
    if not k:
        return []
    p = urllib.parse.urlencode({"query": q[:100], "orientation": "portrait", "per_page": max(n, 3)})
    js = json.loads(_get("https://api.pexels.com/v1/search?" + p, {"Authorization": k}))
    return [{"provedor": "pexels", "id": str(h["id"]), "url": h["src"].get("large2x") or h["src"]["large"],
             "pagina": h["url"], "autor": h.get("photographer", ""), "licenca": "Pexels License",
             "license_key": "pexels-license", "largura": h.get("width")} for h in js.get("photos", [])]


_LIVRE = re.compile(r"^(cc0|cc[- ]?zero|public domain|pd\b|pdm)", re.I)


def _commons(q: str, n: int) -> list[dict]:
    p = urllib.parse.urlencode({"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
                                "gsrsearch": f"{q} filetype:bitmap", "gsrlimit": max(n * 3, 8), "prop": "imageinfo",
                                "iiprop": "url|extmetadata|size", "iiurlwidth": 1600})
    pgs = json.loads(_get("https://commons.wikimedia.org/w/api.php?" + p)).get("query", {}).get("pages", {})
    out = []
    for pg in sorted(pgs.values(), key=lambda x: x.get("index", 0)):
        ii = (pg.get("imageinfo") or [{}])[0]
        lic = (ii.get("extmetadata", {}).get("LicenseShortName", {}) or {}).get("value", "")
        if not _LIVRE.match(lic) or (ii.get("width") or 0) < MIN_LARGURA:
            continue
        autor = re.sub(r"<[^>]+>", "", (ii["extmetadata"].get("Artist", {}) or {}).get("value", ""))[:80]
        out.append({"provedor": "wikimedia", "id": str(pg["pageid"]), "url": ii.get("thumburl") or ii["url"],
                    "pagina": ii.get("descriptionurl", ""), "autor": autor, "licenca": lic,
                    "license_key": "local-cc0", "largura": ii.get("thumbwidth") or ii.get("width")})
    return out


def buscar(consulta: str, en: str = "", n: int = 6) -> list[dict]:
    """Candidatos na ordem da cascata. Cada fonte que falha é pulada (sem chave, sem rede, limite)."""
    achados: list[dict] = []
    for fonte, q in ((_pixabay, consulta), (_pexels, en or consulta), (_commons, en or consulta)):
        try:
            achados += fonte(q, n)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            print(f"  [{fonte.__name__[1:]}] indisponível: {exc}")
        if len(achados) >= n:
            break
    return achados[:n]


def baixar(consulta: str, en: str = "", quantos: int = 3) -> list[Path]:
    from PIL import Image
    pasta = SAIDA / (re.sub(r"[^a-z0-9]+", "_", (en or consulta).lower()).strip("_")[:40] or "busca")
    pasta.mkdir(parents=True, exist_ok=True)
    gravadas: list[Path] = []
    for c in buscar(consulta, en, n=quantos * 3):
        if len(gravadas) >= quantos:
            break
        dest = pasta / f"{c['provedor']}_{c['id']}.jpg"
        if dest.exists():
            gravadas.append(dest)
            continue
        try:
            dados = _get(c["url"])
            im = Image.open(io.BytesIO(dados))
            im.load()
            if im.width < MIN_LARGURA:
                print(f"  descartada {c['id']}: pequena ({im.width}px)")
                continue
            im.convert("RGB").save(dest, quality=92)
        except (OSError, ValueError) as exc:
            print(f"  descartada {c['id']}: {exc}")
            continue
        dest.with_suffix(".jpg.json").write_text(json.dumps(
            {k: c[k] for k in ("provedor", "id", "pagina", "autor", "licenca", "license_key", "url")} | {"consulta": consulta},
            ensure_ascii=False, indent=1), encoding="utf-8")
        gravadas.append(dest)
    return gravadas


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nome in ("buscar", "baixar"):
        s = sub.add_parser(nome)
        s.add_argument("consulta")
        s.add_argument("--en", default="")
        s.add_argument("-n", type=int, default=3 if nome == "baixar" else 6)
    a = ap.parse_args(argv)
    if a.cmd == "buscar":
        for c in buscar(a.consulta, a.en, a.n):
            print(f"{c['provedor']:9} {c['licenca'][:24]:24} {c['largura']}px  {c['autor'][:24]:24} {c['pagina']}")
    else:
        gr = baixar(a.consulta, a.en, a.n)
        for p in gr:
            print("baixada:", p)
        if not gr:
            print("nenhuma foto baixada (sem chave de API e sem resultado livre). Siga com cartões visuais.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
