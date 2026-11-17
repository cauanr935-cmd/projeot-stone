# ADR-002 — Roteamento em cascata (Zero-Cost Cascade) e isolamento de dados sensíveis

**Status:** Aceito (base da pesquisa) · **Spec:** 02

## Contexto
Limites voláteis dos free tiers (RPD/TPM da Groq, Neurons diários da
Cloudflare, quota de 300 s/dia do ZeroGPU), descontinuações em 2026
(GitHub Models, Chutes, DeepInfra) e a cláusula de uso de dados para treino
no plano gratuito da Gemini API.

## Decisão
`ZeroCostCascadeRouter` com cascata por modalidade (`config/providers.yaml`),
leitura de headers (`x-ratelimit-remaining-*`, `retry-after`) em tempo real,
circuit breaker por provedor, cache SHA-256 em disco (≥ 24 h) e desvio
automático para inferência local (WhisperX/faster-whisper, Ollama, Kokoro,
Piper, espeak-ng) quando houver limite, erro ou **dado sensível**. Mídia do
MEI é sensível por padrão; provedores com `trains_on_free_inputs` `true` ou
`unknown` ficam bloqueados para ela.

## Consequências
+ Nenhuma chave é obrigatória; o build e os testes rodam offline.
− Qualidade varia com o tier efetivo; o `render_report.json` registra qual
  foi usado.

## Parâmetros calibrados
- Orçamento de comutação 429 → próximo tier: < 500 ms (testado).
- Latência máxima edge-tts antes de comutar: 3 s.
- Limiar de prompt longo para LLM: 6.000 tokens.
_(preencher na SPEC_02: modelos que de fato responderam, versões, tempos medidos)_

## Desvios da pesquisa
_(preencher — ex.: nomes de modelos que não existiam)_

## Atualizações
- 2026-11-07 — pacote de specs: `unknown` tratado como `true` para dados sensíveis (fail-closed).
