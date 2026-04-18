#!/bin/bash
# record.sh — prepara el entorno y graba el GIF con vhs
# Usage: ./record.sh

set -euo pipefail

# 1. Crear entornos demo
echo "→ Creando entornos demo..."
bash tester.sh setup

# 2. Grabar
echo "→ Grabando GIF..."
vhs demo.tape

# 3. Limpiar
echo "→ Limpiando entornos demo..."
bash tester.sh cleanup

echo "✓ Listo. GIF guardado en show.gif"
