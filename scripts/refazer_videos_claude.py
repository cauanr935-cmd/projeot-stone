"""Refaz o tutorial e os exemplos da galeria com sessões do Claude (mesmo conteúdo, visual de produção).

Uso: python scripts/refazer_videos_claude.py [--only pet_banho_tosa tutorial] [--workers 2]
Saída em output/edicoes/ex_<id>/ (final.mp4, capa.jpg, legenda.txt...). NÃO substitui os vídeos antigos:
isso é feito depois da revisão (scripts/aplicar_videos_novos.py).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.criativos import sessao_claude  # noqa: E402

STATUS = ROOT / "output" / "edicoes" / "_lote_status.json"
REF = "output/edicoes/03afb76c5fc8/fonte"  # render anterior (bolo de pote): pode servir de ponto de partida técnico

QUALIDADE = f"""REFAZER vídeo de vitrine do produto. O visual anterior era motion graphic de baixa qualidade (texto sobre gradiente com bolhas
flutuantes, mesmo molde em todas as cenas). Mantenha o CONTEÚDO (narração e mensagens abaixo) mas entregue qualidade de produção:
- Cada cena com uma composição própria e ilustrações do assunto desenhadas em código com acabamento (formas com gradiente, sombra suave,
  contornos consistentes): nada de apenas texto parado. Tipografia forte e legível, hierarquia clara, margens seguras do Reels.
- Mantenha a paleta indicada e a identidade do negócio.
- A narração (voz local pt-BR) diz exatamente os textos de narração abaixo; a legenda na tela acompanha a fala palavra a palavra e NÃO repete
  o mesmo texto que já está grande na tela (escolha um dos dois em cada momento).
- Conferência obrigatória antes de entregar: extraia 1 quadro por segundo, confirme que NENHUM quadro está vazio/lavado (>85% de cor uma só)
  e que não há texto duplicado ou cortado; corrija e re-renderize se houver. Verifique ffprobe e loudness entre -16 e -13 LUFS.
- Se ajudar, reaproveite técnica (não as ilustrações do bolo de pote) do render anterior em {REF} (se existir).
- Duração: a da narração + respiro; mínimo 20 s."""


def jobs() -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    from src.criativos.tutorial import spec_tutorial
    t = spec_tutorial().model_dump()
    out["tutorial"] = (json.dumps(t, ensure_ascii=False), "Vídeo TUTORIAL do produto 'Impulso Criativos' (o usuário aperta o microfone, fala o pedido, o Reel sai pronto). "
                       "Mostre a interface de verdade desenhada em código: botão de microfone, balões de conversa, barra de progresso, o celular com o Reel pronto.")
    for f in sorted((ROOT / "output" / "criativos").glob("*.spec.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out[d["perfil_id"]] = (json.dumps({k: d[k] for k in ("negocio", "titulo", "hook_overlay", "cta_canal", "paleta", "cenas")}, ensure_ascii=False),
                               f"Reel de exemplo do negócio '{d['negocio']}' (ramo: {d['perfil_id'].replace('_', ' ')}).")
    return out


def rodar(item: tuple[str, tuple[str, str]]) -> tuple[str, dict]:
    nome, (spec, intro) = item
    texto = f"{intro}\n\n{QUALIDADE}\n\nCONTEÚDO (JSON com cenas, narrações e paleta):\n{spec}"
    t0 = time.time()
    try:
        r = sessao_claude.editar(texto, [], f"ex_{nome}", lambda **k: None)
        res = {"ok": True, "segundos": round(time.time() - t0), "video": r["video"], "arquivos": r["arquivos"]}
    except Exception as exc:
        res = {"ok": False, "segundos": round(time.time() - t0), "erro": str(exc)[:300]}
    estado = json.loads(STATUS.read_text()) if STATUS.exists() else {}
    estado[nome] = res
    STATUS.write_text(json.dumps(estado, ensure_ascii=False, indent=1))
    print(nome, res, flush=True)
    return nome, res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    todos = jobs()
    itens = [(k, v) for k, v in todos.items() if not a.only or k in a.only]
    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(rodar, itens))
    return 0


if __name__ == "__main__":
    sys.exit(main())
