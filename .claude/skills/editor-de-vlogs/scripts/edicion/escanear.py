#!/usr/bin/env python3
"""Escanea la carpeta del dia y actualiza material.clips en _edicion/vlog.json.

Uso:
  python3 escanear.py <carpeta del dia | ruta a vlog.json> [--sin-thumbs]

- Lista los clips .mp4/.mov (mayus/minus da igual) en orden alfabetico + los de broll/.
- Por clip: duracion, resolucion, fps, audio, hora de grabacion y perfil de color ADIVINADO.
- Saca una miniatura a _edicion/thumbs/.
- MEZCLA con lo que ya hay: en clips existentes respeta perfil, broll y descartado (los toca Snati).

Perfil (es una ADIVINANZA, Snati lo corrige en la app):
  1) metadatos con "dlog2"/"d-log 2" o "dlog"/"d-log" -> eso
  2) transferencia HLG / PQ -> desconocido (no hay LUT para eso)
  3) heuristica de luminancia en 5 fotogramas: LOG = negros levantados, poco contraste y poca
     saturacion -> "dlog" (no se puede distinguir D-Log de D-Log 2 con la imagen). Si no -> rec709.
"""
import argparse
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402


def listar_clips(carpeta):
    out = []
    for sub, es_broll in (("", False), ("broll", True)):
        d = os.path.join(carpeta, sub)
        if not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d), key=str.lower):
            if n.startswith(".") or not n.lower().endswith(comun.VIDEO_EXT):
                continue
            out.append(((sub + "/" + n) if sub else n, es_broll))
    return out


def textos_metadatos(info):
    partes = []
    for bloque in [info.get("format", {})] + info.get("streams", []):
        for k, v in (bloque.get("tags") or {}).items():
            partes.append(f"{k}={v}")
    return " ".join(partes).lower()


def muestras_luma(path, dur, n=5):
    """Devuelve (p1, p99, saturacion media) de n fotogramas chicos (rgb 0..1)."""
    ys, sats = [], []
    for k in range(n):
        t = dur * (0.1 + 0.8 * k / max(1, n - 1))
        r = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-ss", f"{t:.2f}", "-i", path,
                            "-frames:v", "1", "-vf", "scale=96:54", "-pix_fmt", "rgb24",
                            "-f", "rawvideo", "-"], capture_output=True)
        if r.returncode != 0 or len(r.stdout) < 96 * 54 * 3:
            continue
        a = np.frombuffer(r.stdout[:96 * 54 * 3], np.uint8).reshape(-1, 3) / 255.0
        ys.append(a @ np.array([0.2126, 0.7152, 0.0722]))
        mx, mn = a.max(1), a.min(1)
        sats.append(np.mean((mx - mn) / np.maximum(mx, 1e-3)))
    if not ys:
        return None
    y = np.concatenate(ys)
    return float(np.percentile(y, 1)), float(np.percentile(y, 99)), float(np.mean(sats))


def adivinar_perfil(path, info, v, dur):
    meta = textos_metadatos(info)
    for clave, perfil in (("dlog2", "dlog2"), ("d-log 2", "dlog2"), ("d-log2", "dlog2"),
                          ("dlog", "dlog"), ("d-log", "dlog")):
        if clave in meta:
            return perfil, "metadatos"
    trc = (v.get("color_transfer") or "").lower()
    if trc in ("arib-std-b67", "smpte2084"):
        return "desconocido", "metadatos (HLG/HDR)"
    m = muestras_luma(path, dur)
    if m is None:
        return "desconocido", "sin datos"
    p1, p99, sat = m
    # LOG: negros levantados (~0.08+), blancos que no llegan (<0.9), poco color
    puntos = (p1 > 0.05) + (p99 < 0.88) + (sat < 0.28) + ((p99 - p1) < 0.65)
    if puntos >= 3:
        return "dlog", f"heuristica (p1={p1:.2f} p99={p99:.2f} sat={sat:.2f})"
    return "rec709", f"heuristica (p1={p1:.2f} p99={p99:.2f} sat={sat:.2f})"


def datos_clip(carpeta, archivo, es_broll, edicion, thumbs=True):
    path = os.path.join(carpeta, archivo)
    info = comun.ffprobe(path)
    if not info:
        return None
    v = next((s for s in info["streams"] if s.get("codec_type") == "video"), None)
    a = next((s for s in info["streams"] if s.get("codec_type") == "audio"), None)
    if v is None:
        return None
    dur = float(info["format"].get("duration") or v.get("duration") or 0)
    fr = v.get("avg_frame_rate") if v.get("avg_frame_rate", "0/0") != "0/0" else v.get("r_frame_rate")
    try:
        num, den = [int(x) for x in fr.split("/")]
        fps_fr = f"{num}/{den}"
        fps = round(num / den, 3)
    except (ValueError, ZeroDivisionError, AttributeError):
        fps_fr, fps = "30/1", 30.0
    ancho, alto = int(v.get("width", 0)), int(v.get("height", 0))
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    if abs(rot) in (90, 270):
        ancho, alto = alto, ancho
    perfil, origen = adivinar_perfil(path, info, v, dur)
    creado = (info["format"].get("tags") or {}).get("creation_time", "")
    thumb = ""
    if thumbs:
        rel = f"_edicion/thumbs/{os.path.splitext(comun.nombre_seguro(archivo))[0]}.jpg"
        dst = os.path.join(os.path.dirname(edicion), rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        r = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-ss", f"{dur * 0.3:.2f}",
                            "-i", path, "-frames:v", "1", "-vf", "scale=480:-2", "-q:v", "4", dst],
                           capture_output=True)
        thumb = rel if r.returncode == 0 else ""
    return {
        "archivo": archivo, "duracion": round(dur, 3), "ancho": ancho, "alto": alto,
        "fps": fps, "fps_frac": fps_fr, "audio": a is not None,
        "perfil": perfil, "perfil_detectado": perfil, "perfil_origen": origen,
        "broll": es_broll, "descartado": False, "thumb": thumb,
        "codec": v.get("codec_name", ""), "bits": 10 if "10" in (v.get("pix_fmt") or "") else 8,
        "creado": creado, "hora": creado[11:16] if len(creado) >= 16 else "",
    }


# Campos que decide Snati: si el clip ya estaba, no se pisan
CAMPOS_USUARIO = ("perfil", "broll", "descartado")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ruta", help="carpeta del dia o ruta a _edicion/vlog.json")
    ap.add_argument("--sin-thumbs", action="store_true", help="no sacar miniaturas")
    args = ap.parse_args()

    if args.ruta.lower().endswith(".json"):
        vlog = os.path.abspath(args.ruta)
        _, cfg = comun.cargar_vlog(vlog) if os.path.exists(vlog) else ({}, comun.DEFAULTS)
        carpeta = comun.carpeta_dia(vlog, cfg)
    else:
        carpeta = os.path.abspath(args.ruta)
        vlog = os.path.join(carpeta, "_edicion", "vlog.json")
    if not os.path.isdir(carpeta):
        sys.exit(f"No existe la carpeta {carpeta}")
    edicion = os.path.dirname(vlog)
    os.makedirs(edicion, exist_ok=True)

    comun.abrir_log(edicion, "escanear")
    lista = listar_clips(carpeta)
    nuevos = []
    for i, (archivo, es_broll) in enumerate(lista, 1):
        comun.progreso("escanear", i, len(lista), archivo)
        d = datos_clip(carpeta, archivo, es_broll, edicion, thumbs=not args.sin_thumbs)
        if d:
            d["orden"] = i
            nuevos.append(d)
        else:
            print(f"AVISO no pude leer {archivo}", flush=True)

    def aplicar(raw):
        if not raw:
            raw.update({"version": 1, "titulo": os.path.basename(carpeta), "fecha": ""})
        raw.setdefault("carpeta", carpeta)
        previos = {c.get("archivo"): c for c in raw.get("material", {}).get("clips", [])}
        clips = []
        for d in nuevos:
            p = previos.get(d["archivo"])
            if p:
                for k in CAMPOS_USUARIO:
                    if k in p:
                        d[k] = p[k]
                # otros campos extra que haya puesto la app tambien se conservan
                for k, val in p.items():
                    d.setdefault(k, val)
            clips.append(d)
        raw.setdefault("material", {})["clips"] = clips
        raw.setdefault("estado", {})["paso"] = "material"

    comun.actualizar_vlog(vlog, aplicar)
    perf = {}
    for d in nuevos:
        perf[d["perfil"]] = perf.get(d["perfil"], 0) + 1
    comun.fin_log(f"FIN OK escanear {len(nuevos)} clips")
    print(f"OK {len(nuevos)} clips ({sum(d['broll'] for d in nuevos)} b-roll) | perfiles {perf} | {vlog}",
          flush=True)


if __name__ == "__main__":
    main()
