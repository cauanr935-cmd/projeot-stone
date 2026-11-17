---
description: "Atualiza docs/HUMAN_DEPENDENCIES.md com o estado real do ambiente e as pendências registradas."
---

1. Se `src/core/doctor.py` existir, rode `python -m src.core.doctor --write-report`.
   Caso contrário, faça a sondagem manualmente (ffmpeg/ffprobe no PATH, Python,
   GPU, Ollama em localhost:11434, pesos em `models/`, fonte Montserrat, quais
   variáveis do `.env.example` estão definidas — só existência, nunca valores).
2. Garanta que cada pendência tenha: prioridade, spec, ação humana exata (com URL ou
   comando), impacto, fallback ativo e como verificar.
3. Remova da seção automática itens já resolvidos.
4. Responda com a tabela de pendências agrupada por prioridade.
