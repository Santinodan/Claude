---
name: editor-de-vlogs
description: Edita los vlogs de Snati de punta a punta a partir de la carpeta del dia y su _edicion/vlog.json - escanea clips DJI (D-Log / D-Log 2 / Rec709), transcribe con Whisper, arma la historia (teaser, charla, montajes, cierre), saca silencios, muletillas y correcciones, aplica LUT con intensidad, barras, musica cortada en beat con fades, subtitulos y titulo neon, y exporta Vlog_<titulo>_vN.mp4 a -14 LUFS sin pisar versiones. Usar SIEMPRE que pidan editar un vlog ("edita el vlog", "editá el vlog", "arma el vlog del dia", "saca una version", "aplica las notas de revision", "rehace el vlog"), cuando llegue una ruta a vlog.json o a una carpeta _edicion, o cuando la app Editor de Vlogs lance /editor-de-vlogs.
---

# Editor de Vlogs

Snati elige en la app (o en `vlog.json`) titulo, looks, barras, musica, textos. Vos (Claude) armas la
historia con criterio y los scripts hacen lo mecanico. Contrato de datos: `references/vlog_json.md`.
Reglas de estilo sacadas de vlogs de referencia: `references/analisis_referencias.md`.

Entrada tipica: `/editor-de-vlogs <ruta>/_edicion/vlog.json [pedido opcional]`.
Hablar en espanol rioplatense, corto. Al final: link/ruta del mp4, duracion, que se hizo y dudas.

## Como correr los scripts

Siempre `python3 .claude/skills/editor-de-vlogs/scripts/edicion/<script>.py ...` parado en el repo
(sin `cd ... &&`: la app solo habilita `python3 *`, `ffmpeg *`, `ffprobe *`, `ls *`, `mkdir *`).
Cada script imprime `PASO <etapa> i/n` y escribe `_edicion/progreso.log`.
**transcribir y render pueden tardar mas de 10 min** con material largo: correrlos en segundo plano
(`run_in_background`) y seguir `_edicion/progreso.log` con Read hasta ver `FIN OK` o `FIN ERROR`.
Si falta algo: `pip3 install -r .claude/skills/editor-de-vlogs/requirements.txt` y `brew install ffmpeg`.

## Flujo (primera version)

1. **Leer** `vlog.json` (titulo = direccion del video, `historia.notas`, pedido del usuario).
2. **Escanear**: `escanear.py <vlog.json>` → actualiza `material.clips` (respeta perfil/broll/descartado
   que ya haya tocado Snati). El perfil es una adivinanza: si hay clips `desconocido` o dudosos, avisar.
3. **Transcribir**: `transcribir.py <vlog.json>` (cache por clip; solo hace lo nuevo).
   Deja `_edicion/transcripcion.txt`: frases con tiempos del clip y `!!` en posibles correcciones.
4. **Historia (criterio tuyo)**: leer `transcripcion.txt` y escribir `_edicion/historia.json`
   (formato en `references/historia_json.md`):
   - Teaser 15–30 s (`historia.teaser.duracion_s`) si `historia.teaser.activo`: 5–12 planos de los
     mejores momentos visuales (montaje/b-roll) + como mucho 1 frase gancho con `audio: "voz"`
     que adelante el titulo. Nada que arruine el final.
   - Charla en el orden de la carpeta (Snati ya ordena), cortando lo que no sirve al titulo.
   - Montajes de 10–60 s entre bloques (cambios de lugar/momento) con b-roll y clips sin habla.
   - Cierre: la ultima reflexion/despedida.
   - `quitar`: arranques falsos y correcciones ("no, perdon...", frase repetida: quedarse con la
     ultima version buena), cosas que no van. Revisar cada `!!` y decidir con el contexto.
   - `lugar`/`hora` al arrancar bloques nuevos si `historia.capitulos_lugar_hora`.
5. **Plan**: `plan.py <vlog.json>` → `_edicion/plan.json` (lo mecanico: silencios >
   `cortes.silencio_max_s`, muletillas sueltas, punch-in 1.0/1.12 alternado, cortes en beat 1/2/4/8,
   mapa de musica con fades, todo a frames). Leer el resumen y los `AVISO`.
6. **Render**: `render.py <vlog.json> --preview` (960x540 rapido) si `exportar.preview` o si es la
   primera version; la final sin `--preview`. Hace LUT por perfil con % de intensidad, barras
   (`color.barras`: `todo` o solo `montajes`), voz emparejada, ambiente bajo en montajes, musica fuerte
   en montajes y nada/baja en charla (`musica.en_charla`), subtitulos chicos blancos, titulo de
   episodio rojo neon, lugar/hora y master a `exportar.lufs` (-14) con pico <= -1 dBTP.
   Escribe `_edicion/Vlog_<titulo>_vN.mp4` (N siguiente libre) y lo agrega a `estado.versiones`.
   Pasar `--nota "que cambio"`.
7. **Chequear** antes de entregar: duracion razonable (max 50 min), ver 2–3 fotogramas
   (`ffmpeg -ss T -i video -frames:v 1 x.jpg` + Read) del teaser, una charla y un montaje.

## Revisiones (re-ejecuciones)

- Nunca pisar ni borrar versiones ni material de Snati. Cada render es una version nueva.
- Notas en `revision.notas` con `hecha: false` (ej. `{"tc": "02:14", "texto": "cortar antes"}`):
  el `tc` es del video de la ultima version. Para ubicarlo:
  `plan.py <vlog.json> --tc 02:14 --version N` → dice clip, tiempo del clip y texto.
  Aplicar cada nota editando `historia.json` (mover entrada/salida, sumar a `quitar`, cambiar orden,
  tema, `beats_por_plano`...), volver a correr plan + render y marcar `hecha: true` en `vlog.json`
  (editar solo esa clave, la app puede estar escribiendo el resto).
- Si el pedido es solo de color/musica/textos, no rehacer la historia: cambiar lo que pidio y re-render.

## Que decide Claude y que hacen los scripts

| Criterio (Claude) | Mecanico (scripts) |
|---|---|
| Teaser, orden y recorte de bloques segun el titulo | Silencios, muletillas sueltas, punch-in |
| Correcciones / arranques falsos (`quitar`) | Detectar candidatos `!!` (repeticiones, "perdon") |
| Lugar/hora, que tema va en que montaje, `beats_por_plano` | Beats, encaje de cortes, fades, niveles |
| Revisar resultado y explicar dudas a Snati | LUT, barras, subtitulos, loudness, versiones |

## Archivos

- `scripts/edicion/`: `escanear.py`, `transcribir.py`, `resumen.py`, `plan.py`, `musica.py`,
  `render.py`, `comun.py` (ver `scripts/edicion/LEEME.txt`).
- En `_edicion/`: `vlog.json`, `thumbs/`, `transcripciones/`, `transcripcion.txt`, `historia.json`,
  `plan.json`, `planes/plan_vN.json`, `musica/` (cache de beats), `progreso.log`, `Vlog_<titulo>_vN.mp4`.
- Si algo se repite o falla seguido, proponer a Snati mejorar el script y guardarlo en el repo.
