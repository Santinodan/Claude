# `historia.json` (lo escribe Claude)

Vive en `<carpeta del dia>/_edicion/historia.json`. Es el guion de edicion: que bloques van, en que
orden y que tramos de cada clip. `plan.py` lo lee y hace lo mecanico (silencios, muletillas, punch-in,
beats, musica). Si no existe, `plan.py` usa el orden de la carpeta sin teaser.

Tiempos = **segundos del clip** (los de `_edicion/transcripcion.txt`), no del video final.

```jsonc
{
  "bloques": [
    { "tipo": "teaser",                      // teaser | charla | montaje | cierre
      "resumen": "lo mejor del dia",
      "tomas": [                             // varias tomas = un plano cada una
        { "clip": "DJI_0007.MP4", "entrada": 12.0, "salida": 14.0 },          // ambiente (sin voz)
        { "clip": "broll/calle.mp4", "entrada": 3.0, "salida": 5.0 },
        { "clip": "DJI_0004.MP4", "entrada": 25.7, "salida": 29.5, "audio": "voz" }  // frase gancho
      ] },
    { "tipo": "charla", "clip": "DJI_0001.MP4", "entrada": 0, "salida": 63.2,
      "resumen": "por que vine a Madrid", "lugar": "Madrid", "hora": "11:00 AM" },
    { "tipo": "montaje", "beats_por_plano": 4, "tomas": [ ... ] },
    { "tipo": "charla", "clip": "DJI_0003.MP4" },                 // sin entrada/salida = clip entero
    { "tipo": "cierre", "clip": "DJI_0009.MP4", "entrada": 10, "salida": 40 }
  ],
  "quitar": [                                // correcciones / arranques falsos / lo que no va
    { "clip": "DJI_0001.MP4", "entrada": 7.0, "salida": 7.6, "motivo": "repite 'en China'" }
  ]
}
```

## Campos por bloque

| Campo | Para que |
|---|---|
| `tipo` | `teaser` (arranque con musica fuerte, cortes en beat) · `charla` (a camara, con cortes) · `montaje` (planos con musica fuerte, cortes en beat) · `cierre` (charla final con musica baja y fade out al final) |
| `clip`, `entrada`, `salida` | un solo tramo. En charla, `salida` vacia = hasta el final del clip; en teaser/montaje, toma sin `salida` = plano de ~1 s (teaser) o ~2 s (montaje) desde `entrada` (o del medio del clip) |
| `tomas` | lista de tramos `{clip, entrada, salida, audio}`; en teaser/montaje cada toma = un plano |
| `audio` (en la toma) | `voz` = se procesa como charla (saca silencios) y la musica baja debajo · `ambiente` = sonido del clip bajito (por defecto en teaser/montaje) |
| `beats_por_plano` | fuerza 1/2/4/8 beats por plano. Sin esto elige el multiplo de beat mas cercano al largo de la toma |
| `tema` | indice (0, 1…) o nombre de archivo de `musica.temas` para este bloque |
| `musica` | `false` = este bloque sin musica |
| `cortar` | `false` = no sacar silencios ni muletillas en este bloque (momento que respira) |
| `lugar`, `hora` | separador "lugar · hora" al empezar el bloque (si `textos.lugar_hora`). Sin `hora` usa la hora de grabacion del clip |
| `resumen` | texto corto para la app (que pasa en el bloque) |

## Notas

- En montajes la toma puede estirarse hasta ~0,6 s mas que `salida` para que el corte caiga en el beat.
  Si necesitas un corte exacto, deja margen o pone `beats_por_plano`.
- Varias tomas seguidas del mismo clip en orden se renderizan juntas (mas rapido).
- `quitar` vale en cualquier bloque: saca ese rango del clip donde aparezca.
- Al armar el plan, los bloques se copian a `vlog.json` → `historia.bloques` (una entrada por toma,
  con `grupo` = numero de bloque) para que la app los muestre.
