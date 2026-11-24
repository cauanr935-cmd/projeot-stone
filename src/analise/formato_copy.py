"""Classifica um vídeo falado de MPE em um dos 5 formatos de copy (config/formats.yaml) por MOVIMENTOS RETÓRICOS.

Por que não reaproveitar `classificar.py`: o léxico dele conta palavras soltas e dá UGC a qualquer fala em 1ª pessoa
("eu", "meu"), o que joga quase todo dono de negócio ensinando algo em `ugc_testimonial`. Aqui cada formato exige o
MOVIMENTO que o define, e a posição na fala importa (abertura = 1º quarto, fecho = último quarto):

- pas              dor/erro/perda NA ABERTURA (+ solução depois): "agenda vazia?", "você está perdendo cliente"
- bab              contraste antes→depois (≥ 2 polos distintos): "antes eu…, hoje…", "do zero aos 100 mil"
- ugc_testimonial  relato vivido em PASSADO e 1ª pessoa (≥ 2 verbos distintos): "comecei", "vendi", "aprendi"
- product_demo_pas demonstração/instrução: passo a passo, imperativos, conta/fórmula, sequência (primeiro, depois)
- aida             promessa/curiosidade na abertura + lista de dicas + CTA no fecho: "segredo", "3 dicas", "chama no zap"

Devolve (formato, pontuações, confiança, evidências). Evidências listam as pistas achadas, para auditar o rótulo.
Os formatos são frameworks de copy: o rótulo estima a estrutura DOMINANTE, não é verdade de campo.
"""
from __future__ import annotations

import re
import unicodedata

FORMATOS = ("bab", "product_demo_pas", "ugc_testimonial", "pas", "aida")


def _norm(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")


# padrão -> rótulo curto da evidência
DOR = {r"\berros?\b|\berrad[oa]s?\b": "erro", r"\bprejuizo": "prejuízo", r"\bperd(?:er|endo|e|eu|em)\b": "perder",
       r"\b(?:agenda|loja|salao|oficina|caixa) vazi[oa]\b": "vazio", r"\bnao (?:vende|vendo|vendem|consegue|consigo|tem cliente)": "não vende",
       r"\bninguem (?:compra|chama|aparece|fecha)": "ninguém compra", r"\bproblema": "problema", r"\bdificuldade": "dificuldade",
       r"\b(?:pare|para) de\b": "pare de", r"\bnunca mais\b": "nunca mais", r"\bcuidado\b": "cuidado", r"\bevite\b": "evite",
       r"\bsem cliente": "sem cliente", r"\bfalir|\bquebrar\b|\bfechar as portas": "falir", r"\bvender barato|\bcobrar barato": "vender barato",
       r"\bcansad[oa]\b|\bfrustrad[oa]\b": "cansaço", r"\bmedo\b": "medo", r"\bnao faca\b|\bnao (?:faz|fazer)\b": "não faça"}
SOLUCAO = (r"\bsolucao\b", r"\bresolv", r"\bo segredo\b", r"\bfaca isso\b", r"\bo que eu faria\b", r"\bestrategia", r"\bpassa a\b", r"\bbasta\b")
ANTES = (r"\bantes\b", r"\bno comeco\b", r"\bera\b", r"\bsaia de\b", r"\bdo zero\b", r"\bnao tinha\b", r"\bsem nada\b")
DEPOIS = (r"\bdepois\b", r"\bhoje\b", r"\bagora\b", r"\bpassei a\b", r"\bate chegar\b", r"\baos \d", r"\btransform", r"\bmudou\b", r"\bresultado\b")
CONTRASTE = r"\bde \d[\d.,]*\w* (?:para|pra|a) \d|\bsaiu de .{1,25} para\b|\bdo zero aos?\b"
PASSADO_1P = (r"\bcomecei\b", r"\bfiz\b", r"\bvendi\b", r"\baprendi\b", r"\bconsegui\b", r"\bfaturei\b", r"\babri\b", r"\btive\b",
              r"\bganhei\b", r"\bpercebi\b", r"\bdescobri\b", r"\bcresci\b", r"\bcheguei\b", r"\bfoi assim\b", r"\bminha historia\b",
              r"\bdepoimento\b", r"\bpassei por\b", r"\bperdi\b", r"\bcomprei\b", r"\binvesti\b", r"\bcliente me (?:disse|falou)\b")
DEMO = (r"\bpasso a passo\b", r"\bprimeiro\b", r"\bsegundo\b", r"\bterceiro\b", r"\bem seguida\b", r"\bpegue\b", r"\bcoloque\b",
        r"\bmonte\b", r"\bcalcule\b", r"\bsome\b", r"\bmultiplique\b", r"\bdivida\b", r"\bformula\b", r"\bcomo (?:fazer|montar|calcular|precificar|cobrar)\b",
        r"\bveja\b", r"\bolha (?:so|aqui|isso)\b", r"\brepare\b", r"\bplanilha\b", r"\bsistema\b", r"\bmostrar\b", r"\bvou te mostrar\b",
        r"\bpreco de custo\b", r"\bcusto\b.*\blucro\b", r"\bmargem\b", r"\bvalor da hora\b", r"\bpor (?:hora|metro|ponto)\b")
PROMESSA = (r"\bsegredo\b", r"\bdescubra\b", r"\bvoce sabia\b", r"\bvou te (?:contar|falar|ensinar)\b", r"\bquer saber\b", r"\bsaiba\b",
            r"\baprenda\b", r"\bdica", r"\bmelhor (?:forma|jeito|estrategia)\b", r"\bfacil\b", r"\bsimples\b", r"\bsem (?:gastar|investir)\b")
LISTA = r"\b(?:\d+|tres|quatro|cinco|seis|sete|dez) (?:dicas?|estrategias?|acoes|jeitos|formas|passos|erros|coisas|ideias|motivos|tecnicas)\b"
CTA = (r"\bsiga\b", r"\bsegue\b", r"\bcomente\b", r"\bsalve\b", r"\bcompartilh", r"\blink\b", r"\bwhatsapp\b", r"\bzap\b", r"\bchama\b",
       r"\bchame\b", r"\binscreva", r"\bcurt", r"\bme segue\b", r"\bperfil\b", r"\bmentoria\b", r"\bgaranta\b", r"\bfale comigo\b", r"\bagende\b",
       r"\bencomende\b", r"\bpeca\b", r"\bmanda\b")


def _achados(pads, texto: str) -> list[str]:
    return [p for p in pads if re.search(p, texto)]


def classificar_formato(titulo: str, transcricao: str, feats: dict | None = None) -> tuple[str, dict[str, float], str, list[str]]:
    feats = feats or {}
    corpo = _norm(transcricao)
    tem_fala = len(corpo.split()) >= 12
    palavras = corpo.split()
    n = max(len(palavras), 1)
    abertura = " ".join(palavras[: max(int(n * 0.25), 12)])
    fecho = " ".join(palavras[int(n * 0.75):])
    tit = _norm(titulo)
    tudo = f"{tit} {corpo}"
    sc = dict.fromkeys(FORMATOS, 0.0)
    ev: list[str] = []

    # PAS: a dor precisa aparecer cedo; dor solta no meio é só assunto
    dor_ab = {r for p, r in DOR.items() if re.search(p, f"{tit} {abertura}")}
    dor_tot = {r for p, r in DOR.items() if re.search(p, tudo)}
    sc["pas"] = 2.0 * len(dor_ab) + 0.6 * len(dor_tot - dor_ab)
    if dor_tot and _achados(SOLUCAO, corpo):
        sc["pas"] += 1.0
    ev += [f"dor:{r}" for r in sorted(dor_tot)]

    # BAB: precisa dos dois polos (antes E depois) ou um contraste numérico explícito
    a, d = _achados(ANTES, tudo), _achados(DEPOIS, tudo)
    sc["bab"] = (1.5 * min(len(a), 2) + 1.2 * min(len(d), 2)) if a and d else 0.0
    if re.search(CONTRASTE, tudo):
        sc["bab"] += 2.5
        ev.append("contraste:de→para")
    if a and d:
        ev.append(f"antes/depois:{len(a)}+{len(d)}")

    # UGC: precisa de VÁRIOS verbos de relato em 1ª pessoa no passado — "eu"/"meu" sozinhos não contam
    rel = _achados(PASSADO_1P, tudo)
    sc["ugc_testimonial"] = 1.6 * len(rel) if len(rel) >= 2 else 0.4 * len(rel)
    if rel:
        ev.append(f"relato:{len(rel)}")
    if feats.get("face_detected_ratio", 0) >= 0.6 and feats.get("max_face_area_pct", 0) >= 8 and len(rel) >= 2:
        sc["ugc_testimonial"] += 0.8

    # DEMO: instrução/cálculo/sequência; sem rosto reforça (tela, produto, mãos)
    dem = _achados(DEMO, tudo)
    sc["product_demo_pas"] = 1.3 * len(dem)
    if dem:
        ev.append(f"demo:{len(dem)}")
    if feats.get("face_detected_ratio", 1) <= 0.2 and dem:
        sc["product_demo_pas"] += 1.0

    # AIDA: gancho de promessa + lista de dicas + CTA no FECHO (CTA no meio não vale)
    prom = _achados(PROMESSA, f"{tit} {abertura}")
    cta = _achados(CTA, fecho)
    lista = bool(re.search(LISTA, tudo))
    sc["aida"] = 1.2 * len(prom) + (1.5 if lista else 0) + 1.5 * min(len(cta), 2)
    if prom:
        ev.append(f"promessa:{len(prom)}")
    if lista:
        ev.append("lista")
    if cta:
        ev.append(f"cta_fecho:{len(cta)}")

    if not tem_fala:  # sem fala não há estrutura retórica a ler: o título só sugere AIDA (promessa)
        return "aida", sc, "baixa", ["sem fala"] + ev
    ordem = sorted(sc.items(), key=lambda kv: kv[1], reverse=True)
    (melhor, s1), (_, s2) = ordem[0], ordem[1]
    if s1 < 1.5:  # nenhum movimento claro: explicação genérica → demonstração/dica, nunca UGC por padrão
        return "product_demo_pas", sc, "baixa", ["sem movimento claro"] + ev
    return melhor, sc, "alta" if s1 - s2 >= 2.0 else "media", ev
