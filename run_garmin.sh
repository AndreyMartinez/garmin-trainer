#!/bin/bash
# Ejecuta garmin.js con el PATH correcto (launchd trae un PATH mínimo)
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
NODE="$(command -v node)"
if [ -z "$NODE" ]; then
  echo "$(date) - ERROR: no se encontró node en el PATH" >> garmin_cron.log
  exit 1
fi
echo "$(date) - ejecutando garmin.js" >> garmin_cron.log
"$NODE" garmin.js >> garmin_cron.log 2>&1
