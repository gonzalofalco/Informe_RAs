#!/usr/bin/env bash
set -euo pipefail

# Ejecuta el flujo principal y scripts adicionales desde un solo punto.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

if ! command -v flock >/dev/null 2>&1; then
  echo "Error: 'flock' no esta disponible en el sistema."
  echo "Instalar paquete: util-linux"
  exit 1
fi

LOCK_FILE="${RAS_LOCK_FILE:-$PROJECT_ROOT/logs/informe_ras.lock}"
LOCK_WAIT_SECONDS="${RAS_LOCK_WAIT_SECONDS:-0}"
mkdir -p "$(dirname "$LOCK_FILE")"

exec 9>"$LOCK_FILE"
if [[ "$LOCK_WAIT_SECONDS" =~ ^[0-9]+$ ]] && [[ "$LOCK_WAIT_SECONDS" -gt 0 ]]; then
  if ! flock -w "$LOCK_WAIT_SECONDS" 9; then
    echo "Otra ejecucion sigue en curso (lock: $LOCK_FILE). Se omite esta corrida."
    exit 0
  fi
else
  if ! flock -n 9; then
    echo "Otra ejecucion sigue en curso (lock: $LOCK_FILE). Se omite esta corrida."
    exit 0
  fi
fi

if [[ ! -d ".venv" ]]; then
  echo "Error: no existe .venv en $PROJECT_ROOT"
  echo "Crea el entorno con: python3 -m venv .venv"
  exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

run_step() {
  local step="$1"
  echo "\n>>> Ejecutando: $step"

  if [[ "$step" == *.py ]]; then
    if [[ -f "$step" ]]; then
      python3 "$step"
    elif [[ -f "src/$step" ]]; then
      python3 "src/$step"
    else
      echo "Error: script Python no encontrado: $step"
      exit 1
    fi
  elif [[ "$step" == *.sh ]]; then
    if [[ -f "$step" ]]; then
      bash "$step"
    elif [[ -f "scripts/$step" ]]; then
      bash "scripts/$step"
    else
      echo "Error: script shell no encontrado: $step"
      exit 1
    fi
  else
    # Fallback: permite comandos arbitrarios.
    eval "$step"
  fi
}

# 1) Flujo principal actual.
run_step "login_telecentro.py"

# 2) Scripts extra pasados por argumento.
for extra in "$@"; do
  run_step "$extra"
done

echo "\nOK: flujo completo finalizado."
