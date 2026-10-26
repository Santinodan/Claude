# Editor de Vlogs — brief (en construccion)

Documento vivo con lo que vamos definiendo con Snati antes de armar la skill.

## Decisiones tomadas

| Tema | Decision |
|---|---|
| Para quien | Vlogs propios de Snati, del dia a dia. |
| Direccion | La da el **titulo** que pasa Snati: define que se cuenta y que tomas pesan mas. |
| Formato | Horizontal 16:9. Sin minimo, **maximo 50 min**. |
| Material | Disco duro de Snati (en su compu). Se edita en una sesion **local** de Claude. |
| Perfiles | D-Log (Osmo Pocket 4P) o Rec709. Una LUT por perfil que llegue al **mismo look**. |
| Audio | Camara + mics. **Musica = de lo mas importante.** |
| Cortes | Sacar silencios largos, muletillas y correcciones ("no, mejor dicho..."). |
| Fuera | Higgsfield no se usa. |

## Pendientes

1. **Analisis de musica en vlogs de referencia**: Snati baja los videos, Claude analiza
   como sincroniza la musica con los cortes (BPM, cortes en beat, drops, cambios de tema, ducking bajo la voz).
2. **App de color**: elegir LUT con antes/despues sobre capturas del propio material.
   Idea a futuro: que la app sea el "panel de carga" del vlog (titulo, carpeta, LUT, musica, notas).
3. Referencias de vlogs (las pasa Snati, se analizan sin commitear el material).

## Pipeline tentativo

1. Escanear la carpeta del dia (ffprobe: duracion, perfil de color, audio).
2. Transcribir (Whisper) todo lo hablado.
3. Armar el corte segun el titulo: elegir tomas, sacar silencios / muletillas / correcciones.
4. Color: LUT segun perfil (elegida en la app).
5. Musica: elegir tramos, cortes en beat, ducking bajo la voz, normalizar loudness.
6. Exportar 16:9 + revisar con Snati.
