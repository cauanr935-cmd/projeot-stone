"""Pedido em linguagem livre → briefing do criativo (com perguntas de complemento).

Fluxo do front/MCP: a pessoa fala (ou digita) → `interpretar(texto, estado)` extrai ramo, nome do negócio, oferta,
preço, formato, tom e roteiro → se faltar algo essencial devolve `pergunta` (que o front fala em voz alta) → a pessoa
responde → `interpretar` de novo, agora com o `estado` acumulado → `pronto=True` → `gerar_pedido(...)`.

Camadas (nenhuma exige chave): 1) regras em português (sempre); 2) LLM via LangChain (Claude/Gemini) refina a extração
quando houver chave. Ao LLM vai só o texto do pedido (nunca mídia). Perguntas: no máximo 1 rodada por campo.
"""
from __future__ import annotations

import logging
import re
import unicodedata
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.core.config import ROOT, _read
from src.criativos.spec import carregar_perfis

log = logging.getLogger("criativos.conversa")
PASTA_PEDIDOS = ROOT / "output" / "pedidos"

CAMPOS = ("perfil_id", "negocio", "oferta", "preco", "diferencial", "cta_canal", "tom", "formato_id", "roteiro")
ROTULOS = {"perfil_id": "o ramo do negócio", "negocio": "o nome do negócio", "oferta": "o que você quer divulgar"}

FORMATOS_PALAVRAS = {
    1: ["antes e depois", "transformação", "transformacao", "resultado"],
    2: ["demonstra", "mostrar o produto", "mostrando o produto", "como funciona", "passo a passo"],
    3: ["depoimento", "cliente falando", "avaliação", "avaliacao", "ugc", "indicação", "indicacao"],
    4: ["problema", "dor do cliente", "risco", "perde", "prejuízo", "prejuizo"],
    5: ["atenção", "atencao", "aida", "lançamento", "lancamento", "novidade"],
}
TONS = {"engraçado": ["engraçad", "engracad", "divertid", "humor", "leve", "descontra"],
        "emocional": ["emocion", "emoção", "emocao", "carinho", "história", "historia"],
        "direto": ["direto", "objetivo", "rápido", "rapido", "curto"],
        "profissional": ["profissional", "sério", "serio", "confiança", "confianca"]}


class BriefingLLM(BaseModel):
    """Saída estruturada pedida ao LLM (todos opcionais; vazio = não informado)."""
    perfil_id: str | None = Field(None, description="id do perfil mais próximo do ramo, ou nulo")
    negocio: str | None = Field(None, description="nome do negócio, se dito")
    oferta: str | None = Field(None, description="o que será divulgado (produto/serviço/promoção), frase curta")
    preco: str | None = Field(None, description="preço ou desconto citado, ex.: 'R$ 35' ou '20% off'")
    diferencial: str | None = Field(None, description="diferencial/prova citado, frase curta")
    tom: str | None = None
    roteiro: str | None = Field(None, description="se a pessoa ditou um roteiro/fala pronta, o texto dele")


def _norm(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


PULAR = re.compile(r"^\W*(pode (seguir|gerar|fazer|criar|continuar)|tanto faz|segue assim|nao tenho|nao sei|sem preco|sem promocao|deixa assim|use o padrao)")


def _vazio(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


# ------------------------------------------------------------------ regras (tier local, sempre disponível)
def detectar_perfil(texto: str) -> str | None:
    t = f" {_norm(texto)} "
    sin = _read("perfis_prioritarios.yaml").get("sinonimos", {})
    melhor, pontos = None, 0
    for pid, palavras in sin.items():
        n = sum(1 for w in palavras if re.search(rf"(?<!\w){re.escape(_norm(w))}(?!\w)", t))
        if n > pontos:
            melhor, pontos = pid, n
    return melhor


_NOME = r"([A-ZÀ-Ú0-9][\wÀ-ú'&.-]*(?:\s+(?:d[aeo]s?\s+)?[A-ZÀ-Ú0-9][\wÀ-ú'&.-]*){0,3})"
_PADROES_NOME = [
    rf"(?:chama(?:-se|do|da)?|nome (?:é|e|dele é|dela é)|se chama)\s+(?:de\s+)?[\"“]?{_NOME}",
    rf"(?:marca|empresa|negócio|negocio|loja|salão|salao|oficina|estúdio|estudio|studio|ateliê|atelie)\s+(?:chamad[oa]\s+)?[\"“]?([A-ZÀ-Ú][\wÀ-ú'&.-]*(?:\s+[A-ZÀ-Ú][\wÀ-ú'&.-]*){{0,3}})",
]


def extrair_nome(texto: str) -> str | None:
    for pad in _PADROES_NOME:
        m = re.search(pad, texto)
        if m:
            nome = re.sub(r"[.,;:!?\"”]+$", "", m.group(1)).strip()
            if nome and _norm(nome) not in {"o", "a", "meu", "minha", "um", "uma", "eu"}:
                return nome
    return None


def extrair_preco(texto: str) -> str | None:
    m = re.search(r"R\$\s?\d[\d.,]*", texto) or re.search(r"\b\d+(?:[.,]\d+)?\s*(?:reais|real)\b", texto, re.I) \
        or re.search(r"\b\d{1,2}\s?(?:%|por cento)\s*(?:de\s+)?(?:desconto|off)?", texto, re.I)
    return m.group(0).strip() if m else None


def extrair_oferta(texto: str) -> str | None:
    m = re.search(r"(?:quero|preciso|vou|gostaria de|queria)\s+(?:muito\s+)?(?:divulgar|vender|anunciar|promover|mostrar|fazer (?:um )?(?:v[ií]deo|reel|criativo|an[uú]ncio) (?:d[eao]s?|sobre|para divulgar))\s+(.+?)(?:[.!?;]|\s+(?:para|pro|pra|no|na|com)\s+(?:o|a|meu|minha|um|uma)\b|$)", texto, re.I)
    if not m:
        m = re.search(r"(?:promo[cç][aã]o|oferta|novidade|lan[cç]amento)\s+(?:de|do|da|sobre)\s+(.+?)(?:[.!?;,]|$)", texto, re.I)
    if m:
        o = re.sub(r"^(?:meus?|minhas?|o|a|os|as)\s+", "", m.group(1).strip(), flags=re.I)
        o = re.split(r"\s+(?:por|no|na|pelo|pela|via|em|de um jeito|de forma|com o objetivo)\s+(?=R\$|\d|whats|direct|insta|um |uma |jeito|forma|o |a )|,", o, maxsplit=1, flags=re.I)[0]
        if _norm(o) in {"trabalho", "negocio", "meu trabalho", "meu negocio", "algo", "isso", "tudo", "a empresa", "empresa", "loja"}:
            return None
        return " ".join(o.split()[:10]) or None
    return None


def extrair_formato(texto: str) -> int | None:
    t = _norm(texto)
    m = re.search(r"formato\s*(?:n[uú]mero\s*)?([1-5])\b", t)
    if m:
        return int(m.group(1))
    for fid, ps in FORMATOS_PALAVRAS.items():
        if any(_norm(p) in t for p in ps):
            return fid
    return None


def extrair_tom(texto: str) -> str | None:
    t = _norm(texto)
    return next((k for k, ps in TONS.items() if any(_norm(p) in t for p in ps)), None)


def extrair_canal(texto: str) -> str | None:
    t = _norm(texto)
    for chave, nome in (("whats", "WhatsApp"), ("direct", "Direct do Instagram"), ("telefone", "telefone"), ("ligue", "telefone")):
        if chave in t:
            return nome
    return None


def extrair_roteiro(texto: str) -> str | None:
    m = re.search(r"roteiro(?:\s+(?:é|e|seria|fica))?\s*[:\-]\s*(.+)$", texto, re.I | re.S)
    if m and len(m.group(1).split()) >= 12:
        return m.group(1).strip()
    return None


def _regras(texto: str) -> dict:
    return {"perfil_id": detectar_perfil(texto), "negocio": extrair_nome(texto), "oferta": extrair_oferta(texto),
            "preco": extrair_preco(texto), "formato_id": extrair_formato(texto), "tom": extrair_tom(texto),
            "cta_canal": extrair_canal(texto), "roteiro": extrair_roteiro(texto)}


def _llm(texto: str) -> dict:
    """Refinamento opcional via LangChain; qualquer falha devolve {} (as regras seguem valendo)."""
    from src.criativos.llm import escolher_llm
    nome, modelo = escolher_llm()
    if modelo is None:
        return {}
    try:
        from langchain_core.prompts import ChatPromptTemplate
        perfis = {k: v["nome"] for k, v in carregar_perfis().items()}
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Você extrai dados de um pedido falado em PT-BR por um microempreendedor que quer um Reel. "
                       "Preencha só o que foi dito, sem inventar. perfil_id deve ser um destes: {perfis}."),
            ("human", "{texto}")])
        r = (prompt | modelo.with_structured_output(BriefingLLM)).invoke({"perfis": perfis, "texto": texto})
        d = r.model_dump() if isinstance(r, BriefingLLM) else dict(r)
        if d.get("perfil_id") not in perfis:
            d["perfil_id"] = None
        return {k: v for k, v in d.items() if not _vazio(v)}
    except Exception as exc:
        log.info("extração via LLM falhou (%s); seguindo só com regras", str(exc)[:160])
        return {}


# ------------------------------------------------------------------ API pública
def estado_inicial() -> dict:
    return {"briefing": {}, "rodada": 0, "perguntou": []}


def interpretar(texto: str, estado: dict | None = None, usar_llm: bool = True) -> dict:
    """Atualiza o estado com o que a pessoa disse e decide se já dá para gerar ou se falta algo.

    Retorna {estado, briefing, faltando, pergunta, pronto, entendi}. `entendi` = frases curtas confirmando o que foi captado."""
    est = {**estado_inicial(), **(estado or {})}
    b = dict(est["briefing"])
    texto = (texto or "").strip()
    ultima = (est.get("perguntou") or [None])[-1] if est.get("perguntou") else None

    novo = _regras(texto)
    if usar_llm and texto:
        for k, v in _llm(texto).items():
            if _vazio(novo.get(k)):
                novo[k] = v
    # resposta curta a uma pergunta específica: aceita o texto inteiro como o campo pedido
    if ultima == "negocio" and _vazio(novo.get("negocio")) and 0 < len(texto.split()) <= 6:
        novo["negocio"] = re.sub(r"^(?:é|e|se chama|chama|o nome é|meu negócio é)\s+", "", texto, flags=re.I).strip(" .!")
    if ultima == "oferta" and _vazio(novo.get("oferta")) and texto:
        novo["oferta"] = " ".join(re.sub(r"^(?:eu )?(?:quero|vou)\s+(?:divulgar|vender)\s+", "", texto, flags=re.I).split()[:10])
    for k, v in novo.items():
        if not _vazio(v):
            b[k] = v
    # texto longo sem 'roteiro:' explícito vira direcionamento livre
    if texto and len(texto.split()) > 6:
        b["direcao"] = (b.get("direcao", "") + " " + texto).strip()[-1200:]

    perfis = carregar_perfis()
    if b.get("perfil_id") not in perfis:
        b.pop("perfil_id", None)
    essenciais = ["perfil_id", "negocio"] + (["oferta"] if est["rodada"] == 0 and not b.get("roteiro") else [])
    faltando = [c for c in essenciais if _vazio(b.get(c))]
    if PULAR.search(_norm(texto)) or est["rodada"] >= 2:  # nunca prender a pessoa: depois de 2 perguntas segue com o que há (ramo continua obrigatório)
        faltando = [c for c in faltando if c == "perfil_id"]
    pergunta = _montar_pergunta(faltando, b)
    est.update(briefing=b, rodada=est["rodada"] + (1 if faltando else 0),
               perguntou=(est.get("perguntou") or []) + ([faltando[0]] if faltando else []))
    return {"estado": est, "briefing": b, "faltando": faltando, "pergunta": pergunta, "pronto": not faltando,
            "entendi": _entendi(b)}


def _montar_pergunta(faltando: list[str], b: dict) -> str | None:
    if not faltando:
        return None
    ps = {"perfil_id": "Qual é o seu ramo? Por exemplo: salão, confeitaria, loja de roupas, oficina, aulas particulares ou pet.",
          "negocio": "Qual é o nome do seu negócio?",
          "oferta": "O que você quer divulgar nesse vídeo? Pode ser um produto, um serviço ou uma promoção, e se tiver preço, me conta."}
    if len(faltando) == 1:
        return ps[faltando[0]]
    nomes = " e ".join(ROTULOS[c] for c in faltando[:2])
    return f"Percebi que falta {nomes}. Pode me contar? É só falar."


def _entendi(b: dict) -> list[str]:
    perfis = carregar_perfis()
    out = []
    if b.get("perfil_id"):
        out.append(f"Ramo: {perfis[b['perfil_id']]['nome']}")
    for k, r in (("negocio", "Negócio"), ("oferta", "Divulgar"), ("preco", "Preço"), ("tom", "Tom"), ("cta_canal", "Contato")):
        if b.get(k):
            out.append(f"{r}: {b[k]}")
    if b.get("formato_id"):
        out.append(f"Formato: {b['formato_id']}")
    if b.get("roteiro"):
        out.append("Roteiro próprio: sim")
    return out


def aplicar_briefing(b: dict) -> dict:
    """Briefing → (perfil_id, negocio, formato_id, instrucoes, perfil_override, roteiro) para o grafo."""
    p = carregar_perfis()[b["perfil_id"]]
    over: dict[str, Any] = {}
    if b.get("cta_canal"):
        over["cta_canal"] = b["cta_canal"]
    curto = lambda t, n=6: " ".join(str(t).split()[:n])  # noqa: E731
    if b.get("oferta"):
        over["solucao"] = ([curto(b["oferta"])] + [x for x in p["solucao"] if x != curto(b["oferta"])])[:4]
    if b.get("diferencial"):
        over["prova"] = curto(b["diferencial"], 8)
    if b.get("preco"):
        over["destaque"] = {"valor": str(b["preco"])[:14], "rotulo": curto(b.get("oferta") or p["destaque"]["rotulo"], 7)}
    partes = []
    if b.get("oferta"):
        partes.append(f"Divulgar: {b['oferta']}")
    if b.get("preco"):
        partes.append(f"Preço/desconto: {b['preco']}")
    if b.get("diferencial"):
        partes.append(f"Diferencial: {b['diferencial']}")
    if b.get("tom"):
        partes.append(f"Tom: {b['tom']}")
    if b.get("direcao"):
        partes.append(f"Pedido original da pessoa (siga a direção): {b['direcao']}")
    return {"perfil_id": b["perfil_id"], "negocio": b.get("negocio"), "formato_id": b.get("formato_id"),
            "instrucoes": ". ".join(partes) or None, "perfil_override": over, "roteiro_usuario": b.get("roteiro")}


def gerar_pedido(b: dict, com_voz: bool = True, pedido_id: str | None = None) -> dict:
    """Roda o grafo com o briefing e grava em output/pedidos/<pedido_id>.*  Retorna {pedido_id, saida, trace}."""
    from src.criativos.grafo import executar
    if _vazio(b.get("perfil_id")):
        raise ValueError("briefing sem ramo (perfil_id)")
    pid = pedido_id or uuid.uuid4().hex[:12]
    a = aplicar_briefing(b)
    r = executar(a["perfil_id"], a["negocio"], a["formato_id"], a["instrucoes"], PASTA_PEDIDOS, com_voz,
                 perfil_override=a["perfil_override"], roteiro_usuario=a["roteiro_usuario"], nome_base=f"pedido_{pid}")
    return {"pedido_id": pid, **r}


def arquivos_pedido(pedido_id: str) -> tuple[Path | None, Path | None]:
    if not re.fullmatch(r"[a-f0-9]{12}", pedido_id or ""):
        return None, None
    mp4, rac = PASTA_PEDIDOS / f"pedido_{pedido_id}.mp4", PASTA_PEDIDOS / f"pedido_{pedido_id}.raciocinio.json"
    return (mp4 if mp4.is_file() else None, rac if rac.is_file() else None)
