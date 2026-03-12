#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

# Carga configuracion local si existe
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

TO="${MAIL_TO:-${1:-}}"
CC="${MAIL_CC:-}"
BCC="${MAIL_BCC:-}"
FROM="${MAIL_FROM:-}"
SUBJECT="${MAIL_SUBJECT:-Test Postfix Relay $(date +%F_%T)}"
BODY="${MAIL_BODY:-Prueba automatica de envio usando relay [10.190.89.55]:25}"

if [[ -z "$TO" ]]; then
  echo "Falta destinatario. Configura MAIL_TO en .env o pasalo como primer argumento."
  echo "Uso: $0 destino@email"
  exit 1
fi

MAIL_ARGS=(-s "$SUBJECT")

if [[ -n "$CC" ]]; then
  MAIL_ARGS+=( -a "Cc: $CC" )
fi

if [[ -n "$BCC" ]]; then
  MAIL_ARGS+=( -a "Bcc: $BCC" )
fi

if [[ -n "$FROM" ]]; then
  MAIL_ARGS+=( -r "$FROM" )
fi

echo "$BODY" | mail "${MAIL_ARGS[@]}" "$TO"
echo "Mail enviado a TO=$TO CC=$CC BCC=$BCC (revisar logs/cola para confirmacion final)."
