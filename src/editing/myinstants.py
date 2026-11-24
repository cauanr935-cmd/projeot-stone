"""Base de efeitos sonoros do MyInstants (sons de meme/reação), baixados sob demanda para uso local.

ATENÇÃO (direitos): o MyInstants é feito de uploads de usuários, sem licença declarada; muitos sons são trechos de TV, filmes,
jogos e músicas. Por isso a licença fica como `myinstants` = commercial_ok: false em config/licenses.yaml: o pipeline de
motion em modo comercial recusa esses sons, e a edição pelo Claude só os usa como tempero opcional, avisando no resumo que o
Instagram pode bloquear o áudio. Quem decide publicar é o dono do conteúdo.
Boa conduta: respeita o robots.txt (que permite /media/ e as buscas), se identifica, espera entre requisições, baixa só o que
vai usar (não espelha o site). Cada arquivo ganha .json com título, página e aviso; assets/audio_myinstants/catalogo.json
lista tudo, para o Claude procurar por nome sem rede.

    python -m src.editing.myinstants buscar "risada"            # lista resultados do site, sem baixar
    python -m src.editing.myinstants baixar "whoosh" -n 3       # baixa os melhores para a base
    python -m src.editing.myinstants populares -n 10            # baixa os mais bombados no Brasil
    python -m src.editing.myinstants listar [texto]             # procura na base local
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from html import unescape
from pathlib import Path

from src.core.config import ROOT

BASE = "https://www.myinstants.com"
UA = "ImpulsoReels-sfx/1.0 (edicao de video local; uso pessoal; respeita robots.txt)"
PASTA = ROOT / "assets" / "audio_myinstants"
MAX_BYTES = 1_500_000
MAX_DURACAO_S = 10.0
_ULTIMA = [0.0]
_ROBOTS: list = []


def _permitido(url: str) -> bool:
    if not _ROBOTS:
        rp = urllib.robotparser.RobotFileParser()
        try:  # baixa com o nosso User-Agent (o padrão do urllib é recusado pelo site e viraria "tudo proibido")
            req = urllib.request.Request(BASE + "/robots.txt", headers={"User-Agent": UA})
            rp.parse(urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore").splitlines())
        except OSError:
            rp = None
        _ROBOTS.append(rp)
    return True if _ROBOTS[0] is None else _ROBOTS[0].can_fetch(UA, url)


def _get(url: str, limite: int = 2_000_000) -> bytes:
    if not _permitido(url):
        raise PermissionError(f"robots.txt não permite {url}")
    espera = 1.0 - (time.time() - _ULTIMA[0])
    if espera > 0:
        time.sleep(espera)
    _ULTIMA[0] = time.time()
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40) as r:
        dados = r.read(limite + 1)
    if len(dados) > limite:
        raise ValueError("arquivo grande demais")
    return dados


def _parse(html: str) -> list[dict]:
    itens = []
    for bloco in html.split('<div class="instant">')[1:]:
        m = re.search(r"play\('(/media/sounds/[^']+)'", bloco)
        t = re.search(r'<a href="(/pt/instant/[^"]+/)"[^>]*class="instant-link[^"]*">([^<]+)</a>', bloco)
        if m and t:
            itens.append({"arquivo": m.group(1), "pagina": BASE + t.group(1), "titulo": unescape(t.group(2)).strip(),
                          "slug": t.group(1).strip("/").rsplit("/", 1)[-1]})
    return itens


def buscar(consulta: str, n: int = 12) -> list[dict]:
    try:
        html = _get(f"{BASE}/pt/search/?" + urllib.parse.urlencode({"name": consulta})).decode("utf-8", "ignore")
    except (OSError, PermissionError, ValueError) as exc:
        raise SystemExit(f"MyInstants indisponível ({exc}). Siga com os efeitos CC0 da biblioteca.") from exc
    return _parse(html)[:n]


def populares(n: int = 10) -> list[dict]:
    try:
        html = _get(f"{BASE}/pt/index/br/").decode("utf-8", "ignore")
    except (OSError, PermissionError, ValueError) as exc:
        raise SystemExit(f"MyInstants indisponível ({exc}).") from exc
    return _parse(html)[:n]


def _catalogo() -> dict:
    f = PASTA / "catalogo.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def _baixar_itens(itens: list[dict], consulta: str, quantos: int) -> list[Path]:
    from src.editing import sfx
    PASTA.mkdir(parents=True, exist_ok=True)
    cat = _catalogo()
    gravados: list[Path] = []
    for it in itens:
        if len(gravados) >= quantos:
            break
        nome = re.sub(r"[^a-z0-9\-]+", "-", it["slug"].lower())[:60] + ".mp3"
        dest = PASTA / nome
        if dest.exists():
            gravados.append(dest)
            continue
        try:
            dest.write_bytes(_get(BASE + it["arquivo"], MAX_BYTES))
            x = sfx._decodificar(dest)
            motivo = "longo demais" if x.size > MAX_DURACAO_S * sfx.SR else sfx._reprova(x)
        except (OSError, PermissionError, ValueError, RuntimeError) as exc:
            motivo = f"falha ({exc})"
        if motivo:
            print(f"  descartado {it['titulo']}: {motivo}")
            dest.unlink(missing_ok=True)
            continue
        meta = {"license_key": "myinstants", "licenca": "desconhecida (upload de usuário; pode conter trecho protegido)",
                "origem": "myinstants.com", "titulo": it["titulo"], "pagina": it["pagina"], "consulta": consulta,
                "duracao_s": round(x.size / sfx.SR, 2),
                "aviso": "Pode gerar bloqueio de áudio no Instagram. Não usar em render comercial automático."}
        dest.with_suffix(".mp3.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        cat[nome] = {k: meta[k] for k in ("titulo", "pagina", "consulta", "duracao_s")}
        gravados.append(dest)
    (PASTA / "catalogo.json").write_text(json.dumps(cat, ensure_ascii=False, indent=1), encoding="utf-8")
    return gravados


def baixar(consulta: str, quantos: int = 3) -> list[Path]:
    return _baixar_itens(buscar(consulta, quantos * 3), consulta, quantos)


def listar_local(texto: str = "") -> list[tuple[str, dict]]:
    t = texto.lower()
    return [(k, v) for k, v in _catalogo().items() if not t or t in k.lower() or t in v["titulo"].lower()
            or t in v["consulta"].lower()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("buscar").add_argument("consulta")
    d = sub.add_parser("baixar")
    d.add_argument("consulta")
    d.add_argument("-n", type=int, default=3)
    p = sub.add_parser("populares")
    p.add_argument("-n", type=int, default=10)
    sub.add_parser("listar").add_argument("texto", nargs="?", default="")
    a = ap.parse_args(argv)
    if a.cmd == "buscar":
        for it in buscar(a.consulta):
            print(f"{it['titulo'][:50]:50} {it['pagina']}")
    elif a.cmd == "baixar":
        for f in baixar(a.consulta, a.n):
            print("baixado:", f)
    elif a.cmd == "populares":
        for f in _baixar_itens(populares(a.n * 2), "populares-br", a.n):
            print("baixado:", f)
    else:
        for k, v in listar_local(a.texto):
            print(f"{k:45} {v['duracao_s']:>5}s  {v['titulo']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
