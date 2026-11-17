#!/usr/bin/env bash
# =============================================================================
# Gate de aceitação por spec. Uso:  bash scripts/gate.sh NN   |   bash scripts/gate.sh all
# - Cumulativo: o gate NN roda também os testes de aceitação das specs < NN
#   (proteção contra regressão).
# - Exit 0 = spec liberada para o spec-verifier. Qualquer outro = corrigir.
# - NÃO EDITE este arquivo para "fazer passar" (contrato, ver CLAUDE.md §1.5).
# =============================================================================
set -uo pipefail
cd "$(dirname "$0")/.."

TARGET="${1:-}"
if [[ -z "$TARGET" ]]; then echo "uso: bash scripts/gate.sh <00..07|all>"; exit 2; fi

if [[ -x ".venv/bin/python" ]]; then PY=".venv/bin/python"; else PY="$(command -v python3 || command -v python)"; fi
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"
export REELS_WORKSPACE="${REELS_WORKSPACE:-./workspace}"
# Testes de aceitação nunca dependem de nuvem: força o caminho local por padrão.
export REELS_OFFLINE="${REELS_OFFLINE:-1}"
export REELS_ALLOW_PLACEHOLDER_AUDIO="${REELS_ALLOW_PLACEHOLDER_AUDIO:-1}"
mkdir -p logs
LOG="logs/gate_${TARGET}_$(date +%Y%m%d_%H%M%S).log"

declare -A TESTS=(
  [00]="tests/acceptance/test_spec00_bootstrap.py"
  [01]="tests/acceptance/test_spec01_mcp.py"
  [02]="tests/acceptance/test_spec02_router.py"
  [03]="tests/acceptance/test_spec03_vision.py"
  [04]="tests/acceptance/test_spec04_animation.py"
  [05]="tests/acceptance/test_spec05_editing.py"
  [06]="tests/acceptance/test_spec06_director.py"
  [07]="tests/acceptance/test_spec07_e2e.py"
)

run() { echo "+ $*" | tee -a "$LOG"; "$@" 2>&1 | tee -a "$LOG"; return "${PIPESTATUS[0]}"; }

if [[ "$TARGET" == "all" ]]; then N=7; else N=$((10#$TARGET)); fi
if (( N < 0 || N > 7 )); then echo "spec inválida: $TARGET"; exit 2; fi

# Pré-requisitos por nível
echo "+ $PY -m src.core.doctor --json" | tee -a "$LOG"
"$PY" -m src.core.doctor --json >> "$LOG" 2>&1 || { echo "GATE ${TARGET}: doctor falhou (veja $LOG)" | tee -a "$LOG"; exit 1; }
if (( N >= 1 )); then
  run "$PY" tests/fixtures/generate_test_media.py || { echo "GATE ${TARGET}: geração de fixtures falhou" | tee -a "$LOG"; exit 1; }
fi

FILES=()
for i in $(seq 0 "$N"); do
  k=$(printf "%02d" "$i")
  FILES+=("${TESTS[$k]}")
done
if [[ "$TARGET" == "all" && -d tests/unit ]]; then FILES+=("tests/unit"); fi

run "$PY" -m pytest -q -p no:cacheprovider "${FILES[@]}"
STATUS=$?
echo "GATE ${TARGET}: exit ${STATUS} (log: ${LOG})" | tee -a "$LOG"
exit "$STATUS"
