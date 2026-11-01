#!/usr/bin/env python3
"""Musica: tempo, beats y loudness de un tema + cortes de montaje encajados al beat.

Uso:
  python3 musica.py analizar <tema> [--cache DIR]
  python3 musica.py encajar <tema> --desde 12.3 --duraciones 2,1.5,3 [--disponibles 5,5,5]
                    [--beats-por-plano 2] [--cache DIR]

'analizar' imprime BPM, cantidad de beats, duracion y LUFS (y lo guarda en cache).
'encajar' toma las duraciones deseadas de cada plano y las ajusta para que cada corte caiga
en un beat (1/2/4/8 beats por plano), arrancando el montaje en el primer beat >= --desde.
plan.py usa estas mismas funciones.
"""
import argparse
import hashlib
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402

PERMITIDOS = (1, 2, 4, 8)


def analizar(tema, cache_dir=None):
    """{'archivo','duracion','bpm','beats':[s...],'lufs'} (con cache por archivo+tamano+fecha)."""
    st = os.stat(tema)
    clave = hashlib.md5(f"{os.path.abspath(tema)}|{st.st_size}|{int(st.st_mtime)}".encode()).hexdigest()[:12]
    cache = os.path.join(cache_dir, f"{clave}.json") if cache_dir else None
    if cache and os.path.exists(cache):
        return comun.leer_json(cache)
    import librosa
    sr = 22050
    y = comun.decodificar_audio(tema, sr=sr)
    dur = len(y) / sr
    hop = 512
    env = librosa.onset.onset_strength(y=librosa.effects.percussive(y, margin=3.0), sr=sr, hop_length=hop)
    tempo, frames = librosa.beat.beat_track(onset_envelope=env, sr=sr, hop_length=hop)
    beats = librosa.frames_to_time(frames, sr=sr, hop_length=hop).tolist()
    if len(beats) >= 2:
        bpm = 60.0 / float(np.median(np.diff(beats)))
    else:
        bpm = float(np.atleast_1d(tempo)[0]) or 120.0
        beats = list(np.arange(0, dur, 60.0 / bpm))
    lufs, pico = comun.medir_lufs(["-i", tema])
    info = {"archivo": os.path.abspath(tema), "duracion": dur, "bpm": round(bpm, 2),
            "beats": [round(b, 4) for b in beats], "lufs": lufs, "pico": pico}
    if cache:
        comun.escribir_json(cache, info)
    return info


def beats_desde(info, desde, hasta):
    """Beats del tema entre desde y hasta (el tema se repite en loop si hace falta)."""
    dur, b = info["duracion"], np.array(info["beats"])
    if dur <= 0 or len(b) == 0:
        return np.array([])
    out = []
    k0, k1 = int(desde // dur), int(hasta // dur) + 1
    for k in range(k0, k1 + 1):
        out.append(b + k * dur)
    t = np.concatenate(out)
    return t[(t >= desde - 1e-6) & (t <= hasta + 1e-6)]


def primer_beat(info, t):
    b = beats_desde(info, t - 0.02, t + 10)
    return float(b[0]) if len(b) else t


def elegir_fin(t_cur, beats, deseado, disponible, beats_por_plano=None, en_beat=True):
    """Fin del plano (tiempo absoluto) que cae en un beat.

    beats: tiempos absolutos (salida) de los beats. Devuelve None si no entra ningun beat
    (el plano es mas corto que 1 beat: se usa tal cual y el siguiente corte re-sincroniza).
    """
    futuros = [b for b in beats if b > t_cur + 0.2 and b - t_cur <= disponible + 1e-6]
    if not futuros:
        return None
    if beats_por_plano:
        k = int(beats_por_plano)
        return futuros[k - 1] if len(futuros) >= k else futuros[-1]
    candidatos = futuros
    if en_beat:  # si estamos parados en un beat, preferir 1/2/4/8 beats
        sel = [futuros[k - 1] for k in PERMITIDOS if len(futuros) >= k]
        candidatos = sel or futuros
    return min(candidatos, key=lambda e: abs((e - t_cur) - deseado))


def encajar(info, desde, deseadas, disponibles=None, beats_por_plano=None):
    """Para CLI/pruebas: duraciones ajustadas al beat arrancando en el primer beat >= desde."""
    t0 = primer_beat(info, desde)
    disponibles = disponibles or [d * 3 for d in deseadas]
    beats = list(beats_desde(info, t0, t0 + sum(disponibles) + 30))
    t, out = t0, []
    for d, disp in zip(deseadas, disponibles):
        fin = elegir_fin(t, beats, d, disp, beats_por_plano, en_beat=any(abs(t - b) < 0.03 for b in beats))
        fin = fin if fin is not None else t + min(d, disp)
        out.append(round(fin - t, 3))
        t = fin
    return t0, out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analizar", help="BPM, beats y LUFS de un tema")
    a.add_argument("tema")
    a.add_argument("--cache")
    e = sub.add_parser("encajar", help="ajusta duraciones de planos al beat")
    e.add_argument("tema")
    e.add_argument("--desde", type=float, default=0.0)
    e.add_argument("--duraciones", required=True, help="ej: 2,1.5,3")
    e.add_argument("--disponibles", help="largo maximo de cada plano, ej: 5,5,5")
    e.add_argument("--beats-por-plano", type=int)
    e.add_argument("--cache")
    args = ap.parse_args()
    info = analizar(args.tema, args.cache)
    if args.cmd == "analizar":
        print(f"{os.path.basename(args.tema)}: {info['bpm']} BPM | {len(info['beats'])} beats | "
              f"{comun.tc(info['duracion'])} | {info['lufs']:.1f} LUFS | primeros beats "
              f"{[round(b, 2) for b in info['beats'][:8]]}")
    else:
        des = [float(x) for x in args.duraciones.split(",")]
        disp = [float(x) for x in args.disponibles.split(",")] if args.disponibles else None
        t0, out = encajar(info, args.desde, des, disp, args.beats_por_plano)
        bi = 60.0 / info["bpm"]
        print(f"arranca en {t0:.3f}s del tema | planos: " +
              ", ".join(f"{d:.2f}s ({d / bi:.1f} beats)" for d in out))


if __name__ == "__main__":
    main()
