# Skills de vídeo: relatório de instalação (Parte A)

Instaladas no nível do projeto (`.claude/skills/<nome>/`). Cada uma tem `ORIGEM.txt` com URL, commit fixado e resultado da auditoria.
Auditoria: leitura de SKILL.md e scripts, busca por rede, `shell=True`, `sudo`, `eval`, hooks. Nada foi executado durante a auditoria.

| # | Nome | Status | Fonte (SHA) | Licença | Observação |
|---|------|--------|-------------|---------|------------|
| 1 | /watch | INSTALADO (parcial) | bradautomates/claude-video `03ceb42` | MIT | Só `skills/watch`. Hook SessionStart NÃO instalado. Nuvem (Groq/OpenAI/Gemini) só com chave. Precisa de `yt-dlp` para URLs |
| 2 | Visual Skills | NÃO ENCONTRADO | n/d | n/d | Nome genérico; nenhuma fonte inequívoca |
| 3 | YouTube Agent | NÃO ENCONTRADO | n/d | n/d | Idem |
| 4 | Skill Creator | INSTALADO | anthropics/skills `e4bb5d9` | Apache-2.0 | Oficial. Único link externo: Google Fonts em relatório HTML |
| 5 | Video Use | INSTALADO (parcial) | browser-use/video-use `43cfc56` | MIT | Transcrição usa ElevenLabs Scribe (`ELEVENLABS_API_KEY`). Sem chave, usar a transcrição local do projeto |
| 6 | Herk Edit Kit | PENDENTE | nateherkai/herk-edit-kit | MIT (segundo listagens) | Repositório >360 MB, clone ainda não terminou. Setup oficial usa `npm run setup`, que não será rodado sem revisão |
| 7 | FFmpeg Skill | INSTALADO | kajisho5/ffmpeg-skill `bad487c` | MIT | Python stdlib, sem rede. ffmpeg 6.1.1 local OK |
| 8 | OpenChatCut | PULADO | 0xsline/OpenChatCut | AGPL | App desktop e licença AGPL; exige decisão humana (ADR-006) |
| 9 | HyperFrames | JÁ EXISTIA | (anterior à spec) | n/d | Motion graphics, fora do fluxo com pessoas |
| 10 | Remotion Skills | NÃO INSTALADO | remotion-dev/skills | n/d | Motion graphics; opcional |
| 11 | Video Shotcraft | NÃO INSTALADO | Vincentwei1021/video-shotcraft | n/d | Motion/produto; não auditado |
| 12 | Motion Skills | NÃO ENCONTRADO | n/d | n/d | Nome genérico |
| 13 | Claude Video Effects | INSTALADO (parcial) | Vibha-Ramprakash/claude-video-effects `60840ac` | MIT | 51 efeitos (não 36). Precisa de venv com mediapipe/opencv: `bash .claude/skills/video-effects/scripts/setup.sh` |
| 14 | Clipify | PULADO | n/d | n/d | Só macOS; ambiente é Linux |
| 15 | Motion Graphics | NÃO ENCONTRADO | n/d | n/d | Nome genérico |
| 16 | Add Zooms | INSTALADO | louisedesadeleer/add-zooms `34db910` | MIT | Só ffmpeg, sem rede |
| 17 | ElevenLabs Skills | INSTALADO, BLOQUEADO p/ uso | elevenlabs/skills `97478d1` | MIT | 6 skills (sound-effects, music, voice-isolator, speech-to-text, text-to-speech, setup-api-key). Exigem chave e enviam mídia à ElevenLabs |
| 18 | Pexo | BLOQUEADO | pexoai/pexo-skills | n/d | Serviço pago com chave; não instalado |
| 19 | Video Toolkit | NÃO INSTALADO | digitalsamba/claude-code-video-toolkit (provável) | n/d | Ambíguo e não edita sozinho |
| 20 | OpenMontage | PULADO | calesthio/OpenMontage | AGPL-3.0 | Conflita com o guardrail `REELS_ALLOW_AGPL`; decisão humana |

## Pendências humanas
1. `ELEVENLABS_API_KEY` (e opcionalmente `GEMINI_API_KEY`/`GROQ_API_KEY`) no `.env` para liberar itens 5, 17 e nuvem do /watch. Atenção: isso envia mídia a terceiros (CLAUDE.md regra 7).
2. `yt-dlp` para o /watch com URLs; venv do `video-effects` (comando acima).
3. Decidir sobre AGPL (OpenChatCut, OpenMontage).
4. Confirmar o que são Visual Skills, YouTube Agent, Motion Skills, Motion Graphics e Video Toolkit (nomes do carrossel sem fonte clara).
5. Herk Edit Kit: terminar o clone e auditar antes de instalar.
