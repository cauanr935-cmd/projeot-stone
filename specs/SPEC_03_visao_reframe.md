# SPEC_03 — Visão computacional: normalização CFR, cenas, reframe 9:16 e Hook Finder

**Objetivo:** transformar um vídeo bruto local (normalmente VFR, 16:9, de
celular) em material analisado e verticalizado: CFR, lista de cenas, vídeo
1080×1920 com câmera virtual e ganchos pontuados para os 3 primeiros segundos.

**Depende de:** SPEC_02 (ASR via router). **Gate:** `bash scripts/gate.sh 03`.
**Referência:** pesquisa §“Pipeline de Análise Multimodal”, §“Deteção de
Cenas e Reenquadramento Vertical 9:16”, §“Ciência da Retenção”.

---

## 1. Entregáveis

### 1.1 `src/vision/normalizer.py`
`normalize_to_cfr(input: Path, output: Path, fps: int = 30) -> dict`
- `ffprobe` para detectar VFR (`r_frame_rate != avg_frame_rate`) e
  diferença de `start_time` entre áudio e vídeo.
- `ffmpeg ... -fps_mode cfr -r 30` (equivalente moderno de `-vsync cfr`),
  áudio com `aresample=async=1:first_pts=0` e compensação do offset inicial.
- Retorna `{"was_vfr": bool, "fps": 30, "audio_offset_s": float, "path": str}`.

### 1.2 `src/vision/scene_detector.py`
`detect_scenes(video: Path, out_csv: Path, downscale_factor: int = 2, min_scene_len: str = "0.6s") -> list[dict]`
- PySceneDetect com `ContentDetector` (pesos `1.0 0.5 1.0 0.2`, limiar 32) +
  `AdaptiveDetector` (`min_scene_len="0.6s"`), `downscale_factor=2`.
  Unir os pontos de corte dos dois (deduplicar cortes a < 0,3 s).
- `scenes.csv` com cabeçalho exato `scene,start_s,end_s,start_frame,end_frame`
  e `scene_stats.csv` (métricas por frame).
- Fallback se PySceneDetect não importar: `ffmpeg -vf "select='gt(scene,0.3)',showinfo"`.

### 1.3 `src/vision/reframe_9_16.py`
`reframe_to_vertical(video: Path, output: Path, preset: str = "talking_head", strategy: str = "auto", scenes: list | None = None) -> dict`
- Saída **1080×1920, 30 fps CFR, H.264 yuv420p, AAC**.
- Cadeia de detecção de sujeito (primeira disponível e permitida):
  `ultralytics yolo11n-seg + ByteTrack` (só com `REELS_ALLOW_AGPL=1`) →
  `mediapipe` (rosto/pose) → `OpenCV Haar` (incluso no opencv) →
  saliência/energia de movimento (diferença entre frames) → centro.
- Estratégia **TRACK**: centro do recorte por cena, trajetória suavizada
  (EMA ou Savitzky–Golay, velocidade máxima de pan limitada), zoom dentro do
  intervalo do preset (`talking_head` 1.05–1.85, `cars` 1.00–1.30, `movie`
  1.00–1.30 — ler de `config/formats.yaml` quando vier do plano).
- Estratégia **LETTERBOX**: quando os sujeitos estão espalhados (> 60% da
  largura) ou nenhum sujeito confiável — fundo = o próprio vídeo ampliado e
  desfocado preenchendo 1080×1920, primeiro plano escalado para largura 1080.
- Retorna `{"path", "strategy": "TRACK"|"LETTERBOX"|"CENTER", "detector", "zoom_range"}`.

### 1.4 `src/vision/hook_finder.py`
`score_hooks(video: Path, scenes: list, transcript: dict | None = None, vlm_scores: dict | None = None) -> list[dict]`

Candidatos: janelas de 3–5 s começando em cada início de cena e a cada 1 s.
Pontuação composta (a fórmula original era imagem não recuperável no
documento; esta é a forma normativa desta spec — registrar no ADR-004):

```
S(c_i) = wA·A_i + wF·F_i·(1 − E_i) + wL·L_i + wV·V_i
pesos padrão: wA=0.35, wF=0.30, wL=0.15, wV=0.20  (renormalizar se faltar componente)
A_i  = média de librosa.onset.onset_strength na janela, normalizada 0–1 entre candidatos
F_i  = presença de rosto/sujeito no primeiro frame da janela (0–1, cadeia de detectores)
E_i  = entropia visual do fundo no primeiro frame (entropia de Shannon do histograma
       de cinza ou densidade de bordas, normalizada 0–1) — baixa entropia = melhor
L_i  = pista lexical nas palavras da transcrição (2ª pessoa "você", números, imperativos), 0–1
V_i  = nota do VLM (router.describe_images) para "produto em ação", 0–1, se disponível
```
Retorna lista ordenada por `score` desc: `{"start","end","score","components":{"A","F","E","L","V"},"weights"}`.
As 5 chaves de `components` estão **sempre presentes**; componente
indisponível = `null` (e seu peso é redistribuído em `weights`). `score`
fica em `[0, 1]`.

### 1.5 `src/vision/pipeline.py` — CLI (contrato testado)
```
python -m src.vision.pipeline --input <video> --job-dir <dir> [--preset talking_head] [--transcribe auto|off]
```
Gera no job dir: `normalized.mp4`, `scenes.csv`, `scene_stats.csv`,
`output_9_16.mp4`, `transcript.json` (se ASR rodou; mídia do usuário ⇒
`contains_sensitive_data=True`) e `multimodal_summary.json`:
```json
{
  "job_id": "…",
  "source": {"path": "…", "width": 1920, "height": 1080, "duration_s": 24.1, "was_vfr": true},
  "normalized": {"path": "…/normalized.mp4", "fps": 30},
  "scenes": [{"index": 0, "start": 0.0, "end": 6.2}],
  "transcript": {"engine": "…", "segments": []} ,
  "hooks": [{"start": 4.0, "end": 7.0, "score": 0.71, "components": {…}, "weights": {…}}],
  "selected_hook": {"start": 4.0, "end": 7.0, "score": 0.71},
  "reframe": {"path": "…/output_9_16.mp4", "strategy": "TRACK", "detector": "haar"},
  "silences": [[1.2, 2.0]],
  "created_at": "ISO-8601"
}
```

### 1.6 MCP
- Tools: `extract_multimodal_hooks(input_path, job_id=None, preset="talking_head")`
  (roda o pipeline, valida o caminho contra Roots, emite
  `notifications/resources/updated` para o summary quando possível) e
  `auto_reframe_vertical_9_16(input_path, preset="talking_head", job_id=None)`.
- Resources: `stone-media://jobs/{job_id}/analysis_summary` (real),
  `stone-media://jobs/{job_id}/scenes.csv`,
  `stone-media://jobs/{job_id}/transcript.json`.

---

## 2. Métricas de Autoverificação

```bash
bash scripts/gate.sh 03
```
`tests/acceptance/test_spec03_vision.py` roda o pipeline sobre
`tests/fixtures/sample_raw.mp4` e verifica com `ffprobe`:
1. `normalized.mp4`: `r_frame_rate == avg_frame_rate`.
2. `output_9_16.mp4`: `width == 1080`, `height == 1920`,
   `r_frame_rate == avg_frame_rate`, `h264`, `yuv420p`, com áudio, duração
   igual à do normalizado ± 0,25 s.
3. `scenes.csv` com o cabeçalho exato e ≥ 2 cenas.
4. `multimodal_summary.json`: ≥ 1 gancho com `0 ≤ score ≤ 1` e
   `2.5 ≤ end − start ≤ 5.05`; `selected_hook` presente; `reframe.strategy`
   ∈ {TRACK, LETTERBOX, CENTER}.

## 3. Armadilhas conhecidas
- Não aplique punch-in/zoom de jump-cut aqui (é SPEC_05, sobre o 9:16).
- Renderizar crop dinâmico frame a frame via OpenCV + pipe para ffmpeg é
  aceitável; mantenha o áudio do normalizado (mux no final) para não perder
  sincronia.
- `-vsync` está obsoleto em ffmpeg recente; use `-fps_mode`.
