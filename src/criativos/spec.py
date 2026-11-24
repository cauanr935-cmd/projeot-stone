"""Contrato do criativo (CriativoSpec), perfis prioritários e roteiro offline por formato."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.config import _read, get_format

TipoCena = Literal["hook", "pontos", "antes_depois", "numero", "cta"]
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def carregar_perfis() -> dict[str, dict]:
    return {p["id"]: p for p in _read("perfis_prioritarios.yaml")["perfis"]}


def carregar_genericos() -> dict[str, dict]:
    """Padaria + perfis genéricos por segmento + 'geral': só para o pedido por conversa (não entram na lista dos 10)."""
    return {p["id"]: p for p in _read("perfis_prioritarios.yaml").get("perfis_genericos", [])}


def carregar_perfis_todos() -> dict[str, dict]:
    return {**carregar_perfis(), **carregar_genericos()}


def obter_perfil(perfil_id: str) -> dict:
    perfis = carregar_perfis_todos()
    if perfil_id not in perfis:
        raise KeyError(f"perfil '{perfil_id}' inexistente; opções: {', '.join(perfis)}")
    return perfis[perfil_id]


class Paleta(BaseModel):
    fundo1: str
    fundo2: str
    destaque: str
    acento: str
    texto: str = "#FFFFFF"

    @field_validator("*")
    @classmethod
    def _hex(cls, v: str) -> str:
        if not HEX.match(v):
            raise ValueError(f"cor inválida: {v} (use #RRGGBB)")
        return v


class Cena(BaseModel):
    tipo: TipoCena
    titulo: str = Field(min_length=1, max_length=80)
    itens: list[str] = Field(default_factory=list, max_length=4)
    # antes_depois: itens[0]=antes, itens[1]=depois. numero: valor em `numero`, legenda em `rotulo`.
    numero: str | None = None
    rotulo: str | None = None
    narracao: str = Field(min_length=1, max_length=300)
    duracao: float | None = Field(default=None, ge=1.5, le=15)
    icone: Literal["check", "x"] = "check"
    motivo: str = Field(default="", max_length=400)  # por que esta cena existe (exibido no front)

    @model_validator(mode="after")
    def _coerencia(self) -> "Cena":
        if self.tipo == "antes_depois" and len(self.itens) != 2:
            raise ValueError("antes_depois exige exatamente 2 itens [antes, depois]")
        if self.tipo == "numero" and not self.numero:
            raise ValueError("cena 'numero' exige o campo numero")
        if self.tipo == "pontos" and not self.itens:
            raise ValueError("cena 'pontos' exige itens")
        return self


class CriativoSpec(BaseModel):
    perfil_id: str
    formato_id: int = Field(ge=1, le=5)
    negocio: str
    titulo: str
    hook_overlay: str
    cta_canal: str = "WhatsApp"
    paleta: Paleta
    cenas: list[Cena] = Field(min_length=3, max_length=7)
    voz: str = "pf_dora"
    gerado_por: str = "template_engine"

    @field_validator("hook_overlay")
    @classmethod
    def _hook(cls, v: str) -> str:
        if len(v.split()) > 5:
            raise ValueError("hook_overlay deve ter no máximo 5 palavras (Frame Zero)")
        return v

    @model_validator(mode="after")
    def _estrutura(self) -> "CriativoSpec":
        if self.cenas[0].tipo != "hook":
            raise ValueError("a primeira cena deve ser 'hook'")
        if self.cenas[-1].tipo != "cta":
            raise ValueError("a última cena deve ser 'cta'")
        return self


def spec_offline(perfil_id: str, negocio: str | None = None, formato_id: int | None = None,
                 perfil: dict | None = None) -> CriativoSpec:
    """Roteiro determinístico (tier 'template_engine'): estrutura do framework do formato + copy do perfil.

    `perfil` (opcional) já vem com os ajustes do pedido falado (oferta, preço, canal), ver conversa.aplicar_briefing."""
    p = perfil or obter_perfil(perfil_id)
    fid = formato_id or p["format_id"]
    fmt = get_format(fid)
    nome = negocio or p["negocio"]
    d = p["destaque"]
    hook = Cena(tipo="hook", titulo=p["gancho"], narracao=f"{p['gancho']}. {p['dor']}.")
    cta = Cena(tipo="cta", titulo=p["cta"], itens=[nome], rotulo=p["prova"],
               narracao=f"{p['prova']}. {p['cta']}.")
    numero = Cena(tipo="numero", titulo="O que você leva", numero=d["valor"],
                  rotulo=d["rotulo"], narracao=f"{d['valor']} {d['rotulo']}.")
    if fid == 1:  # BAB
        cenas = [hook,
                 Cena(tipo="antes_depois", titulo="Antes e depois", itens=[p["antes"], p["depois"]],
                      narracao=f"Antes: {p['antes']}. Depois: {p['depois']}."),
                 Cena(tipo="pontos", titulo="Como eu faço", itens=p["solucao"],
                      narracao="O segredo é simples. " + ". ".join(p["solucao"]) + "."),
                 numero, cta]
    elif fid == 2:  # Product Demo + PAS
        cenas = [hook,
                 Cena(tipo="pontos", titulo="O que muda no meu", itens=p["solucao"],
                      narracao=". ".join(p["solucao"]) + "."),
                 numero, cta]
    elif fid == 3:  # UGC
        cenas = [hook,
                 Cena(tipo="pontos", titulo="Por que eu indico", itens=p["solucao"],
                      narracao="Sabe quando é difícil achar? " + ". ".join(p["solucao"]) + "."),
                 numero, cta]
    elif fid == 4:  # PAS
        cenas = [hook,
                 Cena(tipo="pontos", titulo="O risco de deixar pra depois", itens=p["agitacao"], icone="x",
                      narracao="Parece pouco, mas: " + ". ".join(p["agitacao"]) + "."),
                 Cena(tipo="pontos", titulo="A solução", itens=p["solucao"],
                      narracao=". ".join(p["solucao"]) + "."),
                 cta]
    else:  # AIDA
        cenas = [hook,
                 Cena(tipo="pontos", titulo="Onde quase todo mundo erra", itens=p["agitacao"], icone="x",
                      narracao=". ".join(p["agitacao"]) + "."),
                 Cena(tipo="pontos", titulo="O que funciona", itens=p["solucao"],
                      narracao=". ".join(p["solucao"]) + "."),
                 numero, cta]
    return CriativoSpec(perfil_id=perfil_id, formato_id=fid, negocio=nome, titulo=f"{nome} · {fmt['name']}",
                        hook_overlay=p["gancho"], cta_canal=p["cta_canal"], paleta=Paleta(**p["paleta"]),
                        cenas=cenas)


def _frases(texto: str) -> list[str]:
    partes = re.split(r"(?<=[.!?])\s+|\n+", texto.strip())
    return [x.strip() for x in partes if len(x.strip()) > 2]


def spec_do_roteiro(perfil_id: str, roteiro: str, negocio: str | None = None, formato_id: int | None = None,
                    perfil: dict | None = None) -> CriativoSpec:
    """Transforma o roteiro escrito/falado pelo usuário em cenas: 1ª frase = gancho, última = CTA, meio = pontos."""
    p = perfil or obter_perfil(perfil_id)
    fid = formato_id or p["format_id"]
    nome = negocio or p["negocio"]
    frases = _frases(roteiro)
    if len(frases) < 3:
        raise ValueError("roteiro curto demais (use pelo menos 3 frases)")
    curto = lambda t, n=6: " ".join(t.rstrip(".!?").split()[:n])  # noqa: E731
    meio = frases[1:-1][:15]
    grupos = [meio[i:i + 3] for i in range(0, len(meio), 3)][:5]
    cenas = [Cena(tipo="hook", titulo=curto(frases[0], 8), narracao=frases[0][:300])]
    for g in grupos:
        cenas.append(Cena(tipo="pontos", titulo="Olha só", itens=[curto(x) for x in g],
                          narracao=" ".join(g)[:300], motivo="Cena montada a partir do roteiro dado pelo cliente."))
    cenas.append(Cena(tipo="cta", titulo=curto(frases[-1], 8), itens=[nome], rotulo=p["prova"], narracao=frases[-1][:300]))
    return CriativoSpec(perfil_id=perfil_id, formato_id=fid, negocio=nome, titulo=f"{nome} · roteiro do cliente",
                        hook_overlay=curto(frases[0], 5), cta_canal=p["cta_canal"], paleta=Paleta(**p["paleta"]),
                        cenas=cenas, gerado_por="roteiro_do_usuario")
