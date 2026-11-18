# Dossiê de conformidade — H-CASE-01

> Rascunho técnico para envio à organização do case. O envio e a resposta dependem de uma pessoa (pendência H-CASE-04).

## Fatos verificáveis
- Coleta em 17 e 18/11/2026 via actors do Apify (`instagram-reel-scraper`, `instagram-profile-scraper`, `instagram-hashtag-scraper`),
  rota combinada no kickoff de 26/10/2026 (confirmação formal pendente). Só dados públicos: legenda, curtidas, comentários, views, data, duração.
- 1.672 Reels de 76 perfis; 155 Reels com curtidas ocultas pelos autores foram **excluídos do ranking**; 167 colaborações de outro dono foram excluídas.
- Vídeos baixados (393) servem apenas para análise interna local (transcrição, frames, cortes). `*.mp4`, `dados/` e cookies estão no `.gitignore`
  e nunca foram versionados.
- A Etapa 2 (expansão) não foi executada; uma futura expansão pode usar a Graph API oficial (`business_discovery`) para ficar dentro dos Termos da Meta.

## Minuta
**Assunto:** [Impulso Stone Reels MCP] Confirmação de governança da base de dados (Kickoff 26/10/2026 — H-CASE-01)

Olá, organização do case Impulso Stone,

Para o registro formal no relatório final (FINAL_REPORT.md e ADR-009), gostaríamos de ratificar que a base de Reels públicos foi construída
pela rota alinhada no kickoff de 26/10/2026 (Apify, diante da ausência de dados internos de Insights da Stone). Utilizamos apenas metadados
públicos na janela de 12 meses; excluímos do ranking os 155 Reels com curtidas ocultas; e nenhum vídeo de terceiros é redistribuído ou
versionado, sendo o processamento local e efêmero, só para agregação estatística entre os 5 formatos.

Ficamos à disposição para qualquer recomendação adicional.
