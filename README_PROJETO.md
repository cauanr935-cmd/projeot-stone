# Impulso Stone Reels MCP

Servidor MCP e CLI offline-first para transformar vídeos, fotos e áudios de
microempreendedores em Reels verticais H.264/AAC prontos para revisão e
publicação. O projeto **não publica** nas redes sociais.

## Requisitos

- Python 3.11 ou 3.12
- FFmpeg + ffprobe com `libx264`, `libass` e `loudnorm`
- Linux/macOS (Windows pode usar WSL)

## Instalação

Na raiz deste diretório:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[core,dev]'
.venv/bin/python -m src.core.doctor --write-report
```

O caminho offline não baixa pesos de ML. Templates, música procedural,
detecção geométrica de profundidade e animação local funcionam sem chaves.
Gere fixtures sintéticas para experimentar:

```bash
.venv/bin/python tests/fixtures/generate_test_media.py
```

## CLI

Escolha explicitamente um dos cinco formatos; sem `--format`, o diretor
pergunta no terminal:

```bash
.venv/bin/python -m src.main --input-dir tests/fixtures/mixed --format 2 \
  --out output/meu_reel.mp4 --business-name 'Doces da Ana' --product 'bolo de cenoura'
```

O comando cria artefatos em `workspace/jobs/<job-id>/` e só termina com
sucesso se `tests/verify_final_reel.py` aprovar o arquivo. `--keep-source-audio`
mistura o áudio original em volume reduzido. Em modo offline, se não houver
voz local instalada, o tier de teste `placeholder_tone` é usado e **não pode
ser renderizado comercialmente** (`REELS_COMMERCIAL=0` é destinado somente a
testes). Com internet e `edge-tts`, a locução usa a voz selecionada no plano;
se o serviço falhar, o placeholder não é autorizado em render comercial.
Revise a pendência jurídica de edge-tts antes de publicar.

## Interface web local

Para gerar um Reel pela interface, inicie o servidor local:

```bash
.venv/bin/python -m src.web_app
```

Abra `http://127.0.0.1:8000`, selecione vídeos do computador (MP4, MOV, M4V,
WebM ou MKV) ou cole um link direto por linha, escolha o formato e clique em
**Gerar Reel**. A interface consulta o estado do processamento e oferece o
player para pré-visualizar o MP4 antes do download. Pode selecionar qualquer
quantidade de vídeos, incluindo
uma pasta inteira e suas subpastas; o navegador pedirá acesso à pasta
selecionada. Cada arquivo pode ter até 500 MB, sujeito ao espaço livre em
disco. Links de páginas do YouTube, Drive e redes sociais não são aceitos. O servidor
só escuta no localhost, recusa destinos privados e não segue redirecionamentos.
Uploads, entradas e resultados ficam em `workspace/`.
O carregamento opcional de chaves é feito pelo `.env` local, que não deve ser
compartilhado. Se a porta 8000 estiver ocupada, inicie com
`REELS_WEB_PORT=8766 .venv/bin/python -m src.web_app` e abra
`http://127.0.0.1:8766`.

O formulário inclui contexto/mensagem principal, roteiro opcional e escolhas
independentes de locução, música e áudio original. Se houver contexto sem
roteiro separado, o texto do contexto será usado literalmente como locução
quando a fala estiver ativa. O pipeline não interpreta semanticamente as
cenas; descreva os detalhes importantes e confira o vídeo gerado antes de usar.
Com a música ativada, também é possível enviar uma trilha própria em MP3, WAV,
M4A, AAC, OGG ou FLAC (até 100 MB e 15 minutos). O editor prioriza o trecho de
maior energia que caiba no Reel e alinha os cortes às batidas detectadas;
sem arquivo enviado, usa a trilha automática. A análise não entende o
significado das cenas nem verifica direitos autorais: use uma faixa que você
tenha autorização para publicar.

## Servidor MCP

O arquivo `.vscode/mcp.json` registra o servidor para o VS Code/Copilot por
stdio e carrega as chaves opcionais do `.env` local (que não é versionado).
Abra esta pasta do projeto no VS Code, execute **MCP: List Servers** pela
paleta de comandos, selecione `impulso-stone-reels` e escolha **Start**.
Depois, abra o Copilot Chat no modo **Agent**; as ferramentas MCP estarão
disponíveis na sessão. O `.mcp.json` da raiz também atende clientes Copilot
que usam a configuração portátil.

Para Claude Desktop, copie a configuração de `config/mcp.example.json` e
substitua os caminhos de exemplo pelos caminhos absolutos da instalação. O
transporte HTTP de desenvolvimento fica restrito a `127.0.0.1:8765`:

```bash
.venv/bin/python -m src.mcp_server --http
```

Resources publicados: catálogo de formatos, perfis CNAE, status do roteador e
resumo da análise por job. Tools incluem análise/reframe, animação, locução,
legendas, plano criativo e render. O guardrail de licenças bloqueia ativos
não comerciais antes de qualquer render comercial.

## Verificação

```bash
bash scripts/gate.sh 07
bash scripts/gate.sh all
```

Os gates de aceitação não acessam provedores externos e geram seus próprios
fixtures. Antes de usar qualquer Reel comercial, leia
[`docs/HUMAN_DEPENDENCIES.md`](docs/HUMAN_DEPENDENCIES.md), especialmente as
revisões jurídicas e a validação de CNAE/roteiros.

## Base de Reels para MPEs (case de análise)

Base pública de **2.715 Reels de 126 perfis** (Instagram, coleta de 17–18/11/2026 via Apify), com ranking por
`score_relativo` e análise multimodal do top 10% (250 Reels). Detalhes em `docs/base_de_dados.md` e
`docs/ANALISE_TOP10.md`; decisões em ADR-009.

Reproduzir ou ampliar a base (exige `APIFY_TOKEN` no `.env`; a pasta `dados/` não é versionada):

```bash
.venv/bin/python -m src.coleta.descoberta --hashtags mei,abrirmei --por-hashtag 40 --verificar 70
.venv/bin/python -m src.coleta.instagram --perfis config/perfis_loteN.csv --prefixo instagram_loteN \
  --so-reels --limite 40 --max-usd 3 --sem-midia --confirmo-custo
.venv/bin/python -m src.base.unificar --lotes instagram,...,instagram_loteN
.venv/bin/python -m src.ranking.ranking && .venv/bin/python -m src.base.documentar
.venv/bin/python -m src.analise.baixar_top && .venv/bin/python -m src.analise.manifesto \
  && .venv/bin/python -m src.analise.features && .venv/bin/python -m src.analise.classificar
```

Limite conhecido: o crédito gratuito da Apify (US$ 5/mês) limita o volume; vídeos e miniaturas servem só para
análise interna e não devem ser redistribuídos.

## Tutorial com Claude e exemplos

- [`docs/TUTORIAL_CLAUDE.md`](docs/TUTORIAL_CLAUDE.md): passo a passo com o Claude, o MCP e as skills instaladas.
- [`exemplos/README.md`](exemplos/README.md): 18 exemplos com prompts prontos (fonte: `exemplos/catalogo.yaml`; valide com `python scripts/exemplos.py --check`).
