# ADR-001 — Topologia híbrida MCP com uso integral das 3 primitivas

**Status:** Aceito · **Specs:** 01, 07

## Contexto
Servidores MCP que expõem apenas Tools forçam o LLM a gastar chamadas de
inferência e tokens para buscar dados estáticos (transcrições, cenas,
perfis), queimando as quotas gratuitas (TPM/RPD) de que o projeto depende.

## Decisão
- **Resources** (controlados pelo cliente, custo zero de tool call): perfis
  CNAE (`stone-cnae://profiles/{cnae_code}`), catálogo de formatos,
  resumos multimodais (`stone-media://jobs/{job_id}/analysis_summary`,
  `scenes.csv`, `transcript.json`) e status de quota
  (`stone-quota://router/status`).
- **Prompts** (controlados pelo usuário): `gerar_reel_impulso_stone` e um
  por formato (`reel_bab`, `reel_product_demo_pas`, `reel_ugc_testimonial`,
  `reel_pas`, `reel_aida`).
- **Tools** (controladas pelo modelo): processamento pesado e escrita
  (análise, reframe, 2.5D, TTS, legendas, plano, render).
- **Primitivas de cliente:** Roots delimita o sistema de arquivos;
  Elicitation pergunta o formato e confirma sobrescrita; Sampling é
  opcional (escolha de gancho pelo LLM anfitrião).
- SDK: `mcp>=1.12,<2` com `FastMCP`; resolvido como `mcp==1.30.0`.
- URIs de CNAE usam a forma só-dígitos (`9602501`), porque a barra de
  `9602-5/01` quebra o template de URI.

## Consequências
+ O cliente anexa contexto sem gastar chamadas; ferramentas ficam enxutas.
− Clientes que não suportam Resources/Elicitation precisam de caminhos
  alternativos (as tools retornam `needs_format` em vez de decidir).

## Parâmetros calibrados
- MCP 1.30.0; stdio definido para produção e streamable HTTP opcional em
  `127.0.0.1:8765`.
- Recursos, prompts e tools verificados em sessão MCP em memória.
- URI de CNAE de teste é só-dígitos; resource converte para CNAE canônico.

## Desvios da pesquisa
- Elicitation não é requerida para gerar o menu no MCP: sem `format_id`, a
  tool retorna `needs_format` e as cinco opções em vez de selecionar
  automaticamente.

## Atualizações
- 2026-11-07 — implementação: resources, 6 prompts, 10 tools e servidor
  FastMCP 1.30.0.
