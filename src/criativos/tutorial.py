"""Gera o vídeo tutorial da home (src/web/tutorial.mp4 + tutorial.jpg) com o próprio motor de motion graphics e voz local.

Uso: python -m src.criativos.tutorial   (≈1 min; sem chave, sem rede)
"""
from __future__ import annotations

import argparse
from pathlib import Path

from src.core.config import ROOT
from src.core.ffmpeg import run_ffmpeg
from src.criativos.motion import renderizar_criativo
from src.criativos.spec import Cena, CriativoSpec, Paleta

DESTINO = ROOT / "src" / "web"


def spec_tutorial() -> CriativoSpec:
    return CriativoSpec(
        perfil_id="tutorial", formato_id=5, negocio="Impulso Criativos", titulo="Como criar seu Reel falando",
        hook_overlay="Fale. A gente cria.", cta_canal="WhatsApp",
        paleta=Paleta(fundo1="#07100C", fundo2="#0B6B3A", destaque="#00D66C", acento="#7DFFB5", texto="#FFFFFF"),
        gerado_por="tutorial",
        cenas=[
            Cena(tipo="hook", titulo="Fale. A gente cria.",
                 narracao="Criar um Reel para o seu negócio é falar. Só isso. Veja como é rápido."),
            Cena(tipo="pontos", titulo="Em 3 passos", itens=["Aperte o microfone", "Conte seu negócio", "Responda o que eu perguntar"],
                 narracao="Primeiro, aperte o microfone. Depois, conte qual é o seu negócio e o que você quer divulgar. "
                          "Se faltar alguma informação, eu pergunto, e você responde falando de novo."),
            Cena(tipo="pontos", titulo="O que contar", itens=["Nome do negócio", "O que vender", "Preço ou promoção", "Tom do vídeo"],
                 narracao="Diga o nome do seu negócio, o que você quer vender, o preço ou a promoção, e como quer o vídeo. "
                          "Se já tiver um roteiro, pode ler ele."),
            Cena(tipo="numero", titulo="Pronto em", numero="1 min", rotulo="seu Reel vertical, com voz e legenda",
                 narracao="Em cerca de um minuto, seu Reel fica pronto, com voz, música e o formato certo para o Instagram."),
            Cena(tipo="pontos", titulo="Boas práticas", itens=["Fale em lugar silencioso", "Frases curtas e diretas", "Cite um preço real", "Um pedido por vez"],
                 narracao="Para o melhor resultado, fale em um lugar silencioso, use frases curtas, cite um preço real, e peça um vídeo por vez."),
            Cena(tipo="cta", titulo="Experimente agora", itens=["Impulso Criativos"], rotulo="é só falar",
                 narracao="Agora é com você. Aperte o microfone e fale."),
        ])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sem-voz", action="store_true")
    a = ap.parse_args()
    mp4 = DESTINO / "tutorial.mp4"
    r = renderizar_criativo(spec_tutorial(), mp4, com_voz=not a.sem_voz)
    run_ffmpeg(["-y", "-ss", "1.2", "-i", str(mp4), "-frames:v", "1", "-q:v", "3", str(DESTINO / "tutorial.jpg")])
    print(r)


if __name__ == "__main__":
    main()
