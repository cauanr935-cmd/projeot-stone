"""Efeitos sonoros dos criativos: cascata Biblioteca local CC0 → gerador procedural (o render NUNCA usa rede).

    from src.editing.sfx import gerar_trilha_sfx
    info = gerar_trilha_sfx(spec.cenas, duracoes, Path("sfx.wav"))

Cascata por efeito (mesmo desenho da música em config/providers.yaml):
  1. assets/audio_cc0/sfx/<nome>*.{wav,mp3,ogg,flac}  — biblioteca local; cada arquivo tem um <arquivo>.json com a licença.
  2. gerador procedural (numpy)                       — licença do próprio projeto; garante autonomia, sem chave nem rede.
A API entra só para ABASTECER a biblioteca, em comando à parte (`python -m src.editing.sfx baixar`), com trava de licença:
Openverse (sem chave) devolve só CC0/PDM, mas quase tudo hospedado no Freesound, bloqueado em config/licenses.yaml
(ADR-005). Por isso o download recusa essa origem a menos que REELS_ALLOW_FREESOUND_CC0=1 (decisão jurídica humana).

CLI:
    python -m src.editing.sfx listar                       # efeitos e de onde cada um vem hoje
    python -m src.editing.sfx amostras --saida DIR         # grava um .wav de cada efeito (para ouvir)
    python -m src.editing.sfx buscar "whoosh"              # busca no Openverse (CC0/PDM) sem baixar
    python -m src.editing.sfx baixar whoosh "whoosh" -n 1  # baixa para a biblioteca local (respeita a trava)
    python -m src.editing.sfx popular -n 4                 # abastece todas as categorias (várias variantes cada)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from src.core.ffmpeg import _bin

log = logging.getLogger(__name__)

SR = 48000
BIBLIOTECA = Path(os.getenv("REELS_SFX_DIR", "assets/audio_cc0/sfx"))
EXTS = (".wav", ".mp3", ".ogg", ".flac", ".m4a")
FONTES_BLOQUEADAS = {"freesound"}          # espelha blocked_sources_explicit de config/licenses.yaml
LICENCAS_LIVRES = {"cc0", "pdm"}           # sem atribuição obrigatória
OPENVERSE = "https://api.openverse.org/v1/audio/"
UA = "reels-sfx/0.1"


# ----------------------------------------------------------------------------- geradores procedurais
def _t(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR)) / SR


def _norm(x: np.ndarray, pico: float = 0.9) -> np.ndarray:
    return (x / (np.abs(x).max() or 1.0) * pico).astype(np.float32)


def _passa_baixa(x: np.ndarray, alfa: np.ndarray) -> np.ndarray:
    """Filtro de 1 polo com coeficiente variável no tempo (varredura de timbre)."""
    y, ac = np.empty_like(x), 0.0
    for i, (v, a) in enumerate(zip(x, alfa)):
        ac += a * (v - ac)
        y[i] = ac
    return y


def _ruido(n: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).normal(0, 1, n)


def whoosh(dur: float = 0.55) -> np.ndarray:
    t = _t(dur)
    r = _ruido(t.size, 1)
    lp = _passa_baixa(r, np.linspace(0.015, 0.45, t.size))
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.6
    return _norm((lp - _passa_baixa(lp, np.full(t.size, 0.01))) * env)


def swipe(dur: float = 0.3) -> np.ndarray:
    t = _t(dur)
    lp = _passa_baixa(_ruido(t.size, 2), np.linspace(0.5, 0.03, t.size))
    return _norm(lp * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.2)


def pop(dur: float = 0.14) -> np.ndarray:
    t = _t(dur)
    f = 260 + 520 * np.exp(-t * 38)
    corpo = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 28)
    return _norm(corpo + 0.25 * _ruido(t.size, 3) * np.exp(-t * 400))


def tick(dur: float = 0.06) -> np.ndarray:
    t = _t(dur)
    return _norm(np.sin(2 * np.pi * 2300 * t) * np.exp(-t * 90) + 0.3 * _ruido(t.size, 4) * np.exp(-t * 300))


def impact(dur: float = 0.7) -> np.ndarray:
    t = _t(dur)
    sub = np.sin(2 * np.pi * np.cumsum(38 + 70 * np.exp(-t * 14)) / SR) * np.exp(-t * 6)
    estalo = _passa_baixa(_ruido(t.size, 5), np.full(t.size, 0.12)) * np.exp(-t * 26)
    return _norm(sub + 0.5 * estalo)


def riser(dur: float = 1.3) -> np.ndarray:
    t = _t(dur)
    p = t / dur
    tom = np.sin(2 * np.pi * np.cumsum(180 + 1700 * p ** 2) / SR)
    ruido = _passa_baixa(_ruido(t.size, 6), 0.02 + 0.4 * p)
    return _norm((0.6 * tom + 0.5 * ruido) * p ** 1.5 * np.minimum(1, (dur - t) / 0.04 + 0.0))


def chime(dur: float = 1.0) -> np.ndarray:
    t = _t(dur)
    saida = np.zeros_like(t)
    for atraso, f in ((0.0, 880.0), (0.14, 1318.5)):
        m = t >= atraso
        tt = t[m] - atraso
        saida[m] += sum(a * np.sin(2 * np.pi * f * k * tt) for k, a in ((1, 1.0), (2, 0.3), (3.01, 0.12))) * np.exp(-tt * 4.5)
    return _norm(saida)


def erro(dur: float = 0.4) -> np.ndarray:
    t = _t(dur)
    buzz = np.sign(np.sin(2 * np.pi * 140 * t)) * 0.5 + np.sin(2 * np.pi * 105 * t)
    return _norm(buzz * np.exp(-t * 7) * np.minimum(1, t * 400))


GERADORES = {"whoosh": whoosh, "swipe": swipe, "pop": pop, "tick": tick, "impact": impact, "riser": riser, "chime": chime, "erro": erro}
# nomes extras: sem arquivo na biblioteca caem no gerador parecido
ALIAS = {"click": "tick", "boom": "impact", "sucesso": "chime", "caixa": "chime", "notificacao": "pop", "brilho": "chime"}
NOMES = (*GERADORES, *ALIAS)
# categoria -> consultas no Openverse (os títulos do Freesound são em inglês)
CATEGORIAS: dict[str, list[str]] = {
    "whoosh": ["whoosh", "swoosh transition"], "swipe": ["swipe", "swish"], "pop": ["pop", "bubble pop"],
    "tick": ["tick", "short click"], "click": ["ui click", "button click"], "impact": ["impact hit", "thud"],
    "boom": ["boom", "bass drop"], "riser": ["riser", "sweep up"], "chime": ["chime", "ding"],
    "sucesso": ["success", "level up"], "caixa": ["cash register", "coin"], "notificacao": ["notification", "alert"],
    "erro": ["error buzzer", "wrong answer"], "brilho": ["sparkle", "magic twinkle"],
}
_CACHE: dict[str, tuple[np.ndarray, dict]] = {}


# ----------------------------------------------------------------------------- biblioteca local
def _decodificar(arq: Path) -> np.ndarray:
    cmd = [_bin("ffmpeg"), "-hide_banner", "-nostats", "-v", "error", "-i", str(arq), "-ac", "1", "-ar", str(SR),
           "-f", "f32le", "-"]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode or not proc.stdout:
        raise RuntimeError(f"ffmpeg não decodificou {arq.name}: {proc.stderr.decode(errors='replace')[-300:]}")
    return np.frombuffer(proc.stdout, dtype=np.float32)


def _licenca_do_arquivo(arq: Path) -> dict:
    meta = arq.with_suffix(arq.suffix + ".json")
    if meta.exists():
        return json.loads(meta.read_text(encoding="utf-8"))
    return {"license_key": "local-cc0", "licenca": "CC0-1.0 (assumida; sem arquivo de proveniência)", "arquivo": arq.name}


def _aparar(x: np.ndarray, max_s: float = 2.5) -> np.ndarray:
    """Tira o silêncio inicial (senão o som chega atrasado em relação à animação) e limita a duração."""
    pico = np.abs(x).max() or 1.0
    ativo = np.nonzero(np.abs(x) > 0.06 * pico)[0]
    ini = max(int(ativo[0]) - int(0.008 * SR), 0) if ativo.size else 0
    return _norm(x[ini: ini + int(max_s * SR)])


def arquivos_da_biblioteca(nome: str) -> list[Path]:
    """Variantes de um efeito: <nome>.ext ou <nome>_NN.ext (não confunde 'tick' com 'ticket')."""
    if not BIBLIOTECA.is_dir():
        return []
    ex = re.compile(rf"^{re.escape(nome)}(_\d+)?$", re.I)
    return sorted(a for a in BIBLIOTECA.iterdir() if a.suffix.lower() in EXTS and ex.match(a.stem))


def _da_biblioteca(nome: str, k: int = 0) -> tuple[np.ndarray, dict] | None:
    arqs = arquivos_da_biblioteca(nome)
    for j in range(len(arqs)):  # a partir da variante k, pula arquivo que não decodifica
        arq = arqs[(k + j) % len(arqs)]
        try:
            x = _decodificar(arq)
        except RuntimeError as exc:
            log.info("sfx '%s': %s; tentando a próxima variante", nome, exc)
            continue
        return _aparar(x), {**_licenca_do_arquivo(arq), "tier": "local_cc0_library", "variantes": len(arqs)}
    return None


def resolver(nome: str, k: int = 0) -> tuple[np.ndarray, dict]:
    """Cascata: biblioteca local (variante k, em rodízio) → procedural. Loga modalidade/tier/provider/motivo."""
    if nome not in NOMES:
        raise KeyError(f"efeito desconhecido '{nome}'")
    chave = f"{nome}#{k % max(len(arquivos_da_biblioteca(nome)), 1)}"
    if chave not in _CACHE:
        achado = _da_biblioteca(nome, k)
        if achado:
            log.info("cascata sfx modality=sfx tier=local provider=local_cc0_library nome=%s reason=arquivo_na_biblioteca", nome)
        else:
            base = ALIAS.get(nome, nome)
            achado = (GERADORES[base](), {"license_key": "procedural-sfx", "licenca": "gerado pelo projeto", "tier": "procedural"})
            log.info("cascata sfx modality=sfx tier=procedural provider=numpy nome=%s reason=sem_arquivo_local", nome)
        _CACHE[chave] = achado
    return _CACHE[chave]


# ----------------------------------------------------------------------------- linha do tempo dos criativos
@dataclass(frozen=True)
class Evento:
    t: float        # segundos desde o início do vídeo
    nome: str
    ganho: float
    variante: int = 0   # rodízio entre os arquivos da biblioteca: o mesmo som não se repete em sequência


def eventos_do_criativo(cenas, duracoes: list[float]) -> list[Evento]:
    """Sons nos instantes em que a animação de cada cena acontece (tempos espelham src/criativos/motion.py)."""
    bruto: list[tuple[float, str, float]] = []
    inicio = 0.0
    for i, (c, d) in enumerate(zip(cenas, duracoes)):
        if i > 0:
            bruto.append((inicio - 0.04, "whoosh" if i % 2 else "swipe", 0.55))
        if c.tipo == "hook":
            bruto += [(inicio + 0.10, "boom", 0.85), (inicio + 0.12, "impact", 0.55)]
        elif c.tipo == "pontos":
            erro = getattr(c, "icone", "check") == "x"
            for k in range(len(c.itens)):
                t = inicio + 0.45 + k * 0.35 + 0.08
                bruto.append((t, "erro" if erro and k == 0 else "tick" if erro else "pop", 0.6 if erro else 0.7))
        elif c.tipo == "antes_depois":
            bruto += [(inicio + 0.05, "swipe", 0.5), (inicio + 0.9, "tick", 0.6), (inicio + 1.0, "pop", 0.7),
                      (inicio + 1.05, "brilho", 0.4)]
        elif c.tipo == "numero":
            bruto += [(inicio + 0.05, "riser", 0.5), (inicio + 0.15, "pop", 0.65), (inicio + 1.3, "impact", 0.7),
                      (inicio + 1.32, "caixa", 0.55)]
        elif c.tipo == "cta":
            bruto += [(inicio + 0.30, "pop", 0.7), (inicio + 0.80, "sucesso", 0.75), (inicio + 0.85, "notificacao", 0.35)]
        inicio += d
    contagem: dict[str, int] = {}
    ev = []
    for t, nome, ganho in sorted((b for b in bruto if b[0] < inicio), key=lambda b: b[0]):
        ev.append(Evento(t, nome, ganho, contagem.get(nome, 0)))
        contagem[nome] = contagem.get(nome, 0) + 1
    return ev


def gerar_trilha_sfx(cenas, duracoes: list[float], saida: Path, commercial: bool | None = None) -> dict:
    """Renderiza os efeitos numa trilha mono 48 kHz (WAV 16 bits) e devolve a proveniência de cada som usado."""
    total = sum(duracoes)
    eventos = eventos_do_criativo(cenas, duracoes)
    mix = np.zeros(int((total + 1.5) * SR), dtype=np.float32)
    usados: dict[str, dict] = {}
    for e in eventos:
        x, meta = resolver(e.nome, e.variante)
        usados[e.nome] = meta
        i = max(int(e.t * SR), 0)
        n = min(x.size, mix.size - i)
        if n > 0:
            mix[i:i + n] += x[:n] * e.ganho
    if commercial is None:
        commercial = os.getenv("REELS_COMMERCIAL", "1") == "1"
    from src.router.license_guard import validate_commercial_sources
    avisos = validate_commercial_sources(sorted({m["license_key"] for m in usados.values()}), commercial)
    mix = np.clip(mix, -0.98, 0.98)
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(saida), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype("<i2").tobytes())
    return {"arquivo": str(saida), "eventos": len(eventos), "efeitos": usados, "avisos_licenca": avisos}


# ----------------------------------------------------------------------------- Openverse (abastece a biblioteca)
def buscar_openverse(consulta: str, max_ms: int = 4000, n: int = 10) -> list[dict]:
    """Candidatos CC0/PDM curtos. Sem chave. Marca quais passam na trava de origem."""
    q = urllib.parse.urlencode({"q": consulta, "license": ",".join(sorted(LICENCAS_LIVRES)), "page_size": 20})   # anônimo: páginas maiores dão 401
    req = urllib.request.Request(f"{OPENVERSE}?{q}", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            itens = json.load(r).get("results", [])
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Openverse recusou a busca (HTTP {exc.code}). Acesso anônimo tem limite de taxa/tamanho; "
                         "tente de novo em alguns minutos.") from exc
    except OSError as exc:
        raise SystemExit(f"sem rede para o Openverse ({exc}). O render segue funcionando com a biblioteca local/procedural.") from exc
    liberada = os.getenv("REELS_ALLOW_FREESOUND_CC0") == "1"
    saida = []
    for it in itens:
        if not it.get("url") or (it.get("duration") or 0) > max_ms:
            continue
        origem = (it.get("source") or "").lower()
        saida.append({"id": it["id"], "titulo": it.get("title"), "origem": origem, "licenca": it["license"],
                      "duracao_ms": it.get("duration"), "url": it["url"], "pagina": it.get("foreign_landing_url"),
                      "autor": it.get("creator"), "permitido": origem not in FONTES_BLOQUEADAS or liberada})
        if len(saida) >= n:
            break
    return saida


def baixar_para_biblioteca(nome: str, consulta: str, quantos: int = 1) -> list[Path]:
    if nome not in NOMES:
        raise SystemExit(f"efeito desconhecido '{nome}'. Use um de: {', '.join(NOMES)}")
    cands = buscar_openverse(consulta, max_ms=2500)
    ok = [c for c in cands if c["permitido"] and _titulo_ok(c["titulo"]) and c["id"] not in _ids_da_biblioteca()]
    if not ok:
        bloqueados = {c["origem"] for c in cands}
        raise SystemExit(f"nenhum candidato liberado ({len(cands)} achados; origens {sorted(bloqueados) or '—'}). "
                         "Fontes em blocked_sources_explicit (ADR-005) exigem REELS_ALLOW_FREESOUND_CC0=1 após revisão jurídica.")
    BIBLIOTECA.mkdir(parents=True, exist_ok=True)
    gravados: list[Path] = []
    for c in ok:
        if len(gravados) >= quantos:
            break
        ext = Path(urllib.parse.urlparse(c["url"]).path).suffix.lower() or ".mp3"
        destino = BIBLIOTECA / f"{nome}_{len(arquivos_da_biblioteca(nome)) + 1:02d}{ext}"
        try:
            req = urllib.request.Request(c["url"], headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                destino.write_bytes(r.read())
            motivo = _reprova(_decodificar(destino))
        except (OSError, RuntimeError) as exc:
            motivo = f"falha ao baixar/decodificar ({exc})"
        if motivo:
            log.info("sfx %s: descartado '%s' — %s", nome, c["titulo"], motivo)
            destino.unlink(missing_ok=True)
            continue
        destino.with_suffix(destino.suffix + ".json").write_text(json.dumps({
            "license_key": "openverse-cc0", "licenca": c["licenca"].upper(), "origem": c["origem"], "titulo": c["titulo"],
            "autor": c["autor"], "pagina": c["pagina"], "url": c["url"], "id": c["id"], "consulta": consulta,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        gravados.append(destino)
    return gravados


_TITULO_RUIM = re.compile(r"music|song|loop|voice|speech|vocal|talk|singing|ambien|drone|album|beat\b", re.I)


def _titulo_ok(titulo: str | None) -> bool:
    """Descarta o que não é efeito curto (música, voz, ambiente)."""
    return not _TITULO_RUIM.search(titulo or "")


def _ids_da_biblioteca() -> set[str]:
    ids = set()
    for j in BIBLIOTECA.glob("*.json") if BIBLIOTECA.is_dir() else []:
        try:
            ids.add(json.loads(j.read_text(encoding="utf-8")).get("id"))
        except (OSError, ValueError):
            pass
    return ids


def _reprova(x: np.ndarray) -> str | None:
    """Controle de qualidade objetivo (não substitui ouvir): vazio, quase mudo ou saturado."""
    if x.size < int(0.05 * SR):
        return "curto demais"
    pico = float(np.abs(x).max())
    if pico < 0.02:
        return "quase mudo"
    if (np.abs(x) >= 0.999 * pico).mean() > 0.02 and pico >= 0.99:
        return "saturado"
    return None


def popular_biblioteca(por_categoria: int = 4, categorias: list[str] | None = None) -> dict[str, int]:
    """Baixa várias variantes de cada categoria. Uma busca por consulta (o acesso anônimo tem limite diário)."""
    resultado: dict[str, int] = {}
    for nome, consultas in CATEGORIAS.items():
        if categorias and nome not in categorias:
            continue
        tem = len(arquivos_da_biblioteca(nome))
        for consulta in consultas:
            falta = por_categoria - len(arquivos_da_biblioteca(nome))
            if falta <= 0:
                break
            try:
                baixar_para_biblioteca(nome, consulta, falta)
            except SystemExit as exc:
                log.info("sfx %s '%s': %s", nome, consulta, exc)
        resultado[nome] = len(arquivos_da_biblioteca(nome)) - tem
    return resultado


# ----------------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("listar")
    a = sub.add_parser("amostras")
    a.add_argument("--saida", default="output/sfx_amostras")
    b = sub.add_parser("buscar")
    b.add_argument("consulta")
    d = sub.add_parser("popular", help="baixa várias variantes de todas as categorias (respeita a trava de licença)")
    d.add_argument("-n", type=int, default=4, help="variantes por categoria")
    d.add_argument("--so", help="categorias separadas por vírgula")
    c = sub.add_parser("baixar")
    c.add_argument("nome")
    c.add_argument("consulta")
    c.add_argument("-n", type=int, default=1)
    args = ap.parse_args(argv)

    if args.cmd == "listar":
        for nome in NOMES:
            x, meta = resolver(nome)
            print(f"{nome:12} {x.size / SR:5.2f}s  tier={meta['tier']:18} variantes={len(arquivos_da_biblioteca(nome)):>2}  licença={meta['licenca']}")
    elif args.cmd == "amostras":
        pasta = Path(args.saida)
        pasta.mkdir(parents=True, exist_ok=True)
        for nome in GERADORES:
            x, _ = resolver(nome)
            with wave.open(str(pasta / f"{nome}.wav"), "wb") as w:
                w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
                w.writeframes((x * 32767).astype("<i2").tobytes())
        print(f"{len(GERADORES)} amostras em {pasta}")
    elif args.cmd == "buscar":
        for it in buscar_openverse(args.consulta):
            print(f"{'OK ' if it['permitido'] else 'BLQ'} {it['origem']:10} {it['licenca']:4} {it['duracao_ms']:>5}ms  {it['titulo'][:50]}")
    elif args.cmd == "popular":
        novos = popular_biblioteca(args.n, args.so.split(",") if args.so else None)
        print("novos por categoria:", novos, "| total de arquivos:", sum(len(arquivos_da_biblioteca(n)) for n in CATEGORIAS))
    elif args.cmd == "baixar":
        for p in baixar_para_biblioteca(args.nome, args.consulta, args.n):
            print("gravado", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
