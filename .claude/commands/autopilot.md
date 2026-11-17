---
description: "Executa todas as specs pendentes (SPEC_00 → SPEC_07) em sequência, sem intervenção humana."
---

Execute o projeto Impulso Stone Reels MCP de forma totalmente autônoma, seguindo
o `CLAUDE.md` à risca.

1. Leia `CLAUDE.md`, `specs/00_OVERVIEW.md` e `docs/PROGRESS.md`.
2. Se não houver repositório git, rode `git init` e faça um commit inicial do pacote de specs.
3. Para cada spec com status diferente de DONE, na ordem 00 → 07:
   a. Delegue ao subagente `spec-implementer`: "Implemente a SPEC_NN".
   b. Rode `bash scripts/gate.sh NN` você mesmo e confira o exit code.
   c. Delegue ao subagente `spec-verifier`: "Verifique a SPEC_NN".
   d. Se FAIL, devolva os achados ao `spec-implementer` e repita (máx. 6 ciclos;
      depois mude de abordagem e registre no ADR).
   e. Nas SPEC_02, 04, 05 e 07, rode também o `license-privacy-auditor` e registre
      os itens JURÍDICO em `docs/HUMAN_DEPENDENCIES.md`.
   f. Atualize ADR, `docs/PROGRESS.md`, rode `python -m src.core.doctor --write-report`
      (a partir da SPEC_00) e faça `git commit -m "spec-NN: ..."`.
4. Ao final: `bash scripts/gate.sh all`, escreva `docs/FINAL_REPORT.md` e responda com
   um resumo de 10 linhas no máximo: specs concluídas, tiers usados, pendências humanas
   por prioridade.

Nunca pare para perguntar nada. Falta de chave de API não é bloqueio.
