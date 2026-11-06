#!/bin/bash
# Genera FrutillaFinanzas.xcodeproj a partir de project.yml.
# Si falta XcodeGen, lo instala con Homebrew.
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v xcodegen >/dev/null 2>&1; then
  if ! command -v brew >/dev/null 2>&1; then
    echo "Falta Homebrew. Instalalo desde https://brew.sh y volvé a correr este script." >&2
    exit 1
  fi
  echo "Instalando XcodeGen con Homebrew..."
  brew install xcodegen
fi

xcodegen generate
echo "Listo. Abrí FrutillaFinanzas.xcodeproj con Xcode."
[ "${1:-}" = "--abrir" ] && open FrutillaFinanzas.xcodeproj || true
