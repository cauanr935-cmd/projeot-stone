# Know-how de edição viral (extraído da base)

Gerado por `python -m src.analise.edicao_padroes extrair && ... agregar`. Base: 636 Reels (249 do top 10% x 387 de controle). Análise automática de vídeo (OpenCV/ffmpeg); descreve padrões, não prova causa.

## Ritmo e câmera

| métrica | top 10% (p25 / mediana / p75) | controle (mediana) |
|---|---|---|
| cortes por minuto | 0.0 / **1.39** / 7.38 | 0.8 |
| duração do plano (s) | 4.25 / **11.25** / 35.0 | 14.88 |
| 1º corte (s) | 2.94 / **5.25** / 11.87 | 6.62 |
| punch-in por minuto | 0.0 / **0.0** / 0.0 | 0.0 |
| movimento nos 3 s iniciais | 3.74 / **7.14** / 10.39 | 5.88 |
| duração do Reel (s) | 22.3 / **55.4** / 92.23 | 48.37 |
| Reels com corte nos 3 s | 16.9% | 15.2% |
| planos com push-in (aproximação) | 19.5% | 24.8% |
| planos com pull-out (afastamento) | 30.6% | 23.2% |

### Onde caem os cortes (% por décimo da duração, top 10%)

`15.1 | 11.8 | 11.2 | 6.9 | 8.1 | 10.7 | 9.2 | 7.0 | 7.5 | 12.4`

## Ganchos (primeiros 3 s da fala)

Reels do top cuja 1ª palavra começa em até 0,5 s: **71.1%**.

| tipo | % no top | % controle | lift | molde |
|---|---|---|---|---|
| numero_valor | 23.8 | 13.2 | 1.8 | Número concreto no 1º segundo: «R$ [valor] / [N]% / [N] erros que [consequência]» |
| pergunta | 20.6 | 14.7 | 1.4 | Pergunta direta sobre a dor ou o desejo do cliente: «Você ainda [faz X] sem saber [consequência]?» |
| urgencia_novidade | 10.1 | 7.6 | 1.32 | Novidade/urgência: «Mudou [coisa] e quase ninguém [agiu]» |
| segmentacao | 9.5 | 4.1 | 2.35 | Chama o público pelo nome: «Se você é [perfil] e [situação], pare e veja isso» |
| promessa_como | 4.2 | 4.6 | 0.93 | Promessa + método: «Como [resultado] em [prazo/passos], sem [obstáculo]» |
| erro_dor | 2.1 | 2.0 | 1.04 | Erro ou perda que o público comete: «O erro que faz [público] perder [coisa] todo mês» |
| imperativo | 1.6 | 2.0 | 0.78 | Comando curto: «Pare. [Instrução de 1 linha]» |
| historia_prova | 1.1 | 1.0 | 1.04 | Prova em 1ª pessoa: «Eu [estava mal] e [resultado] em [tempo]; veja o que mudou» |

## Chamadas para ação (último ~18% da fala)

| tipo | % top | % controle | lift |
|---|---|---|---|
| siga | 23.1 | 13.9 | 1.66 |
| comente | 14.4 | 6.9 | 2.07 |
| salve_compartilhe | 10.3 | 6.9 | 1.48 |
| direct_whats | 7.2 | 7.9 | 0.91 |
| link_bio | 1.0 | 0.5 | 2.07 |

## Legenda e hashtags (top 10%)

- Hashtags por post: 0.0 / **4.0** / 5.0; caracteres da legenda: 180.0 / **396.0** / 719.0.
- Com emoji: 57.4%; 1ª linha é pergunta: 18.1%; tem CTA: 43.4%.
- Hashtags mais frequentes: #empreendedorismo, #mei, #contabilidade, #gestaofinanceira, #negocios, #vendas, #microempreendedor, #gestao, #gestãofinanceira, #simplesnacional, #fluxodecaixa, #receitafederal, #gestaodenegocios, #empreendedorismofeminino, #liderança.

Hashtags por segmento: ver `config/playbook_viral.yaml`.

## Como o Claude usa isto

`src/criativos/sessao_claude.py` injeta `config/playbook_viral.yaml` no prompt da edição; `src/analise/legenda_hashtags.py` gera `legenda.txt`.
