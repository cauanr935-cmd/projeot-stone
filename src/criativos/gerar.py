"""CLI: python -m src.criativos.gerar --perfil all|<id> [--formato N] [--sem-voz] [--saida DIR]"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.criativos import servico
from src.criativos.spec import carregar_perfis


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Gera criativos em motion graphics para os 10 perfis prioritários")
    ap.add_argument("--perfil", default="all", help="id do perfil, lista separada por vírgula ou 'all'")
    ap.add_argument("--negocio")
    ap.add_argument("--formato", type=int)
    ap.add_argument("--instrucoes", help="orientação extra para a IA (ignorada no modo offline)")
    ap.add_argument("--saida", type=Path, default=servico.SAIDA_PADRAO)
    ap.add_argument("--sem-voz", action="store_true")
    ap.add_argument("--listar", action="store_true")
    a = ap.parse_args(argv)
    if a.listar:
        for k, v in carregar_perfis().items():
            print(f"{k:22} CNAE {v['cnae']}  formato {v['format_id']}  {v['nome']}")
        return 0
    ids = list(carregar_perfis()) if a.perfil == "all" else a.perfil.split(",")
    falhas = 0
    for pid in ids:
        r = servico.gerar_criativo(pid, a.saida, a.negocio, a.formato, a.instrucoes, not a.sem_voz) \
            if len(ids) == 1 else servico.gerar_lote([pid], a.saida, not a.sem_voz)[0]
        ok = "erro" not in r and r.get("auditoria", {}).get("passou", False)
        falhas += not ok
        print(json.dumps({k: r.get(k) for k in ("perfil_id", "output", "duracao_s", "gerado_por", "erro")}
                         | {"auditoria_ok": ok}, ensure_ascii=False))
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
