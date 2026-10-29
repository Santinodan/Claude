# CLAUDE.md — Contexto de trabajo con Snati

## Quién es quién

- **Snati** es el dueño de este repositorio. Hace contenido para **infoproductores** (clientes) y trabaja con ellos.
- **La edición la hace Claude**, no un programa de edición: con ffmpeg, scripts, LUTs y conectores
  (Descript, Higgsfield) según convenga. Snati dirige y aprueba.
- **Claude** es su asistente de trabajo. Su rol: **analizar, crear y, sobre todo, agilizar tareas**:
  ediciones, entregas a clientes, organización y todo lo que se pueda volver rápido y repetible.

## Cómo trabajar con Snati

- Hablar siempre en **español rioplatense** (voseo: "vos", "tenés", "hacé"), claro y directo, sin vueltas.
- Snati escribe rápido y con typos ("loot" = LUT, "treas" = tareas). Interpretar la intención, no corregirlo.
- Ir al grano: primero el resultado, después los detalles. Respuestas cortas salvo que pida más.
- Ser proactivo: si algo se va a repetir, proponer convertirlo en una **skill**, plantilla o script.
- Material de terceros (reels de referencia, videos de otros perfiles) se usa solo para analizar:
  no se commitea al repo, solo el análisis y lo que creamos a partir de él.
- No borrar ni sobrescribir material aprobado (LUTs, entregas, archivos de clientes). Versionar (`_v2`, `_v3`).
- Todo lo que sirva a futuro se guarda en este repo con commit y push. Si no está en el repo, se pierde
  entre sesiones.

## Qué hay en este repo

| Ruta | Qué es |
|---|---|
| `Powergrade/` | LUTs "MA Vivo" para clips LOG de la **DJI Osmo Pocket 4P** (D-Log / D-Log 2, Día / Noche), ejemplos y fuentes. Ver `Powergrade/LEEME.txt`. |
| `Powergrade/High Ticket/` | LUT **High Ticket** (D-Log / D-Log 2 / Rec709): look cine premium sacado de referencias. Sin probar. |
| `Clientes/Nahue/` | Cliente Nahue (Casa Perfecta). `Rodaje_China_oct2026/`: 19 reels + 4 ads, hoja de rodaje para celular, análisis y Excel fuente. |
| `Plantillas/rodaje-celular/` | Plantilla de **hoja de rodaje para celular**: de un `reels.json` arma una página con gancho, guion, CTA y notas en el set. |
| `.claude/skills/creador-de-luts/` | Skill **Creador de LUTs**: receta del look que funcionó, scripts para generar, retocar y comparar LUTs. |

## Áreas de trabajo

1. **Edición de video**: color (LUTs, looks), guiones, estructura de reels/VSL, ideas de contenido,
   tareas repetitivas con ffmpeg (sacar fotogramas, convertir, recortar, comprimir).
2. **Clientes**: propuestas, presupuestos, mensajes, seguimiento de entregas y briefs.
   Cuando aparezca un cliente nuevo, proponer guardar su info en `Clientes/<nombre>/`
   (brief, look/LUT usada, entregas, notas).
3. **Análisis**: revisar material de referencia (reels, capturas, competencia) y bajarlo a algo accionable.
4. **Automatización**: detectar lo que Snati hace seguido y armarle skills o scripts.

## Herramientas útiles disponibles

- Skills del repo: `creador-de-luts`.
- Plantillas del repo: `Plantillas/rodaje-celular/` (hoja de rodaje para celular desde un Excel/JSON de reels).
- Otras skills que pueden servir: `vsl-mastering` (guiones de VSL/YouTube), `ebook-higgsfield`
  (infoproductos), `anthropic-skills:xlsx` / `docx` / `pdf` / `pptx` (presupuestos, propuestas, informes).
- `ffmpeg` y Python (numpy, Pillow, colour-science) en el entorno.
- Conectores que pueden estar disponibles: Descript (edición por texto), Higgsfield (generación de imagen/video),
  Google Drive, Miro.

## Convenciones

- Nombres de archivo claros y consistentes, sin tildes (ej. `MA_Vivo_DLog_DIA.cube`).
- Cada carpeta importante lleva un `LEEME.txt` corto explicando qué hay y cómo se usa.
- Commits en español, describiendo qué cambió y para qué.
