# SPEC_05 — Jump-cuts calibrados (AST), MIR/ducking e legendas karaoke `.ass`

**Objetivo:** automatizar a montagem rítmica com os parâmetros de retenção
de Dost & Huang (2026), sincronia com batidas, ducking da trilha e legendas
dinâmicas palavra a palavra.

**Depende de:** SPEC_04. **Gate:** `bash scripts/gate.sh 05`.
**Referência:** pesquisa §“Calibração Matemática de Jump-Cuts”,
§“Arquitetura do Motor de Edição Local”, §“Implementação Prática / 3”,
ADR-004.

---

## 1. Entregáveis

### 1.1 `src/editing/jumpcuts.py`
```python
build_ast_calibrated_jumpcuts(video_path: Path, output_path: Path, cut_style: str = "seamless",
                              noise_db: int = -32, min_silence_dur: float = 0.40,
                              punch_in: bool = True) -> dict
# -> {"output","segments":[[st,en],...],"junctions_s":[...],"pad","input_duration",
#     "output_duration","removed_seconds","audio_fades": int}
plan_pattern_interrupts(duration_s: float, target_cuts_per_sec: float,
                        existing_cuts_s: list[float], min_gap_s: float = 1.2) -> list[float]
```
CLI: `python -m src.editing.jumpcuts --input <9x16.mp4> --out <mp4> --style seamless|overlapping [--noise-db -32] [--min-silence 0.4]`.

Regras normativas:
- Passagem rápida de detecção **só no áudio**:
  `ffmpeg -hide_banner -nostats -vn -i in -af silencedetect=noise=-32dB:d=0.4 -f null -`
  (limiares por fonte: −32 dB/0,4 s celular; −45/0,5 estúdio; −50/0,25 TTS).
- `PAD` lido de `config/formats.yaml` (`seamless` 0,090 s; `overlapping`
  0,015 s). Inverter silêncios em segmentos de fala com o PAD de cada lado.
- **Corrigir os bugs da implementação de referência:** (a) incluir o trecho
  de fala **depois do último silêncio** até o fim do arquivo; (b) tratar
  silêncio no início; (c) descartar segmentos < 0,18 s; (d) o punch-in
  (`scale=1166:2074,crop=1080:1920` ≈ 1,08) só é válido sobre entrada 9:16 —
  validar a resolução de entrada.
- Áudio cortado no **milissegundo exato** com `afade` de 15 ms na entrada e
  na saída de cada segmento; vídeo alinhado ao frame mais próximo com
  **difusão do erro** (o arredondamento de um segmento é compensado no
  próximo) para que a dessincronia não acumule.
- Punch-in alternado 1,00 ↔ 1,08 a cada junção; últimos 5 s sem punch-in.
- `plan_pattern_interrupts`: devolve instantes extras de corte (punch-in/
  B-roll) para que `len(existing ∪ extras) ≈ round(target · duration)`
  (±1), respeitando `min_gap_s`. Usado pela SPEC_07 para atingir a
  frequência do formato.

### 1.2 `src/editing/beat_sync.py` e `src/editing/music.py`
```python
extract_beats(audio_path: Path) -> dict          # {"bpm","beats":[s],"downbeats":[s],"engine"}
snap_to_beats(times_s: list[float], beats_s: list[float], max_shift_s: float = 0.12) -> list[float]
duck_music_under_voice(music_path: Path, voice_path: Path, out_music_path: Path,
                       ducking_db: float = -14) -> dict   # grava a TRILHA já atenuada (sem a voz)
generate_procedural_music(out_wav: Path, bpm: int = 120, duration_s: float = 45, seed: int = 0) -> dict
```
- Padrão: **librosa** (`beat_track` + downbeats estimados a cada 4 batidas,
  fase escolhida pela maior energia de onset). madmom/BeatNet/Essentia só se
  o guardrail permitir (madmom models = não comercial; Essentia = AGPL).
- Ducking: envelope de atividade vocal (VAD do Silero se instalado; senão
  RMS com limiar) aplicado à trilha (ou `sidechaincompress`), atenuando
  ≥ 6 dB durante a voz, com ataque/soltura suaves (≥ 50 ms / ≥ 200 ms).
- `generate_procedural_music`: trilha própria (kick em todo tempo, caixa nos
  tempos 2 e 4, acorde simples), BPM exato, licença do projeto
  (`license_key: procedural-music`). Grava também em `assets/audio_cc0/`
  uma faixa padrão de 45 s a 100 BPM e uma a 120 BPM se não existirem.

### 1.3 `src/editing/subtitles_ass.py`
```python
generate_karaoke_ass_subtitles(words_or_segments: list, ass_output_path: Path,
                               hook_overlay: str | None = None) -> dict
# aceita lista plana [{"word","start","end"}] ou segments do WhisperX com "words"
# -> {"path","events": int,"frame_zero_words": int,"mode": "karaoke"|"hook_then_karaoke"}
```
- `pysubs2`, `PlayResX=1080`, `PlayResY=1920`, estilo **`ImpulsoKaraoke`**
  (fonte Montserrat ExtraBold de `assets/fonts/` ou fallback, tamanho 68,
  branco, contorno 4,5, sombra 2, alinhamento centro, `marginv=350`).
- Blocos de **no máximo 4 palavras**; um evento por palavra ativa com a tag
  `{\c&H34C9FC&\fscx112\fscy112}` na palavra ativa e reset depois; texto em
  maiúsculas.
- **Frame Zero (0–3000 ms):** no máximo **5 palavras distintas** visíveis.
  Se a fala tiver mais de 5 palavras nesse intervalo, exibir um evento de
  estilo **`ImpulsoHook`** com `hook_overlay` (≤ 5 palavras) de 0 a 3000 ms
  e iniciar o karaoke em 3000 ms (`mode="hook_then_karaoke"`). A fala
  continua audível.
- Teto duro de leitura: nenhum evento com menos de 100 ms (≤ 10 palavras/s);
  palavras mais rápidas são agrupadas. A meta 5–10 palavras/s é suave
  (registrar no ADR-004 que fala natural PT-BR ≈ 2,5–3,5 palavras/s).

### 1.4 MCP
Tool `generate_karaoke_ass_subs(words_json_path | job_id, hook_overlay=None)`.

---

## 2. Métricas de Autoverificação

```bash
bash scripts/gate.sh 05
```
`tests/acceptance/test_spec05_editing.py` gera sua própria entrada 9:16
(12 s, “fala” = tom de 440 Hz em rajadas, pausas de ~1 s com *room tone* a
≈ −48 dBFS) e verifica:
1. Duração pós-corte **estritamente menor** que a original nos dois estilos,
   e `overlapping` < `seamless`.
2. Dessincronia final |duração vídeo − duração áudio| ≤ 40 ms.
3. **Sem cliques (métrica numérica):** em cada junção (`junctions_s`), o
   menor RMS em janelas de 2 ms dentro de ±25 ms cai abaixo de 50% do RMS do
   *room tone* de referência (40–80 ms antes da junção) — prova de que há
   micro-fade e não emenda seca.
4. `plan_pattern_interrupts(30, 0.517, [])` devolve 16 ± 1 cortes com
   espaçamento ≥ 1,2 s.
5. Trilha procedural a 120 BPM ⇒ `extract_beats` estima 120 ± 4 (ou oitava
   60 ± 2 / 240 ± 8); downbeats ⊂ beats.
6. Ducking: RMS da trilha atenuada durante a voz ≥ 6 dB abaixo do RMS fora
   da voz.
7. `.ass` via `pysubs2.load()`: `PlayResX == 1080`, `PlayResY == 1920`;
   eventos `ImpulsoKaraoke` com ≤ 4 palavras; palavras distintas em eventos
   que começam antes de 3000 ms ≤ 5 (inclusive no caso de fala rápida, que
   deve ativar `hook_then_karaoke`); nenhum evento < 100 ms.

## 3. Armadilhas conhecidas
- `concat` com segmentos de áudio e vídeo de durações diferentes desalinha
  tudo depois da junção — por isso a difusão do erro.
- `afade` com `st` calculado sobre a duração do **segmento**, não do arquivo.
- AAC adiciona *priming*; meça junções com tolerância (o teste usa ±25 ms).
- **Verificado ao montar este pacote:** o punch-in da pesquisa
  (`scale=1166:2074,crop=1080:1920`) gera SAR 9333:9328 e o filtro `concat`
  recusa o grafo (“parameters do not match”). Adicione `setsar=1` em
  **todos** os ramos de vídeo antes do `concat`.
