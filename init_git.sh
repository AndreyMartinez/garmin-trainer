#!/usr/bin/env bash
# Inicializa el repositorio git de este proyecto.
# Correr una sola vez, desde esta carpeta:  bash init_git.sh
set -e
cd "$(dirname "$0")"

# Limpia cualquier .git a medias (requiere tus permisos de macOS)
rm -rf .git

git init
git config user.name "Raphael Martinez"
git config user.email "rmartinezvel@saviaraiz.com"
git add -A
git commit -m "Bloque 5K: extracción Garmin, generador de plan y visor de sesiones"

echo ""
echo "✅ Repo creado. Archivos versionados:"
git ls-files
echo ""
echo "Para compartir en GitHub:"
echo "  1) Crea un repo vacío en github.com (privado recomendado: contiene datos de salud)"
echo "  2) git remote add origin <URL-del-repo>"
echo "  3) git branch -M main && git push -u origin main"
