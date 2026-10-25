---
name: creador-de-luts
description: Crear, ajustar o regenerar LUTs .cube de color grading para clips LOG (DJI D-Log / D-Log 2, DJI Osmo Pocket 4P), en especial la familia "MA Vivo" (look estilo reel de @marcoalbanny - colores vivos, sombras teal, piel calida, cielo turquesa). Usar SIEMPRE que el usuario pida una LUT, un LUT, "loot", un powergrade, un look de color, "que se vea como el reel", una version de dia/noche, o retocar una LUT existente (mas calida, mas brillo, menos saturada, etc.).
---

# Creador de LUTs (familia "MA Vivo")

Esta skill guarda la receta que FUNCIONO para crear las LUTs de `Powergrade/` de este repo.
Usala para crear LUTs nuevas, retocar las aprobadas o regenerarlas.

## Lo que ya existe (no romperlo)

| Archivo en `Powergrade/` | Estado | Uso |
|---|---|---|
| `D-Log/MA_Vivo_DLog_NOCHE.cube` | APROBADA (el look base) | Clips D-Log de noche / interiores oscuros |
| `D-Log/MA_Vivo_DLog_DIA.cube` | APROBADA | Clips D-Log con luz de dia, cielo turquesa |
| `D-Log 2 (sin probar)/MA_Vivo_DLog2_NOCHE.cube` | Sin probar | Clips D-Log 2 de noche |
| `D-Log 2 (sin probar)/MA_Vivo_DLog2_DIA.cube` | Sin probar | Clips D-Log 2 de dia |
| `Ejemplos/*.jpg/png` | Referencia | Comparativas clip vs reel (lo que se buscaba) |
| `_Fuente/` | Original | Scripts originales (tienen rutas rotas de otra sesion; usar los de esta skill) |

Formato de todas: `.cube` 3D, tamano 33, dominio 0-1, entrada = codigo LOG, salida = Rec.709 gamma 2.4.
Nombre: `MA_Vivo_<PERFIL>_<LUZ>.cube` (PERFIL = DLog | DLog2, LUZ = DIA | NOCHE).

## Herramientas (en `scripts/` de esta skill)

Instalar una vez: `pip install -r .claude/skills/creador-de-luts/scripts/requirements.txt` (numpy, colour-science, pillow).

- `generar_familia.py` – genera LUTs desde cero con el pipeline original.
  - `DLog_NOCHE` sale **identica byte a byte** a la aprobada (verificado).
  - `DLog2_NOCHE` = mismo look con exposicion x2.973 (dif. max 0.028 vs la del repo).
  - `DLog_DIA` / `DLog2_DIA`: solo punto de partida. Las DIA aprobadas se retocaron a mano y esos
    parametros NO se guardaron, asi que no se pueden regenerar exactas.
  - `--mult X --nombre DLog_ALGO` crea una variante libre con otro multiplicador de exposicion.
  - `--set '{"sat":1.1}'` / `--set-boost '{...}'` pisan parametros (ver `references/parametros.md`).
- `ajustar_cube.py` – **forma preferida de iterar**: toma una LUT aprobada y le suma un retoque
  (`--expo`, `--contraste`, `--sat`, `--temp`, `--tinte`, `--sombras-teal`, `--piel`, `--cielo`,
  `--negro`, `--mezcla`). Sin flags devuelve la misma LUT (verificado), asi que el look aprobado no se pierde.
- `preview.py` – aplica LUTs a un fotograma LOG y arma una comparativa vertical rotulada
  (+ referencia opcional) e imprime metricas OKLab (luminancia y croma por zona) para comparar sin mirar.
- `lutlib.py` – libreria: curvas D-Log / D-Log2, matrices de gamut, tonemap, grade OKLab, leer/escribir/aplicar `.cube`.

## Como se construyo el look (pipeline)

Por cada valor de entrada (codigo LOG):

1. **Decodificar con la curva D-Log 2 → lineal**, incluso para clips D-Log. Asi se aprobo el look:
   el gris de D-Log (0.40) leido como D-Log2 cae ~1.58 stops arriba, y eso es parte del look Noche.
   Por eso la diferencia entre variantes es solo un **multiplicador de exposicion**:
   `DLOG_GREY_COMP = 0.18 / dlog2_to_lin(0.3996) ≈ 0.336`.
2. Matriz D-Gamut2 → Rec.709 lineal, multiplicada por el multiplicador de la variante.
3. `tonemap`: rodilla suave en altas (no quema hasta ~6.5 stops sobre gris) + curva tipo ACES (exposure 0.5053).
4. `grade` en OKLab con `final_params.json`: contraste en S, azules corridos a turquesa/cian
   (`blue_shift -58`), verdes desaturados y oscurecidos, naranjas/piel saturados (`warm_sat 1.28`),
   split toning: sombras teal (hue 170) y altas calidas (hue 85).
5. Encode Rec.709 gamma 2.4.
6. **Boost**: un segundo `grade` sobre la imagen ya en 709 (base en `generar_familia.BOOST_BASE`
   + `boost_params.json`): mas contraste, sombras teal (hue 185), saturacion 1.18, piel calida.

Este fue el "v2" que se aprobo frente al "v1" (ver `Powergrade/Ejemplos/NOCHE_tu_clip_vs_reel.jpg`).

## Flujo de trabajo cuando el usuario pide algo

1. **Entender el pedido**: que perfil grabo (D-Log o D-Log 2), que luz (dia/noche/interior),
   y que quiere cambiar. Si no lo dice, preguntar el perfil; es lo que mas cambia el resultado.
2. **Conseguir un fotograma** del clip LOG sin filtros (si el usuario lo sube):
   `ffmpeg -ss 00:00:03 -i clip.mp4 -frames:v 1 frame_log.png`. Si hay referencia (reel, captura), guardarla tambien.
3. **Elegir el camino**:
   - Retoque de una aprobada (mas calida, mas clara, etc.) → `ajustar_cube.py` sobre el `.cube` de `Powergrade/`.
     Empezar con valores sutiles (`--temp 0.01`, `--expo 0.2`, `--sat 1.05`).
   - Otra exposicion / otro perfil con el mismo look → `generar_familia.py --mult ...`.
   - Look muy distinto → `generar_familia.py` con `--set` / `--set-boost`, o un params JSON nuevo.
4. **Previsualizar**: `preview.py --frame frame_log.png --ref referencia.png --out comp.png LUT_vieja.cube LUT_nueva.cube`,
   mirar la imagen (con Read) y comparar las metricas contra la referencia. Iterar.
5. **Entregar** en `Powergrade/` respetando nombres y carpetas. Las nuevas sin probar van en una carpeta
   `(sin probar)` hasta que el usuario las confirme. Nunca sobrescribir una APROBADA sin que lo pida:
   versionar (`..._v2.cube`). Actualizar `Powergrade/LEEME.txt` y guardar en `Powergrade/_Fuente/`
   los parametros/comandos usados, para poder regenerarla despues.
6. **Validar** antes de entregar: el `.cube` tiene `LUT_3D_SIZE 33` y 35937 lineas de datos; negros y
   blancos no se dan vuelta; probarla en el fotograma con `preview.py`.

## Instrucciones de uso para el usuario (repetirlas al entregar)

- UNA sola LUT por clip, al 100%, directo sobre el clip LOG, sin otro filtro antes.
- Elegir la LUT segun el perfil con que se grabo (D-Log vs D-Log 2) y la luz de la toma.
- Si queda muy oscura o clara, corregir la exposicion ANTES de la LUT (o pedir una variante).

Comandos ejemplo (desde la raiz del repo):

```bash
S=.claude/skills/creador-de-luts/scripts
# Regenerar la familia en una carpeta temporal
python3 $S/generar_familia.py --out /tmp/luts
# Dia aprobada un poco mas calida y clara, como v2
python3 $S/ajustar_cube.py "Powergrade/D-Log/MA_Vivo_DLog_DIA.cube" "Powergrade/D-Log/MA_Vivo_DLog_DIA_v2.cube" \
  --titulo "MA Vivo - D-Log - Dia v2" --temp 0.01 --expo 0.2
# Comparativa
python3 $S/preview.py --frame frame_log.png --out comp.png \
  "Powergrade/D-Log/MA_Vivo_DLog_DIA.cube" "Powergrade/D-Log/MA_Vivo_DLog_DIA_v2.cube" --etiquetas "v1,v2"
```
