"""Motion graphics 1080x1920 gerados em código (Pillow + ffmpeg), sem nenhum ativo externo.

Cada cena do CriativoSpec vira uma animação (texto cinético, cartões, antes/depois, contador, CTA).
Áudio: voz Kokoro/edge via roteador de custo zero + trilha procedural própria (sem licença de terceiros).
"""
from __future__ import annotations

import asyncio
import logging
import math
import re
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from src.core.ffmpeg import _bin, ffprobe_json
from src.criativos.spec import Cena, CriativoSpec

log = logging.getLogger("criativos.motion")
W, H, FPS = 1080, 1920, 30
SAFE_TOP, SAFE_BOTTOM = 260, 1480  # zonas seguras da UI do Reels
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FADE = 0.28


def _hex(c: str) -> tuple[int, int, int]:
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    for path in ((FONT_BOLD if bold else FONT_REG), FONT_BOLD, FONT_REG):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def out_cubic(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def out_back(x: float, s: float = 1.9) -> float:
    x = min(max(x, 0.0), 1.0)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    linhas, atual = [], ""
    for palavra in text.split():
        teste = f"{atual} {palavra}".strip()
        if draw.textlength(teste, font=font) <= max_w or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


class Fundo:
    """Fundo animado sem "bolhas": gradiente que desliza + estilo por perfil (listras, varredura de luz ou painéis).
    Calculado em 1/4 da resolução e ampliado (suave por natureza e ~20x mais barato por quadro)."""

    Q = 4

    def __init__(self, spec: CriativoSpec):
        q = self.Q
        w, h = W // q, H // q
        a, b = np.array(_hex(spec.paleta.fundo1), np.float32), np.array(_hex(spec.paleta.fundo2), np.float32)
        t = np.linspace(0, 1, h * 2, dtype=np.float32)[:, None, None]
        self.base = (a * (1 - t) + b * t) * np.ones((1, w, 1), np.float32)  # 2h de altura: rola vertical sem emenda
        self.c1, self.c2 = np.array(_hex(spec.paleta.acento), np.float32), np.array(_hex(spec.paleta.destaque), np.float32)
        self.estilo = sum(map(ord, spec.perfil_id or "x")) % 3
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        self.xx, self.yy, self.w, self.h = xx * q, yy * q, w, h
        v = np.sqrt(((self.xx - W / 2) / (W / 2)) ** 2 + ((self.yy - H / 2) / (H / 2)) ** 2)
        self.vinheta = (1 - .28 * np.clip(v - .35, 0, 1) ** 1.5)[..., None].astype(np.float32)

    def frame(self, t: float) -> Image.Image:
        h = self.h
        off = int((h * .5) * (.5 + .5 * math.sin(t * .35)))
        img = self.base[off:off + h].copy()
        xx, yy = self.xx, self.yy
        if self.estilo == 0:  # listras diagonais que correm
            m = (((xx + yy * .6 - t * 110) % 260) < 70).astype(np.float32)[..., None] * .10
            img = img * (1 - m) + self.c1 * m
        elif self.estilo == 1:  # feixe de luz varrendo a tela
            pos = (t * 420) % (W + H + 800) - 400
            m = np.exp(-(((xx * .75 + yy * .35) - pos) / 170) ** 2)[..., None] * .22
            img = img * (1 - m) + self.c1 * m
        else:  # painéis angulares deslizando
            m = ((((xx * .5 - yy + (t * 70) % 900)) % 900) < 300).astype(np.float32)[..., None] * .09
            img = img * (1 - m) + self.c2 * m
        halo = np.exp(-(((xx - W * (.5 + .35 * math.sin(t * .6))) / 520) ** 2 + ((yy - H * .32) / 620) ** 2))[..., None] * .12
        img = img * (1 - halo) + self.c2 * halo
        peq = Image.fromarray(np.clip(img * self.vinheta, 0, 255).astype(np.uint8), "RGB")
        return peq.resize((W, H), Image.BILINEAR).convert("RGBA")


def _texto_centro(d: ImageDraw.ImageDraw, texto: str, y: int, font, cor, max_w: int = 900, gap: int = 14,
                  sombra: bool = True) -> int:
    for linha in wrap(d, texto, font, max_w):
        w = d.textlength(linha, font=font)
        if sombra:
            d.text(((W - w) / 2 + 4, y + 5), linha, font=font, fill=(0, 0, 0, 110))
        d.text(((W - w) / 2, y), linha, font=font, fill=cor)
        y += font.size + gap
    return y


def _icone(d: ImageDraw.ImageDraw, tipo: str, cx: int, cy: int, r: int, cor) -> None:
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=cor)
    k = r * .5
    if tipo == "check":
        d.line([(cx - k, cy), (cx - k * .2, cy + k * .8), (cx + k, cy - k * .7)], fill=(255, 255, 255, 255),
               width=max(6, r // 4), joint="curve")
    else:
        d.line([(cx - k * .8, cy - k * .8), (cx + k * .8, cy + k * .8)], fill=(255, 255, 255, 255), width=max(6, r // 4))
        d.line([(cx - k * .8, cy + k * .8), (cx + k * .8, cy - k * .8)], fill=(255, 255, 255, 255), width=max(6, r // 4))


def cena_hook(d, spec: CriativoSpec, c: Cena, t: float, dur: float) -> None:
    pal = spec.paleta
    palavras = c.titulo.split()
    fonte = _font(150 if len(palavras) <= 3 else 124)
    # quebra em linhas por palavra para o efeito cinético
    linhas = wrap(d, c.titulo, fonte, 940)
    y = SAFE_TOP + 430
    idx = 0
    total = len(palavras)
    for linha in linhas:
        ws = linha.split()
        largura = d.textlength(linha, font=fonte)
        x = (W - largura) / 2
        for w in ws:
            ini = idx * 0.16
            p = out_back((t - ini) / 0.45)
            wlen = d.textlength(w + " ", font=fonte)
            if p > 0:
                cor = _hex(pal.destaque) if idx == total - 1 else _hex(pal.texto)
                tam = max(10, int(fonte.size * min(p, 1.15)))
                f2 = _font(tam)
                dy = (1 - min(p, 1)) * 60
                d.text((x + 5, y + 6 + dy), w, font=f2, fill=(0, 0, 0, 120))
                d.text((x, y + dy), w, font=f2, fill=(*cor, 255))
            x += wlen
            idx += 1
        y += fonte.size + 30
    # sublinhado pulsante
    prog = out_cubic((t - total * .16) / .5)
    larg = 620 * prog
    pulso = 1 + .06 * math.sin(t * 6)
    d.rounded_rectangle([(W - larg * pulso) / 2, y + 20, (W + larg * pulso) / 2, y + 40], 10, fill=_hex(pal.acento))
    sub = out_cubic((t - 0.9) / .5)
    if sub > 0:
        f = _font(52, bold=False)
        _texto_centro(d, c.narracao.split(". ", 1)[-1].rstrip("."), int(y + 100 + (1 - sub) * 40), f,
                      (*_hex(pal.texto), int(230 * sub)), 820, sombra=False)


def cena_pontos(d, spec: CriativoSpec, c: Cena, t: float, dur: float) -> None:
    pal = spec.paleta
    p = out_cubic(t / .5)
    y = SAFE_TOP + 190
    cor_tit = _hex(pal.destaque if c.icone == "check" else pal.acento)
    y = _texto_centro(d, c.titulo, int(y - (1 - p) * 50), _font(74), (*cor_tit, int(255 * p)), 940)
    y += 50
    cor_ic = _hex(pal.acento if c.icone == "check" else "#E5484D")
    fonte = _font(56)
    for i, item in enumerate(c.itens):
        pi = out_back((t - .45 - i * .35) / .55, 1.3)
        if pi <= 0:
            continue
        linhas = wrap(d, item, fonte, 700)
        h = 70 + len(linhas) * 70
        off = (1 - min(pi, 1)) * 700
        x0, x1 = 70 + off, W - 70 + off
        d.rounded_rectangle([x0 + 6, y + 8, x1 + 6, y + h + 8], 36, fill=(0, 0, 0, 90))
        d.rounded_rectangle([x0, y, x1, y + h], 36, fill=(255, 255, 255, 235))
        _icone(d, c.icone, int(x0 + 80), int(y + h / 2), 40, (*cor_ic, 255))
        ty = y + 35
        for linha in linhas:
            d.text((x0 + 150, ty), linha, font=fonte, fill=(20, 20, 30, 255))
            ty += 70
        y += h + 36


def cena_antes_depois(d, spec: CriativoSpec, c: Cena, t: float, dur: float) -> None:
    pal = spec.paleta
    antes, depois = c.itens
    topo, alt = SAFE_TOP + 90, 540
    p1 = out_cubic(t / .5)
    # painel ANTES (cinza)
    d.rounded_rectangle([70 - (1 - p1) * 900, topo, W - 70 - (1 - p1) * 900, topo + alt], 48, fill=(70, 70, 80, 235))
    d.text((120 - (1 - p1) * 900, topo + 40), "ANTES", font=_font(48), fill=(200, 200, 210, 255))
    if p1 > .5:
        _texto_centro(d, antes, topo + 200, _font(68), (230, 230, 235, 255), 820, sombra=False)
    # divisor e painel DEPOIS (revelado por wipe)
    p2 = out_cubic((t - 1.0) / .8)
    y2 = topo + alt + 50
    if p2 > 0:
        d.rounded_rectangle([70, y2, 70 + (W - 140) * p2, y2 + alt], 48, fill=_hex(pal.acento))
        if p2 > .6:
            d.text((120, y2 + 40), "DEPOIS", font=_font(48), fill=(255, 255, 255, 255))
            _texto_centro(d, depois, y2 + 200, _font(68), (255, 255, 255, 255), 820, sombra=True)
        seta = out_back((t - .9) / .5)
        cx, cy = W // 2, topo + alt + 25
        d.polygon([(cx - 36, cy - 30), (cx + 36, cy - 30), (cx, cy + 20)], fill=_hex(pal.destaque))
        _ = seta


def cena_numero(d, spec: CriativoSpec, c: Cena, t: float, dur: float) -> None:
    pal = spec.paleta
    p = out_cubic(t / .4)
    y = _texto_centro(d, c.titulo, int(SAFE_TOP + 220 - (1 - p) * 40), _font(66, False), (*_hex(pal.texto), int(255 * p)), 900)
    valor = c.numero or ""
    m = re.match(r"^(\D*?)(\d+)(.*)$", valor)
    if m and t < 1.4:
        pref, num, suf = m.groups()
        valor = f"{pref}{int(int(num) * out_cubic(t / 1.3))}{suf}"
    pop = out_back((t - .15) / .6)
    tam = int(190 * max(pop, .01))
    fonte = _font(min(tam, 200) or 10)
    while d.textlength(valor, font=fonte) > 940 and fonte.size > 60:
        fonte = _font(fonte.size - 8)
    w = d.textlength(valor, font=fonte)
    cy = H // 2 - 60
    d.rounded_rectangle([(W - w) / 2 - 60, cy - 40, (W + w) / 2 + 60, cy + fonte.size + 60], 60, fill=(0, 0, 0, 90))
    d.text(((W - w) / 2, cy), valor, font=fonte, fill=_hex(pal.destaque))
    if c.rotulo:
        q = out_cubic((t - .7) / .5)
        _texto_centro(d, c.rotulo, int(cy + fonte.size + 120 + (1 - q) * 40), _font(58, False),
                      (*_hex(pal.texto), int(255 * q)), 860)


def cena_cta(d, spec: CriativoSpec, c: Cena, t: float, dur: float) -> None:
    pal = spec.paleta
    p = out_cubic(t / .5)
    nome = c.itens[0] if c.itens else spec.negocio
    y = _texto_centro(d, nome, int(SAFE_TOP + 150 - (1 - p) * 40), _font(60), (*_hex(pal.destaque), int(255 * p)), 900)
    if c.rotulo:
        y = _texto_centro(d, f"“{c.rotulo}”", y + 20, _font(54, False), (*_hex(pal.texto), int(230 * p)), 860, sombra=False)
    y += 60
    q = out_back((t - .3) / .6)
    y = _texto_centro(d, c.titulo, int(y + (1 - min(q, 1)) * 60), _font(88), (*_hex(pal.texto), int(255 * min(q, 1))), 920)
    # botão pulsante
    pulso = 1 + .05 * math.sin(t * 7)
    bw, bh = 760 * pulso, 170 * pulso
    by = max(y + 80, 1080)
    r = out_cubic((t - .8) / .5)
    if r > 0:
        cor_botao = (37, 211, 102) if "whats" in spec.cta_canal.lower() else _hex(pal.acento)
        d.rounded_rectangle([(W - bw) / 2 + 6, by + 10, (W + bw) / 2 + 6, by + bh + 10], 85, fill=(0, 0, 0, 100))
        d.rounded_rectangle([(W - bw) / 2, by, (W + bw) / 2, by + bh], 85, fill=(*cor_botao, int(255 * r)))
        f = _font(62)
        txt = f"Chama no {spec.cta_canal}"
        tw = d.textlength(txt, font=f)
        d.text(((W - tw) / 2, by + bh / 2 - 40), txt, font=f, fill=(255, 255, 255, int(255 * r)))
    if "pix" in c.titulo.lower() and r > 0:
        f = _font(46)
        d.rounded_rectangle([W / 2 - 150, by + 230, W / 2 + 150, by + 310], 40, outline=_hex(pal.destaque), width=5)
        tw = d.textlength("Aceito Pix", font=f)
        d.text(((W - tw) / 2, by + 245), "Aceito Pix", font=f, fill=_hex(pal.destaque))


CENAS = {"hook": cena_hook, "pontos": cena_pontos, "antes_depois": cena_antes_depois,
         "numero": cena_numero, "cta": cena_cta}


def _quadro_cena(spec: CriativoSpec, fundo: Fundo, c: Cena, t_cena: float, dur: float, t_global: float,
                 total: float) -> Image.Image:
    quadro = fundo.frame(t_global)
    camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(camada, "RGBA")
    # marca no topo (fora da faixa de UI do Reels)
    f = _font(36, False)
    d.text((70, 150), spec.negocio.upper(), font=f, fill=(*_hex(spec.paleta.texto), 190))
    CENAS[c.tipo](d, spec, c, t_cena, dur)
    # câmera: entra deslizando com "pop" de zoom, segue com push-in lento e sai com impulso
    entra = out_cubic(t_cena / 0.38)
    sai = max(0.0, (t_cena - (dur - 0.22)) / 0.22) ** 2
    lado = 1 if (hash(c.tipo) + int(dur * 10)) % 2 == 0 else -1
    zoom = (1 + .06 * (t_cena / max(dur, .1))) * (1 + (1 - entra) * .14) * (1 + sai * .05)
    dx = lado * ((1 - entra) * W * .22 - sai * W * .18)
    cx = W / 2
    camada = camada.transform((W, H), Image.AFFINE, (1 / zoom, 0, cx - (cx + dx) / zoom, 0, 1 / zoom, H / 2 - (H / 2) / zoom),
                              Image.BILINEAR)
    fade = min(1.0, t_cena / .16, max(0.0, (dur - t_cena) / .16))
    if fade < 1:
        a = camada.getchannel("A").point(lambda v: int(v * fade))
        camada.putalpha(a)
    quadro = Image.alpha_composite(quadro, camada)
    if t_cena < .12:  # flash de corte na cor de destaque
        flash = Image.new("RGBA", (W, H), (*_hex(spec.paleta.destaque), int(70 * (1 - t_cena / .12))))
        quadro = Image.alpha_composite(quadro, flash)
    d2 = ImageDraw.Draw(quadro, "RGBA")
    d2.rounded_rectangle([70, 100, W - 70, 112], 6, fill=(255, 255, 255, 60))
    d2.rounded_rectangle([70, 100, 70 + (W - 140) * t_global / total, 112], 6, fill=_hex(spec.paleta.destaque))
    return quadro.convert("RGB")


# ----------------------------------------------------------------------------- áudio
def _duracao(path: Path) -> float:
    return float(ffprobe_json(path)["format"]["duration"])


def _trilha_procedural(path: Path, dur: float, sr: int = 44100) -> None:
    """Pad suave original (acordes por seno + tremolo): sem licença de terceiros."""
    t = np.arange(int(dur * sr)) / sr
    acordes = [(220.0, 277.18, 329.63), (196.0, 246.94, 293.66), (174.61, 220.0, 261.63), (196.0, 246.94, 293.66)]
    sinal = np.zeros_like(t)
    passo = 4.0
    for i, acorde in enumerate(acordes * int(dur // (passo * 4) + 2)):
        ini, fim = i * passo, (i + 1) * passo
        m = (t >= ini) & (t < fim)
        if not m.any():
            continue
        env = np.minimum(1, (t[m] - ini) / .5) * np.minimum(1, (fim - t[m]) / .5)
        for f in acorde:
            sinal[m] += env * np.sin(2 * np.pi * f * t[m]) / 3
    sinal *= (.8 + .2 * np.sin(2 * np.pi * 2 * t))
    sinal = sinal / (np.abs(sinal).max() or 1) * .6
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((sinal * 32767).astype(np.int16).tobytes())


async def _vozes(spec: CriativoSpec, pasta: Path) -> list[Path | None]:
    from src.router.cascade_router import ZeroCostCascadeRouter
    router = ZeroCostCascadeRouter()
    saidas: list[Path | None] = []
    for i, c in enumerate(spec.cenas):
        mp3 = pasta / f"voz_{i}.mp3"
        try:
            await router.synthesize_ptbr_voiceover(c.narracao, mp3, mp3.with_suffix(".srt"), spec.voz)
            saidas.append(mp3)
        except Exception as exc:  # TTS indisponível: segue só com trilha
            log.info("TTS indisponível na cena %d (%s); seguindo sem voz", i, exc)
            saidas.append(None)
    return saidas


def _mixar_audio(vozes: list[Path | None], duracoes: list[float], trilha: Path, saida: Path,
                 sfx: Path | None = None) -> None:
    total = sum(duracoes)
    cmd: list[str] = [_bin("ffmpeg"), "-hide_banner", "-nostats", "-y"]
    partes, rotulos, n = [], [], 0
    inicio = 0.0
    for v, dur in zip(vozes, duracoes):
        if v:
            cmd += ["-i", str(v)]
            ms = int(inicio * 1000) + 150
            partes.append(f"[{n}:a]aresample=44100,adelay={ms}|{ms},apad=whole_dur={total:.3f}[v{n}]")
            rotulos.append(f"[v{n}]")
            n += 1
        inicio += dur
    cmd += ["-i", str(trilha)]
    if sfx:
        cmd += ["-i", str(sfx)]
    if rotulos:
        partes.append("".join(rotulos) + f"amix=inputs={len(rotulos)}:normalize=0:duration=longest[voz]")
        partes.append(f"[{n}:a]volume=0.16,atrim=0:{total:.3f}[bg]")
        partes.append("[voz][bg]amix=inputs=2:normalize=0:duration=longest[mix0]")
    else:
        partes.append(f"[{n}:a]volume=0.5,atrim=0:{total:.3f}[mix0]")
    if sfx:  # efeitos por cima de voz+trilha; o loudnorm abaixo acerta o conjunto
        partes.append(f"[{n + 1}:a]aresample=44100,volume=0.45,apad=whole_dur={total:.3f},atrim=0:{total:.3f}[fx]")
        partes.append("[mix0][fx]amix=inputs=2:normalize=0:duration=longest[mix]")
    else:
        partes.append("[mix0]anull[mix]")
    partes.append("[mix]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,"
                  f"afade=t=out:st={max(total - .5, 0):.2f}:d=0.5[out]")
    cmd += ["-filter_complex", ";".join(partes), "-map", "[out]", "-ac", "2", str(saida)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(f"ffmpeg áudio falhou: {proc.stderr[-1500:]}")


# ----------------------------------------------------------------------------- render
def renderizar_criativo(spec: CriativoSpec, saida: Path, com_voz: bool = True, progresso=None,
                        com_sfx: bool = True) -> dict:
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="criativo_") as tmp:
        tmp = Path(tmp)
        vozes = asyncio.run(_vozes(spec, tmp)) if com_voz else [None] * len(spec.cenas)
        duracoes = []
        for c, v in zip(spec.cenas, vozes):
            base = c.duracao or 3.0
            duracoes.append(round(max(base, (_duracao(v) + .7) if v else base), 2))
        from src.core.config import get_format
        dmin = get_format(spec.formato_id)["duration"]["min"] + 0.4  # margem sobre o mínimo do formato
        total = sum(duracoes)
        if total < dmin:  # estica as pausas de leitura proporcionalmente (voz fica no início de cada cena)
            fator = dmin / total
            duracoes = [round(d * fator, 2) for d in duracoes]
            total = sum(duracoes)
        trilha = tmp / "trilha.wav"
        _trilha_procedural(trilha, total + 1)
        audio = tmp / "audio.m4a.wav"
        info_sfx = None
        if com_sfx:
            from src.editing.sfx import gerar_trilha_sfx
            info_sfx = gerar_trilha_sfx(spec.cenas, duracoes, tmp / "sfx.wav")
        _mixar_audio(vozes, duracoes, trilha, audio, Path(info_sfx["arquivo"]) if info_sfx else None)

        cmd = [_bin("ffmpeg"), "-hide_banner", "-nostats", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(audio),
               "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
               "-fps_mode", "cfr", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart",
               "-shortest", str(saida)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        fundo = Fundo(spec)
        n_total = int(round(total * FPS))
        limites = np.cumsum([0, *duracoes])
        try:
            for n in range(n_total):
                tg = n / FPS
                i = min(int(np.searchsorted(limites, tg, side="right") - 1), len(spec.cenas) - 1)
                quadro = _quadro_cena(spec, fundo, spec.cenas[i], tg - limites[i], duracoes[i], tg, total)
                proc.stdin.write(quadro.tobytes())  # type: ignore[union-attr]
                if progresso and n % 30 == 0:
                    progresso(n / n_total)
            proc.stdin.close()  # type: ignore[union-attr]
            err = proc.stderr.read().decode(errors="replace")  # type: ignore[union-attr]
            if proc.wait():
                raise RuntimeError(f"ffmpeg vídeo falhou: {err[-1500:]}")
        except BrokenPipeError:
            raise RuntimeError(f"ffmpeg encerrou antes: {proc.stderr.read().decode(errors='replace')[-1500:]}")  # type: ignore[union-attr]
    return {"output": str(saida), "duracao_s": round(total, 2), "cenas": len(spec.cenas),
            "voz": any(vozes),
            "sfx": ({"eventos": info_sfx["eventos"], "tiers": {k: v["tier"] for k, v in info_sfx["efeitos"].items()},
                     "avisos_licenca": info_sfx["avisos_licenca"]} if info_sfx else None),
            "perfil_id": spec.perfil_id, "formato_id": spec.formato_id,
            "gerado_por": spec.gerado_por}
