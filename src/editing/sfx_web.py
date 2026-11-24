"""Busca e baixa efeitos sonoros REAIS (CC0) da web para a biblioteca local, a pedido do Claude durante a edição.

Fonte: OpenGameArt.org, filtrando só áudio com licença CC0 (domínio público, sem atribuição). Regras de boa conduta:
respeita o robots.txt, se identifica no User-Agent, espera entre requisições e baixa poucos arquivos por vez.
Cada arquivo gravado em assets/audio_cc0/sfx/ ganha um .json com origem, licença, autor e página (proveniência).
Depois de baixado, o som fica na biblioteca: renders seguintes não usam rede (sfx.resolver lê a biblioteca primeiro).
NÃO contorna nada: sites que não permitem acesso automático (ex.: Kenney, robots.txt) ficam de fora.

    python -m src.editing.sfx_web buscar "whoosh"                 # lista candidatos CC0, sem baixar
    python -m src.editing.sfx_web baixar whoosh "air whoosh" -n 2 # baixa para a biblioteca (nome = efeito do projeto)
    python -m src.editing.sfx_web garantir whoosh pop impact -n 2 # garante N variantes reais de cada efeito (usa as consultas padrão)
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path

from src.editing import sfx

BASE = "https://opengameart.org"
UA = "ImpulsoReels-sfx/1.0 (edicao de video local; uso pessoal; respeita robots.txt)"
PAUSA_S = 1.2
MAX_BYTES = 3_000_000
MAX_DURACAO_S = 8.0
EXT_OK = (".wav", ".ogg", ".mp3", ".flac")
_ULTIMA = [0.0]
_ROBOTS: list = []


def _permitido(url: str) -> bool:
    if not _ROBOTS:
        rp = urllib.robotparser.RobotFileParser(BASE + "/robots.txt")
        try:
            rp.read()
        except OSError:
            rp = None
        _ROBOTS.append(rp)
    rp = _ROBOTS[0]
    return True if rp is None else rp.can_fetch(UA, url)


def _get(url: str, limite: int = 2_000_000) -> bytes:
    if not _permitido(url):
        raise PermissionError(f"robots.txt não permite buscar {url}")
    espera = PAUSA_S - (time.time() - _ULTIMA[0])
    if espera > 0:
        time.sleep(espera)
    _ULTIMA[0] = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        dados = r.read(limite + 1)
    if len(dados) > limite:
        raise ValueError("arquivo grande demais")
    return dados


def buscar(consulta: str, n: int = 8) -> list[dict]:
    """Páginas CC0 de áudio que combinam com a consulta (título, licença e arquivos)."""
    q = urllib.parse.urlencode([("keys", consulta), ("field_art_type_tid[]", 13), ("field_art_licenses_tid[]", 4)])
    try:
        html = _get(f"{BASE}/art-search-advanced?{q}").decode("utf-8", "ignore")
    except (OSError, PermissionError, ValueError) as exc:
        raise SystemExit(f"não consegui buscar no OpenGameArt ({exc}). Siga com a biblioteca local/procedural.") from exc
    slugs = list(dict.fromkeys(re.findall(r'href="(/content/[a-z0-9\-]+)"', html)))
    slugs = [s for s in slugs if s not in {"/content/faq"}][: n + 2]
    achados = []
    for s in slugs:
        try:
            pag = _get(BASE + s).decode("utf-8", "ignore")
        except (OSError, PermissionError, ValueError):
            continue
        licencas = re.findall(r"<div class='license-name'>([^<]+)</div>", pag)
        if not licencas or {x.strip().upper() for x in licencas} != {"CC0"}:
            continue  # só CC0 puro
        titulo = (re.search(r"<title>(.*?)\s*\|", pag) or [None, s])[1]
        autor = (re.search(r'href="/users/[^"]+"[^>]*>([^<]+)</a>', pag) or [None, ""])[1]
        arqs = [u for u in dict.fromkeys(re.findall(r'href="(https?://[^"]*/sites/default/files/[^"]+)"', pag))
                if u.lower().split("?")[0].endswith(EXT_OK)]
        if arqs:
            achados.append({"pagina": BASE + s, "slug": s.rsplit("/", 1)[-1], "titulo": titulo.strip(), "autor": autor.strip(),
                            "arquivos": arqs[:6]})
        if len(achados) >= n:
            break
    return achados


def baixar(nome: str, consulta: str, quantos: int = 1) -> list[Path]:
    if nome not in sfx.NOMES:
        raise SystemExit(f"efeito desconhecido '{nome}'. Use um de: {', '.join(sfx.NOMES)}")
    sfx.BIBLIOTECA.mkdir(parents=True, exist_ok=True)
    gravados: list[Path] = []
    ja = sfx._ids_da_biblioteca()
    for cand in buscar(consulta, n=10):
        for url in cand["arquivos"]:
            if len(gravados) >= quantos:
                return gravados
            fid = f"oga:{cand['slug']}:{Path(urllib.parse.urlparse(url).path).name}"
            if fid in ja or not sfx._titulo_ok(cand["titulo"]):
                continue
            ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
            destino = sfx.BIBLIOTECA / f"{nome}_{len(sfx.arquivos_da_biblioteca(nome)) + 1:02d}{ext}"
            try:
                destino.write_bytes(_get(url, MAX_BYTES))
                x = sfx._decodificar(destino)
                motivo = "longo demais (não é efeito curto)" if x.size > MAX_DURACAO_S * sfx.SR else sfx._reprova(x)
            except (OSError, PermissionError, ValueError, RuntimeError) as exc:
                motivo = f"falha ({exc})"
            if motivo:
                print(f"  descartado {Path(url).name}: {motivo}")
                destino.unlink(missing_ok=True)
                continue
            destino.with_suffix(destino.suffix + ".json").write_text(json.dumps({
                "license_key": "opengameart-cc0", "licenca": "CC0", "origem": "opengameart.org", "titulo": cand["titulo"],
                "autor": cand["autor"], "pagina": cand["pagina"], "url": url, "id": fid, "consulta": consulta,
            }, ensure_ascii=False, indent=1), encoding="utf-8")
            gravados.append(destino)
            ja.add(fid)
    return gravados


def garantir(nomes: list[str], por_efeito: int = 2) -> dict[str, int]:
    """Para cada efeito, completa a biblioteca com variantes reais (consultas padrão de sfx.CATEGORIAS)."""
    res = {}
    for nome in nomes:
        novos = 0
        for consulta in sfx.CATEGORIAS.get(nome, [nome]):
            falta = por_efeito - len(sfx.arquivos_da_biblioteca(nome))
            if falta <= 0:
                break
            try:
                novos += len(baixar(nome, consulta, falta))
            except SystemExit as exc:
                print(f"  {nome} '{consulta}': {exc}")
        res[nome] = len(sfx.arquivos_da_biblioteca(nome))
        print(f"{nome}: {res[nome]} variante(s) real(is) na biblioteca (+{novos})")
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("buscar")
    b.add_argument("consulta")
    d = sub.add_parser("baixar")
    d.add_argument("nome")
    d.add_argument("consulta")
    d.add_argument("-n", type=int, default=1)
    g = sub.add_parser("garantir")
    g.add_argument("nomes", nargs="+")
    g.add_argument("-n", type=int, default=2)
    a = ap.parse_args(argv)
    if a.cmd == "buscar":
        for c in buscar(a.consulta):
            print(f"CC0  {c['titulo'][:50]:50} {len(c['arquivos'])} arq  {c['pagina']}")
    elif a.cmd == "baixar":
        for p in baixar(a.nome, a.consulta, a.n):
            print("baixado:", p)
    else:
        garantir(a.nomes, a.n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
