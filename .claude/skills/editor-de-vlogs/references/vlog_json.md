# Formato de `vlog.json` (contrato app ↔ Claude)

Vive en `<carpeta del dia>/_edicion/vlog.json`. La app lo escribe; Claude Code lo lee y escribe
solo las partes marcadas como "Claude". Todo en español, sin tildes en las claves.

```jsonc
{
  "version": 1,
  "titulo": "Un dia cerrando clientes en Madrid",   // da la direccion del video
  "carpeta": "/Volumes/Disco/Vlogs/2026-10-26",       // carpeta del dia (clips en orden + subcarpeta broll/)
  "fecha": "2026-10-26",

  "material": {
    "clips": [
      {
        "archivo": "DJI_0001.MP4",        // relativo a la carpeta (los de b-roll: "broll/xxx.mp4")
        "orden": 1,                       // orden de la carpeta (alfabetico)
        "duracion": 63.2,                 // segundos
        "ancho": 3840, "alto": 2160, "fps": 29.97,
        "audio": true,
        "perfil": "dlog",                 // dlog | dlog2 | rec709 | desconocido (Snati puede corregirlo)
        "broll": false,
        "descartado": false,
        "thumb": "_edicion/thumbs/DJI_0001.jpg"
      }
    ]
  },

  "historia": {
    "teaser": { "activo": true, "duracion_s": 20 },
    "capitulos_lugar_hora": true,
    "notas": "Lo importante es la reunion con el cliente",
    "bloques": []                         // Claude: [{tipo: teaser|charla|montaje|cierre, clip, entrada, salida, resumen}]
  },

  "cortes": {
    "silencio_max_s": 0.25,
    "muletillas": true,
    "correcciones": true,
    "punch_in": true,
    "agresividad": "normal"               // suave | normal | fuerte
  },

  "color": {
    "looks": {
      "dlog":   { "lut": "Powergrade/D-Log/MA_Vivo_DLog_DIA.cube", "intensidad": 100 },
      "dlog2":  { "lut": "", "intensidad": 100 },
      "rec709": { "lut": "Powergrade/High Ticket/High_Ticket_Rec709.cube", "intensidad": 80 }
    },
    "barras": { "formato": "2.22:1", "donde": "montajes" }   // formato null = sin barras; donde: todo | montajes
  },

  "audio": {
    "fuente_voz": "auto",                 // auto | camara | mic
    "reducir_ruido": true,
    "ambiente_montajes_db": -18
  },

  "musica": {
    "temas": [ { "archivo": "/ruta/instrumental.mp3", "uso": "montajes" } ],   // uso: teaser | montajes | cierre
    "en_charla": "nada",                  // nada | baja
    "fade_s": 4,
    "corte_en_beat": true,
    "volumen_montaje_db": -10
  },

  "textos": {
    "subtitulos": true,
    "titulo_episodio": { "activo": true, "numero": "2", "texto": "CONSTRUYENDO" },
    "lugar_hora": true
  },

  "exportar": { "resolucion": "1080p", "lufs": -14, "preview": true },

  "revision": {
    "notas": [ { "tc": "02:14", "texto": "cortar antes", "hecha": false } ]
  },

  "estado": {                             // Claude actualiza mientras trabaja
    "paso": "cortes",                     // ultimo paso en curso
    "versiones": [ { "archivo": "_edicion/Vlog_Madrid_v1.mp4", "fecha": "2026-10-26T20:10:00", "nota": "" } ]
  }
}
```

Archivos de trabajo que genera Claude en `_edicion/`:
- `thumbs/` miniaturas · `transcripciones/<clip>.json` (Whisper, por palabra)
- `plan.json` (lista final de segmentos a renderizar) · `Vlog_<titulo>_vN.mp4` (versiones)
