#!/bin/bash
# Abre el Editor de Vlogs en la Mac: actualiza, instala lo que falte, prende el servidor y abre el navegador.
# Lo usan "Editor de Vlogs.app", "Abrir Editor de Vlogs.command" y Claude Code ("abrí el editor de vlogs").
PUERTO=8787
URL="http://localhost:$PUERTO"
LOG="$HOME/Library/Logs/EditorDeVlogs.log"
mkdir -p "$(dirname "$LOG")"

# Las apps abiertas desde el Finder no traen el PATH de la Terminal: sumamos donde suelen estar claude, brew y python.
export PATH="$HOME/.local/bin:$HOME/.claude/local:/opt/homebrew/bin:/usr/local/bin:$HOME/.npm-global/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

aviso() { osascript -e "display notification \"$1\" with title \"Editor de Vlogs\"" >/dev/null 2>&1 || echo "$1"; }
alerta() { osascript -e "display alert \"Editor de Vlogs\" message \"$1\"" >/dev/null 2>&1 || echo "$1"; }

# Carpeta del repo: la de este script (.claude/skills/editor-de-vlogs) o ~/Claude
SKILL="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$SKILL/../../.." 2>/dev/null && pwd)"
[ -f "$REPO/.claude/skills/editor-de-vlogs/servidor.py" ] || REPO="$HOME/Claude"
SKILL="$REPO/.claude/skills/editor-de-vlogs"
if [ ! -f "$SKILL/servidor.py" ]; then
  alerta "No encuentro el proyecto en $REPO. Bajalo una vez con: git clone https://github.com/Santinodan/Claude.git ~/Claude"
  exit 1
fi

# ¿Ya esta prendido? Entonces solo abrimos el navegador.
if curl -fs "$URL/api/estado" >/dev/null 2>&1; then
  open "$URL"; exit 0
fi

aviso "Abriendo…"
cd "$REPO" && git pull --ff-only -q >>"$LOG" 2>&1   # traer lo ultimo (si falla, sigue con lo que hay)

# Dependencias (solo la primera vez tarda)
if ! command -v ffmpeg >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    aviso "Instalando ffmpeg (una sola vez, tarda unos minutos)…"; brew install ffmpeg >>"$LOG" 2>&1
  else
    alerta "Falta ffmpeg. Instalá Homebrew desde https://brew.sh y volvé a abrir la app (o pedile a Claude Code que lo instale)."
  fi
fi
if ! python3 -c "import numpy, librosa, faster_whisper" >/dev/null 2>&1; then
  aviso "Instalando librerías de Python (una sola vez)…"
  python3 -m pip install --user -q -r "$SKILL/requirements.txt" >>"$LOG" 2>&1 || \
  python3 -m pip install --user -q --break-system-packages -r "$SKILL/requirements.txt" >>"$LOG" 2>&1
fi
command -v claude >/dev/null 2>&1 || aviso "No encontré Claude Code: la app abre igual, pero Editar con Claude no va a andar."

# Prender el servidor en segundo plano y esperar a que responda
nohup python3 "$SKILL/servidor.py" --puerto $PUERTO >>"$LOG" 2>&1 &
for i in $(seq 1 40); do
  curl -fs "$URL/api/estado" >/dev/null 2>&1 && { open "$URL"; exit 0; }
  sleep 0.5
done
alerta "No pude prender el editor. Detalle en $LOG"
exit 1
