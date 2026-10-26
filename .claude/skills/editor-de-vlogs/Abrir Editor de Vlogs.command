#!/bin/bash
# Doble clic en la Mac: levanta el servidor local y abre el Editor de Vlogs en el navegador.
cd "$(dirname "$0")"
PUERTO=8787
if ! command -v ffmpeg >/dev/null; then echo "Falta ffmpeg. Instalalo con:  brew install ffmpeg"; read -n1; exit 1; fi
if ! command -v claude >/dev/null; then echo "Aviso: no encuentro Claude Code (comando 'claude'). La app abre igual, pero el boton Editar no va a andar."; fi
( sleep 1.5; open "http://localhost:$PUERTO" ) &
python3 servidor.py --puerto $PUERTO
