# `plan.json` y la línea de tiempo (contrato app ↔ motor)

`_edicion/plan.json` es la edición final que lee `render.py`. Lo arma `plan.py` (con la historia de Claude)
y después Snati lo puede retocar en la **Línea de tiempo** de la app. Todo lo de abajo marcado *(timeline)*
es opcional: si falta, el render se comporta como antes.

## Cabecera
```jsonc
{ "version": 1, "fps": "30000/1001", "duracion": 110.3,
  "editado_a_mano": true,            // (timeline) la app lo pone al guardar
  "editado": "2026-10-26T20:00:00",  // (timeline)
  ... }
```
Si `editado_a_mano` es true, `plan.py` NO lo pisa (salvo `--forzar`, que antes guarda copia en
`planes/plan_manual_<fecha>.json`).

## Pistas

| Pista en la app | Clave | Notas |
|---|---|---|
| V1 Video | `segmentos[]` | Secuenciales: `t` = suma de las `dur` anteriores. |
| A1 Voz | (la misma `segmentos[]`) | Audio del clip de cada segmento. |
| C1 Color | `capas_color[]` *(timeline)* | Capas de ajuste con LUT. |
| A2 Música | `musica[]` | |
| A3 Efectos | `sfx[]` *(timeline)* | |
| T1 Textos | `textos[]` | |

### segmentos[] (V1 + A1)
Campos de siempre: `n, bloque, tipo (teaser|charla|montaje|cierre), clip, entrada, salida, t, dur, frames, zoom, perfil, audio (voz|ambiente)`.
*(timeline)* agrega:
- `vol_db` (número, default 0): ganancia extra del audio de ese segmento.
- `mute` (bool): sin audio del clip.
- `color` (`{lut, intensidad}` o null): color propio del segmento; gana sobre capas y perfil.

La app mantiene: `dur = salida - entrada`, `frames = round(dur * fps)`, `t` corrido (ripple).
El render igual los recalcula desde `entrada/salida` por si vienen desfasados.

### capas_color[] (C1) *(timeline)*
`{id, nombre, t, dur, lut, intensidad (0-100)}` — `lut` relativo al repo (`Powergrade/...`, `Perfiles/...`) o absoluto.
Un segmento usa la capa que cubre su **inicio** (`t`). Prioridad: `segmento.color` > capa > look del perfil (vlog.json).

### musica[] (A2)
`{id?, tema, t, dur, desde, nivel_db, fade_in, fade_out, lufs_tema?, mute?}` — `mute` es *(timeline)*.

### sfx[] (A3) *(timeline)*
`{id, archivo (ruta absoluta), t, dur, desde (default 0), nivel_db (default -14, mismo criterio que la música:
loudness objetivo del efecto), fade_in (0), fade_out (0), mute}`. Si `dur` falta, dura lo que el archivo.

### textos[] (T1)
De siempre: `{tipo: "titulo", t, dur, numero, texto}` y `{tipo: "lugar_hora", t, dur, lugar, hora}`.
*(timeline)* agrega `{tipo: "texto", t, dur, texto, estilo: "titulo"|"lugar"|"simple", pos: "centro"|"arriba"|"abajo"}`
y `oculto: true` en cualquier texto para no mostrarlo.

Los subtítulos no son una pista: salen de la transcripción (vlog.json `textos.subtitulos`).
