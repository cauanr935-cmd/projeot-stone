---
description: "Implementa uma spec específica e só termina com o gate verde e o verificador aprovando. Uso: /implement-spec 03"
argument-hint: "<NN>"
---

Implemente a SPEC_$ARGUMENTS do projeto Impulso Stone Reels MCP.

1. Confirme em `docs/PROGRESS.md` que todas as specs anteriores estão DONE. Se alguma
   não estiver, implemente-a primeiro (ordem serial obrigatória).
2. Delegue ao subagente `spec-implementer`: "Implemente a SPEC_$ARGUMENTS".
3. Rode `bash scripts/gate.sh $ARGUMENTS`.
4. Delegue ao subagente `spec-verifier`: "Verifique a SPEC_$ARGUMENTS". Repita 2–4 até PASS.
5. Atualize ADR, `docs/PROGRESS.md`, `docs/HUMAN_DEPENDENCIES.md` e faça commit
   `spec-$ARGUMENTS: <resumo>`.

Não peça nada ao usuário; registre dependências humanas e siga.
