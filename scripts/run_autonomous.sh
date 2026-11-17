#!/usr/bin/env bash
# =============================================================================
# Execução headless (sem interação) de todas as specs com o Claude Code.
#
#   bash scripts/run_autonomous.sh            # modo seguro: acceptEdits + allowlist de .claude/settings.json
#   UNSAFE_SKIP_PERMISSIONS=1 bash scripts/run_autonomous.sh
#                                             # pula TODAS as permissões. Use SOMENTE em
#                                             # container/VM descartável sem segredos.
#
# Variáveis opcionais: MAX_TURNS (padrão 250), START_AT (ex.: 03), MAX_RETRIES (padrão 2)
# Requisitos: CLI `claude` autenticada no PATH.
# =============================================================================
set -uo pipefail
cd "$(dirname "$0")/.."

MAX_TURNS="${MAX_TURNS:-250}"
START_AT="${START_AT:-00}"
MAX_RETRIES="${MAX_RETRIES:-2}"
mkdir -p logs

if [[ "${UNSAFE_SKIP_PERMISSIONS:-0}" == "1" ]]; then
  PERM=(--dangerously-skip-permissions)
else
  PERM=(--permission-mode acceptEdits)
fi

[[ -d .git ]] || { git init -q && git add -A && git commit -qm "chore: pacote de specs inicial" || true; }

for i in $(seq $((10#$START_AT)) 7); do
  NN=$(printf "%02d" "$i")
  if grep -qE "^\| *SPEC_${NN} *\|[^|]*\| *DONE" docs/PROGRESS.md 2>/dev/null; then
    echo "SPEC_${NN} já DONE — pulando"; continue
  fi
  echo "=== SPEC_${NN} ==="
  claude -p "/implement-spec ${NN}" "${PERM[@]}" --max-turns "$MAX_TURNS" \
    --output-format json > "logs/claude_spec${NN}.json" 2> "logs/claude_spec${NN}.err"

  attempt=0
  until bash scripts/gate.sh "$NN" > "logs/gate_spec${NN}_outer.log" 2>&1; do
    attempt=$((attempt+1))
    if (( attempt > MAX_RETRIES )); then
      echo "SPEC_${NN}: gate continua falhando após ${MAX_RETRIES} retomadas. Veja logs/ e docs/PROGRESS.md."
      exit 1
    fi
    TAIL=$(tail -n 60 "logs/gate_spec${NN}_outer.log")
    claude -c -p "O gate da SPEC_${NN} falhou na verificação externa. Últimas linhas:
${TAIL}
Corrija seguindo o CLAUDE.md (sem enfraquecer testes), rode o gate e o spec-verifier de novo." \
      "${PERM[@]}" --max-turns "$MAX_TURNS" --output-format json >> "logs/claude_spec${NN}.json" 2>> "logs/claude_spec${NN}.err"
  done
  echo "SPEC_${NN}: gate verde."
done

bash scripts/gate.sh all && echo "PROJETO CONCLUÍDO. Leia docs/FINAL_REPORT.md e docs/HUMAN_DEPENDENCIES.md."
