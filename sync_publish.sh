#!/usr/bin/env bash
# Garmin Recovery Sync publishing step extracted without changing semantics.
# This script is intended to run ONLY from the Sync workflow checkout.
set -euo pipefail

git config user.name "Garmin Recovery Bot"
git config user.email "actions@github.com"

git add recovery.csv wellness.json activities.csv activities.json daily_summary.json weekly_summary.json intervals_status.json

if git diff --cached --quiet; then
  echo "Sin cambios de Intervals que publicar."
  exit 0
fi

git commit -m "Actualizar recuperación y análisis profesional"

for attempt in 1 2 3 4 5; do
  echo "Intento de publicación $attempt/5"

  if ! git pull --rebase origin main; then
    echo "Conflicto al integrar cambios remotos. No se sobrescriben datos." >&2
    git rebase --abort || true
    exit 1
  fi

  if git push origin HEAD:main; then
    echo "Datos de Intervals publicados correctamente."
    exit 0
  fi

  sleep $((attempt * 3))
done

echo "No se pudo publicar después de cinco intentos." >&2
exit 1
