# SPEC_04 — Síntese 2.5D de fotos estáticas (deformação zero do produto)

**Objetivo:** transformar fotos de produto em clipes 1080×1920 com sensação
de movimento de câmera, **sem re-sintetizar pixels do produto** — logotipo,
rótulo e textura ficam intactos.

**Depende de:** SPEC_03. **Gate:** `bash scripts/gate.sh 04`.
**Referência:** pesquisa §“Animação de Imagens Estáticas a Custo Zero”,
ADR-003.

---

## 1. Entregáveis

### 1.1 `src/animation/depth.py`
`estimate_depth(image: np.ndarray) -> tuple[np.ndarray, str]` → mapa 0–1
(1 = perto) e nome do motor:
1. `depth-anything/Depth-Anything-V2-Small-hf` via `transformers`
   (`pipeline("depth-estimation")`), liberando o modelo da memória depois.
   **Somente o checkpoint Small** (Base/Large são CC-BY-NC — ADR-006).
2. Fallback **geométrico** (sem rede, sem pesos): profundidade radial
   centrada + saliência (bordas/contraste) — determinístico.

### 1.2 `src/animation/parallax_2_5d.py` — CLI (contrato testado)
```
python -m src.animation.parallax_2_5d --image <img> --out <dir>/parallax_move.mp4 \
       --duration 5 --fps 30 [--strength 10] [--pivot-box auto|x,y,w,h]
```
Função: `animate_static_image_2_5d(image_path, output_path, duration=5.0, fps=30, strength=None, pivot_box="auto") -> dict`.

Algoritmo normativo:
1. **Enquadrar** a foto em tela 1080×1920 com margem de segurança (~8%)
   para o deslocamento: *cover* se a proporção permitir sem cortar o
   produto; senão *contain* sobre fundo da própria foto ampliada e desfocada.
2. **Profundidade** com `estimate_depth`.
3. **PIVOT_CENTER_BOX**: `auto` = caixa do objeto saliente central (ou
   caixa central 50%×40% da tela se a saliência falhar). Profundidade de
   referência `d_p` = mediana da profundidade na caixa.
4. **Deslocamento**: para cada pixel, `disp = strength · (d − d_p) ·
   camera(t)`, com `camera(t)` em órbita suave (seno/cosseno, 1 ciclo ou
   meio ciclo na duração). Dentro da PIVOT_CENTER_BOX o deslocamento é
   **forçado a zero** (máscara com borda suavizada de 12–24 px) ⇒
   deslocamento líquido zero e deformação zero no produto.
   `strength` padrão = `PARALLAX_STRENGTH` do formato (6 a 16; o formato 2
   usa 10). Sem zoom global sobre o pivô (escala ≤ 1,02 se usar).
5. `cv2.remap` por frame; oclusões preenchidas por replicação de borda/
   inpainting simples.
6. Encode via pipe para ffmpeg: H.264, yuv420p, 30 fps CFR, **exatamente
   `round(duration·fps)` frames**.
7. Gravar ao lado do vídeo `<stem>.pivot.json`:
   `{"pivot_box": {"x","y","w","h"}, "depth_engine", "strength", "canvas": [1080,1920]}`
   (coordenadas no espaço do vídeo de saída).

### 1.3 `src/animation/optical_flow_morph.py` — CLI (contrato testado)
```
python -m src.animation.optical_flow_morph --images <a> <b> [<c> ...] --out <dir>/morph.mp4 \
       --duration 6 --fps 30 [--sway]
```
- Enquadra cada foto em 1080×1920 (mesma regra), alinha (ECC/homografia por
  ORB se útil) e interpola entre fotos consecutivas com
  `cv2.DISOpticalFlow_create(PRESET_MEDIUM)` nos dois sentidos, combinando
  os warps com peso por consistência *forward-backward* (evita
  *ghosting*). Segura ~0,6 s em cada foto real.
- `--sway`: oscilação de câmera na mão (passeio aleatório suavizado,
  translação ≤ 1,5%, rotação ≤ 0,6°).
- Exatamente `round(duration·fps)` frames, 1080×1920, yuv420p.

### 1.4 Opcional — `src/animation/zerogpu_client.py`
Cliente `gradio_client` para B-roll atmosférico no HF ZeroGPU, ativo só com
`HF_TOKEN` **e** `REELS_ENABLE_ZEROGPU=1`; contador local de quota diária
(300 s) persistido em `.cache/`; nunca chamar se `quota_restante <
duration` declarada pelo endpoint; **nunca** usar para fotos de produto.
Testes só com mocks (`tests/unit/`). Pode ficar como esqueleto documentado
se o tempo apertar (registrar no ADR-007).

### 1.5 MCP
Tool `animate_static_image_2_5d(image_path, duration=5.0, fps=30, strength=None, mode="parallax"|"morph", extra_images=None, job_id=None)`.

---

## 2. Métricas de Autoverificação

```bash
bash scripts/gate.sh 04
```
`tests/acceptance/test_spec04_animation.py`:
1. Parallax sobre `tests/fixtures/img_1.jpg` (5 s, 30 fps):
   `parallax_move.mp4` 1080×1920, `nb_frames` = 150 ± 2, `yuv420p`.
2. **Deformação zero:** recorte da PIVOT_CENTER_BOX (do `.pivot.json`) no
   frame 0 e no frame 75 ⇒ **SSIM ≥ 0,90** (tons de cinza).
3. **Anti-trapaça:** fora da caixa, diferença média absoluta entre frame 0 e
   75 > 1,0 nível de cinza (o vídeo realmente se move).
4. Morph `img_1`, `img_2`, `img_3` (6 s, 30 fps, `--sway`): 1080×1920,
   `nb_frames` = 180 ± 2, `yuv420p`, e transição gradual (maior diferença
   entre frames consecutivos < 50% da diferença entre o primeiro e o último
   frame).

## 3. Armadilhas conhecidas
- Ken Burns (zoom global) derruba o SSIM do pivô — o movimento tem de vir
  da paralaxe diferencial, não de escala.
- Entregar `nb_frames` exato exige controlar a contagem de frames escritos
  no pipe (não use `-t` sozinho com fps variável).
