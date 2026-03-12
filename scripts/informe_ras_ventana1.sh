#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

export RAS_SPLIT_ONLY_WINDOW=window1
export RAS_SPLIT_OUTPUT_DIR=downloads/divididos/window1
./scripts/informe_ras.sh dividir_filtrados_por_horario.py
