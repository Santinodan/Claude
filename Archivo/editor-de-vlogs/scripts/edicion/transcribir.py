#!/usr/bin/env python3
"""Transcribe con Whisper (faster-whisper) los clips del vlog, con tiempo por palabra.

Uso:
  python3 transcribir.py <vlog.json> [--modelo small] [--idioma es] [--broll] [--forzar]

- Cache por clip en _edicion/transcripciones/<clip>.json (si existe, lo saltea; --forzar rehace).
- Saltea clips descartados, sin audio y (salvo --broll) los de b-roll.
- El audio se decodifica con ffmpeg a 16 kHz mono y se le pasa el array a Whisper
  (pasarle la ruta falla en algunos entornos por la version de 'av').
- Al final arma _edicion/transcripcion.txt (texto con tiempos + posibles correcciones) para leer rapido.

Formato del json por clip:
  {"clip", "idioma", "duracion", "segmentos": [{"inicio","fin","texto",
     "palabras": [{"inicio","fin","palabra","prob"}]}]}
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402


def ruta_tx(edicion, archivo):
    return os.path.join(edicion, "transcripciones", comun.nombre_seguro(archivo) + ".json")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("vlog")
    ap.add_argument("--modelo", default="small")
    ap.add_argument("--idioma", default="es", help="'auto' para detectar")
    ap.add_argument("--broll", action="store_true", help="transcribir tambien b-roll")
    ap.add_argument("--forzar", action="store_true", help="rehacer aunque haya cache")
    args = ap.parse_args()

    vlog = os.path.abspath(args.vlog)
    _, cfg = comun.cargar_vlog(vlog)
    edicion = comun.dir_edicion(vlog)
    carpeta = comun.carpeta_dia(vlog, cfg)
    clips = [c for c in cfg["material"]["clips"] if not c.get("descartado") and c.get("audio", True)
             and (args.broll or not c.get("broll"))]
    pendientes = [c for c in clips if args.forzar or not os.path.exists(ruta_tx(edicion, c["archivo"]))]
    comun.marcar_paso(vlog, "transcribir")
    comun.abrir_log(edicion, "transcribir")

    modelo = None
    for i, c in enumerate(pendientes, 1):
        comun.progreso("transcribir", i, len(pendientes), c["archivo"])
        if modelo is None:
            from faster_whisper import WhisperModel
            modelo = WhisperModel(args.modelo, device="cpu", compute_type="int8",
                                  cpu_threads=max(1, (os.cpu_count() or 4) - 1))
        audio = comun.decodificar_audio(os.path.join(carpeta, c["archivo"]), sr=16000)
        segs_out, idioma = [], ""
        if len(audio) > 1600:
            segs, info = modelo.transcribe(audio, language=None if args.idioma == "auto" else args.idioma,
                                           vad_filter=True, word_timestamps=True, beam_size=5,
                                           condition_on_previous_text=False)
            idioma = info.language
            for s in segs:
                segs_out.append({
                    "inicio": round(s.start, 3), "fin": round(s.end, 3), "texto": s.text.strip(),
                    "palabras": [{"inicio": round(w.start, 3), "fin": round(w.end, 3),
                                  "palabra": w.word.strip(), "prob": round(w.probability, 3)}
                                 for w in (s.words or [])]})
        comun.escribir_json(ruta_tx(edicion, c["archivo"]),
                            {"clip": c["archivo"], "idioma": idioma, "duracion": len(audio) / 16000,
                             "segmentos": segs_out})
        n_pal = sum(len(s["palabras"]) for s in segs_out)
        print(f"  {c['archivo']}: {n_pal} palabras", flush=True)

    # resumen legible para Claude (elegir teaser, bloques y correcciones)
    import resumen
    txt = resumen.armar(cfg, edicion)
    with open(os.path.join(edicion, "transcripcion.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    comun.fin_log("FIN OK transcribir")
    print(f"OK transcripciones en {os.path.join(edicion, 'transcripciones')} | "
          f"resumen en {os.path.join(edicion, 'transcripcion.txt')}", flush=True)


if __name__ == "__main__":
    main()
