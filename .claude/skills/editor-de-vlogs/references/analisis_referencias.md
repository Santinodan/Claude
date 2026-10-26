# Analisis de vlogs de referencia (oct 2026)

Material analizado (solo analisis, los videos NO se suben al repo):

| Ref | Video | Duracion | Idioma |
|---|---|---|---|
| G1 | Guillermo Hernandez — "la realidad de construir una empresa exitosa con 19 años" | 18:44 | es |
| G2 | Guillermo Hernandez — "viviendo mi vida soñada en bali con 19 años" | 19:02 | es |
| B1 | Brez — "celebrating my 22nd birthday in spain as a millionaire..." | 28:26 | en |

Herramientas: ffmpeg (scdet = cortes, cropdetect = barras, ebur128 = loudness), Whisper small
(transcripcion con tiempo por palabra), librosa (beats), demucs (separar voz/musica en tramos de 60 s).
Scripts en `scripts/analisis/`.

---

## 1. Estructura

- **Arranque = avance/teaser sin voz** con musica, cortado en beat:
  - B1: 0:00–0:30, montaje de los mejores momentos del vlog (aeropuerto → auto → fiesta → pileta → club),
    un plano cada ~2 s, **con barras**.
  - G2: plano general quieto del lugar (8 s) → corte a noche → **titulo de episodio "#2 CONSTRUYENDO"**
    en rojo neon. Despues aparece el nombre "GUILLERMO" en rojo.
  - G1: arranca hablando a camara, con un montaje de 12 s cortado **en cada beat** (1 plano = 1 beat).
- **Cuerpo = alterna bloques de charla a camara con montajes cortos (10–60 s) con musica.**
  Los montajes funcionan como transicion entre lugares / momentos del dia.
- Cuanto se habla: G1 83%, G2 75%, **B1 61%** (Brez tiene mas montaje y momentos sin charla).

## 2. Cortes en la charla (jump cuts)

- Silencios practicamente eliminados en los 3: entre palabras la pausa mediana es **0 s** y el p95 **0–0,22 s**.
  Solo el 0,5–2% de las pausas supera 0,5 s.
  → Regla: **cortar todo silencio > ~0,25 s**, dejando 2–4 frames de aire antes y despues de la palabra.
- Jump cuts con **cambio de encuadre** (punch-in): se alterna plano abierto y plano mas cerrado
  (~110–120%) del mismo clip para que el corte no "salte". (G1 0:57–1:09)

## 3. Musica (lo mas importante)

- **Montaje = musica fuerte. Charla = sin musica.**
  - G1 (1:00–2:00): con voz la musica queda en –56 dB (o sea, apagada); en el montaje sube a –10/–15 dB,
    **mas alta que la voz** (voz a –21 dB).
  - B1 (10:00–10:30): musica a full en el montaje → **fade out de ~5 s** → charla con sonido ambiente.
- **Cortes en el beat:** en los montajes, **83–100% de los cortes caen en el beat** (al azar seria 25–35%).
  - Largo de plano en multiplos de beat: **1, 2, 4, 6 u 8 beats**.
  - Intro rapida: 1 plano por beat. Montaje de paseo: 4–8 beats por plano.
  - Algunos montajes cortos no siguen el beat (sonido ambiente, sin tema de fondo).
- **Guillermo corta estricto al beat; Brez es mas libre:** en B1 la mayoria de los montajes
  sigue la accion (fiesta, pileta) y no el beat, salvo momentos clave como el cierre (26:15, 86% en beat).
  → Por defecto cortar en beat (estilo Guillermo); en momentos de accion se puede priorizar la accion.
- Tempos de los temas: 90–100 BPM y 120–150 BPM (rap/trap, coincide con la playlist "Soul").
- Brez usa temas **con letra** en los montajes; Guillermo mezcla.

## 4. Barras negras (letterbox)

- **B1:** barras **solo en los montajes cinematicos** (intro, fiesta, momentos clave), no en la charla.
  Medida: imagen visible 1280x576 en 720p → **2.22:1**, barra de **10% de alto** arriba y abajo
  (en 1080p: 1920x864, barras de 108 px).
- G1/G2: sin barras.
- Snati quiere barras finas en sus vlogs → definir si van en todo el video o solo en montajes (ver pendientes).

## 5. Texto en pantalla

- **Subtitulos (G1):** chicos, blanco, sans serif tipo Helvetica/SF, en minuscula natural, sin caja,
  centrados abajo (~90% del alto), 4–7 palabras por linea, una sola linea. Muy discretos.
- **Lugar y hora (G1 1:00):** "Bali" a la izquierda y "11:00 AM" a la derecha, chico, blanco,
  a media altura, sobre un plano general. Funciona como separador de capitulo.
- **Titulo de episodio (G2):** "#2" y despues "CONSTRUYENDO", tipografia condensada en mayusculas,
  **rojo con glow** (neon), centrado, sobre plano nocturno oscuro.
- **Nombre (G2):** "GUILLERMO" rojo, condensado, sobre plano detalle.

## 6. Color

- G1/G2: contraste alto, negros densos, verdes/turquesas fuertes, piel calida. Look "cine teal".
- B1: noche muy oscura, luces de colores saturadas, dia con turquesa de pileta.
- Coincide con la familia MA Vivo / High Ticket del repo.

## 7. Sonido general

| Ref | Loudness integrado | Rango (LRA) |
|---|---|---|
| G1 | –17,9 LUFS | 11 LU |
| G2 | –16,1 LUFS | 9 LU |
| B1 | –19,7 LUFS | 21 LU (mucho contraste charla/fiesta) |

→ Entregar a **–14 a –16 LUFS** (YouTube normaliza a –14), pico maximo –1 dBTP.

---

## Reglas para la skill (resumen)

1. Intro: teaser de 15–30 s con lo mejor del vlog, musica fuerte, cortes en beat, barras.
2. Charla: sacar silencios > 0,25 s, muletillas y correcciones; alternar encuadre en jump cuts.
3. Montajes entre bloques: musica fuerte (≈ +8 dB sobre la voz), cortes en beat (1/2/4/8 beats).
4. Entrar a la charla: fade out de la musica de 3–5 s (o corte seco en un beat fuerte).
5. Textos: subtitulos chicos y blancos; lugar + hora como separador; titulo de capitulo en rojo neon condensado.
6. Master final –14/–16 LUFS.
