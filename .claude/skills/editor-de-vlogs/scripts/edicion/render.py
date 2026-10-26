#!/usr/bin/env python3
"""Renderiza _edicion/plan.json a _edicion/Vlog_<titulo>_vN.mp4 (nunca pisa versiones).

Uso:
  python3 render.py <vlog.json> [--preview] [--nota "texto"] [--conservar]

  --preview    960x540, x264 ultrafast crf 28 (rapido para revisar). Sin flag: resolucion de
               exportar.resolucion (1080p por defecto), crf 18.
  --nota       nota que queda en estado.versiones.
  --conservar  no borra la carpeta temporal _edicion/tmp_render_vN/.

Que hace (en orden):
  1. Audio de cada clip a 48 kHz (+ limpieza de ruido si audio.reducir_ruido) y su loudness.
  2. Video por TRAMOS (segmentos seguidos del mismo clip y bloque, un ffmpeg por tramo):
     recorte por frames, punch-in, escala a 16:9, LUT con % de intensidad (lut3d + blend),
     barras (drawbox), subtitulos / titulo / lugar-hora (ASS). Archivos intermedios + concat.
  3. Mezcla (numpy): voz emparejada a -20 LUFS por clip, ambiente de montajes a
     audio.ambiente_montajes_db, musica segun plan.musica (fades), fades de 5 ms en cada corte.
  4. Master: ganancia a exportar.lufs (-14) + limitador a -1 dBTP aprox, AAC.
  5. Agrega la version a estado.versiones y copia el plan a _edicion/planes/plan_vN.json.

Progreso: lineas 'PASO <etapa> <i>/<n> <detalle>' (etapas: audio, render, mezcla, master, listo).
"""
import argparse
import glob
import os
import re
import shutil
import sys
from fractions import Fraction

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402

SR = 48000
VOZ_LUFS = -20.0
RESOLUCIONES = {"720p": (1280, 720), "1080p": (1920, 1080), "1440p": (2560, 1440),
                "2160p": (3840, 2160), "4k": (3840, 2160)}


# ---------- utilidades ----------
def siguiente_version(ed, slug, versiones):
    n = 0
    for f in glob.glob(os.path.join(ed, f"Vlog_{slug}_v*.mp4")):
        m = re.search(r"_v(\d+)\.mp4$", f)
        if m:
            n = max(n, int(m.group(1)))
    for v in versiones or []:
        m = re.search(r"_v(\d+)\.mp4$", v.get("archivo", ""))
        if m:
            n = max(n, int(m.group(1)))
    return n + 1


def resolver_lut(ruta):
    if not ruta:
        return None
    for cand in (ruta, os.path.join(comun.repo_root(), ruta)):
        if os.path.isfile(cand):
            return cand
    return None


def par(n):
    return int(round(n / 2.0)) * 2


def ass_tiempo(t):
    t = max(0.0, t)
    cs = int(round(t * 100))
    return f"{cs // 360000}:{(cs // 6000) % 60:02d}:{(cs // 100) % 60:02d}.{cs % 100:02d}"


def ass_txt(s):
    return str(s).replace("\\", "/").replace("{", "(").replace("}", ")").replace("\n", " ")


# ---------- textos ----------
def eventos_subtitulos(segs):
    """Lineas de 4-7 palabras en tiempo de salida, a partir de las palabras de cada segmento de voz."""
    pal = []
    for s in segs:
        if s.get("audio") != "voz":
            continue
        for i, f, w in s.get("palabras", []):
            a = s["t"] + max(0.0, i - s["entrada"])
            b = s["t"] + min(s["dur"], f - s["entrada"])
            if b > a and w.strip():
                pal.append((a, b, w.strip()))
    eventos, linea = [], []
    for k, (a, b, w) in enumerate(pal):
        if linea:
            largo = len(" ".join(x[2] for x in linea + [(a, b, w)]))
            corte = (len(linea) >= 7 or largo > 38 or a - linea[-1][1] > 0.6 or
                     linea[-1][2][-1:] in ".?!" or (len(linea) >= 4 and linea[-1][2][-1:] == ","))
            if corte:
                eventos.append(linea)
                linea = []
        linea.append((a, b, w))
    if linea:
        eventos.append(linea)
    out = []
    for i, ln in enumerate(eventos):
        ini = ln[0][0]
        fin = ln[-1][1] + 0.2
        if i + 1 < len(eventos):
            fin = min(fin, eventos[i + 1][0][0])
        fin = max(fin, ini + 0.5)
        texto = " ".join(x[2] for x in ln).strip().rstrip(".,;")
        out.append({"t": ini, "fin": fin, "texto": texto})
    return out


def cabecera_ass(W, H, cfg):
    tx = cfg.get("textos", {})
    f_sub = tx.get("fuente", "Helvetica Neue")
    f_tit = tx.get("fuente_titulo", "Impact")
    s_sub = int(H * 0.034)
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{f_sub},{s_sub},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,{max(1, H // 900)},{max(1, H // 1100)},2,40,40,{int(H * 0.07)},1
Style: Titulo,{f_tit},{int(H * 0.13)},&H004848FF,&H004848FF,&H000000FF,&H00000000,1,0,0,0,92,100,4,0,1,2,0,5,40,40,40,1
Style: Lugar,{f_sub},{int(H * 0.036)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,2,0,1,{max(1, H // 1000)},0,4,{int(W * 0.08)},{int(W * 0.08)},0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def lineas_textos(textos, subs, T0, T1, W, H):
    """Eventos ASS que caen en [T0, T1) en tiempo relativo al tramo."""
    out = []

    def recorte(t, fin):
        a, b = max(t, T0), min(fin, T1)
        return (a - T0, b - T0, t >= T0, fin <= T1) if b > a + 0.02 else None

    for s in subs:
        r = recorte(s["t"], s["fin"])
        if r:
            out.append(f"Dialogue: 0,{ass_tiempo(r[0])},{ass_tiempo(r[1])},Sub,,0,0,0,,{ass_txt(s['texto'])}")
    for t in textos:
        r = recorte(t["t"], t["t"] + t["dur"])
        if not r:
            continue
        fi, fo = (300 if r[2] else 0), (400 if r[3] else 0)
        a, b = ass_tiempo(r[0]), ass_tiempo(r[1])
        if t["tipo"] == "titulo":
            num = ass_txt(t.get("numero", ""))
            txt = ass_txt(t.get("texto", "")).upper()
            linea = (r"{\fs" + str(int(H * 0.07)) + "}#" + num + r"\N{\fs" + str(int(H * 0.13)) + "}" + txt) if num else txt
            # capa 0 = glow (borde rojo difuminado), capa 1 = letra
            out.append(f"Dialogue: 0,{a},{b},Titulo,,0,0,0,,{{\\fad({fi},{fo})\\bord{max(4, H // 120)}\\blur{max(8, H // 70)}\\3c&H0000FF&\\1c&H0000FF&\\alpha&H30&}}{linea}")
            out.append(f"Dialogue: 1,{a},{b},Titulo,,0,0,0,,{{\\fad({fi},{fo})\\bord{max(1, H // 540)}\\blur2\\3c&H0010E0&}}{linea}")
        elif t["tipo"] == "lugar_hora":
            if t.get("lugar"):
                out.append(f"Dialogue: 0,{a},{b},Lugar,,0,0,0,,{{\\fad({fi},{fo})\\an4}}{ass_txt(t['lugar'])}")
            if t.get("hora"):
                out.append(f"Dialogue: 0,{a},{b},Lugar,,0,0,0,,{{\\fad({fi},{fo})\\an6}}{ass_txt(t['hora'])}")
    return out


# ---------- tramos ----------
def agrupar_tramos(segs):
    tramos = []
    for s in segs:
        p = tramos[-1][-1] if tramos else None
        if (p and p["clip"] == s["clip"] and p["bloque"] == s["bloque"] and p["tipo"] == s["tipo"]
                and s["entrada"] >= p["salida"] - 1e-4 and s["entrada"] - p["salida"] < 20):
            tramos[-1].append(s)
        else:
            tramos.append([s])
    return tramos


def filtro_tramo(tramo, clip, ss, W, H, fo, lut, opacidad, barras, ass):
    fc = comun.fps_frac(clip)
    h = 0.5 / float(fc)
    sel = "+".join(f"gte(t,{s['entrada'] - ss - h:.5f})*lt(t,{s['salida'] - ss - h:.5f})" for s in tramo)
    f = [f"[0:v]select='{sel}',setpts=N/({fc.numerator}/{fc.denominator}*TB)"]
    if fc != fo:
        f[0] += f",fps={fo.numerator}/{fo.denominator}"
    cw, ch = clip.get("ancho") or W, clip.get("alto") or H
    distinto = abs(cw / max(1, ch) - W / H) > 0.01
    zooms = [s for s in tramo if s.get("zoom", 1.0) > 1.001]

    def ajustar(w, h_):
        if distinto:
            return (f"scale={w}:{h_}:force_original_aspect_ratio=decrease:flags=bicubic,"
                    f"pad={w}:{h_}:(ow-iw)/2:(oh-ih)/2")
        return f"scale={w}:{h_}:flags=bicubic"

    t0 = tramo[0]["t"]
    if zooms:
        z = max(s["zoom"] for s in zooms)
        ZW, ZH = par(W * z), par(H * z)
        en = "+".join(f"between(t,{s['t'] - t0:.4f},{s['t'] - t0 + s['dur'] - 0.5 / float(fo):.4f})" for s in zooms)
        f[0] += f",{ajustar(ZW, ZH)},split[za][zb]"
        f.append(f"[za]scale={W}:{H}:flags=bicubic[zn]")
        f.append(f"[zb]crop={W}:{H}[zc]")
        f.append(f"[zn][zc]overlay=format=yuv420p10:enable='{en}'[base]")
    else:
        f[0] += f",{ajustar(W, H)}[base]"
    cadena = "[base]"
    if lut:
        cadena += "scale=in_color_matrix=bt709,format=gbrp16le,"
        if opacidad >= 0.999:
            cadena += f"lut3d=file={lut}:interp=tetrahedral,"
        else:
            f.append(cadena + f"split[o][l];[l]lut3d=file={lut}:interp=tetrahedral[g];"
                              f"[o][g]blend=all_mode=normal:all_opacity={opacidad:.3f}[gr]")
            cadena = "[gr]"
        cadena += "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,"
    else:
        cadena += "format=yuv420p,"
    if barras:
        cadena += (f"drawbox=x=0:y=0:w=iw:h={barras}:color=black:t=fill,"
                   f"drawbox=x=0:y=ih-{barras}:w=iw:h={barras}:color=black:t=fill,")
    if ass:
        cadena += f"subtitles=filename={ass},"
    cadena += "tpad=stop_mode=clone:stop_duration=5[out]"
    f.append(cadena)
    return ";".join(f)


def alto_barras(formato, W, H):
    if not formato:
        return 0
    try:
        a, b = str(formato).split(":") if ":" in str(formato) else (formato, 1)
        r = float(a) / float(b)
    except (ValueError, ZeroDivisionError):
        return 0
    visible = W / r
    return max(0, int(round((H - visible) / 2)))


# ---------- audio ----------
def retardo(a, b, max_lag=4800):
    """Muestras que 'b' esta atrasado respecto de 'a' (correlacion por FFT en 20 s con senal)."""
    n = min(len(a), len(b), SR * 20)
    if n < SR:
        return 0
    ini = int(np.argmax([np.sum(np.abs(a[k:k + n])) for k in range(0, max(1, len(a) - n), SR * 5)][:20])) * SR * 5
    x, y = a[ini:ini + n, 0], b[ini:ini + n, 0]
    L = 1 << int(np.ceil(np.log2(2 * n)))
    c = np.fft.irfft(np.fft.rfft(y, L) * np.conj(np.fft.rfft(x, L)), L)
    c = np.concatenate([c[-max_lag:], c[:max_lag + 1]])
    return int(np.argmax(c)) - max_lag


def extraer_audio(clip, carpeta, tmp, limpiar):
    """Audio del clip a f32 estereo 48 kHz alineado al video. La limpieza (afftdn) mete un retardo:
    se mide contra el audio original y se compensa."""
    dst = os.path.join(tmp, "audio", comun.nombre_seguro(clip["archivo"]) + ".f32")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst):
        crudo = dst + ".crudo"
        r = comun.subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-i", os.path.join(carpeta, clip["archivo"]),
                                  "-vn", "-af", "aresample=async=1:first_pts=0", "-ac", "2", "-ar", str(SR),
                                  "-f", "f32le", crudo], capture_output=True, text=True)
        if r.returncode != 0:
            open(crudo, "wb").close()
        if limpiar and os.path.getsize(crudo) > SR * 8:
            comun.correr(["ffmpeg", "-v", "error", "-nostdin", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2",
                          "-i", crudo, "-af", "highpass=f=70,afftdn=nf=-25", "-f", "f32le", dst])
            a = np.memmap(crudo, dtype=np.float32, mode="r").reshape(-1, 2)
            b = np.fromfile(dst, dtype=np.float32).reshape(-1, 2)
            lag = retardo(a, b)
            if lag > 0:
                b = np.concatenate([b[lag:], np.zeros((lag, 2), np.float32)])
                b.tofile(dst)
            del a
            os.remove(crudo)
        else:
            os.replace(crudo, dst)
    if os.path.getsize(dst) < SR * 8 * 0.2:
        return dst, -70.0
    lufs, _ = comun.medir_lufs(["-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", dst])
    return dst, lufs


def leer_tema(path, cache):
    if path not in cache:
        cache[path] = comun.decodificar_audio(path, sr=SR, canales=2)
    return cache[path]


def mezclar(plan, cfg, audios, tmp, fo):
    total_frames = sum(s["frames"] for s in plan["segmentos"])
    NS = int(round(total_frames / float(fo) * SR))
    mix = np.memmap(os.path.join(tmp, "mezcla.f32"), dtype=np.float32, mode="w+", shape=(max(NS, 1), 2))
    amb = float(cfg["audio"].get("ambiente_montajes_db", -18))
    cues = plan.get("musica", [])
    rampa = int(SR * 0.005)
    F = 0
    for s in plan["segmentos"]:
        a0 = int(round(F / float(fo) * SR))
        F += s["frames"]
        a1 = int(round(F / float(fo) * SR))
        n = a1 - a0
        ruta, lufs = audios.get(s["clip"], (None, -70.0))
        if not ruta or n <= 0 or lufs <= -60:
            continue
        src = np.memmap(ruta, dtype=np.float32, mode="r").reshape(-1, 2)
        i0 = int(round(s["entrada"] * SR))
        trozo = np.zeros((n, 2), np.float32)
        disp = src[i0:i0 + n]
        trozo[:len(disp)] = disp
        g = float(np.clip(VOZ_LUFS - lufs, -15, 24))
        if s["audio"] != "voz":
            con_musica = any(c["t"] < s["t"] + s["dur"] and c["t"] + c["dur"] > s["t"] for c in cues)
            g += amb if con_musica else -6.0
        trozo *= 10 ** (g / 20)
        if n > 2 * rampa:   # micro-fade para que el corte no haga "click"
            r = np.linspace(0, 1, rampa, dtype=np.float32)[:, None]
            trozo[:rampa] *= r
            trozo[-rampa:] *= r[::-1]
        mix[a0:a1] += trozo
    cache = {}
    for k, c in enumerate(cues, 1):
        comun.progreso("mezcla", k, len(cues), os.path.basename(c["tema"]))
        if not os.path.exists(c["tema"]):
            continue
        tema = leer_tema(c["tema"], cache)
        if len(tema) == 0:
            continue
        a0 = int(round(c["t"] * SR))
        n = min(int(round(c["dur"] * SR)), NS - a0)
        if n <= 0:
            continue
        idx = (int(round(c["desde"] * SR)) + np.arange(n)) % len(tema)   # loop si el tema se termina
        trozo = tema[idx].astype(np.float32)
        lufs_t = c.get("lufs_tema", -14) if c.get("lufs_tema", -70) > -60 else -14
        env = np.full(n, 10 ** ((c["nivel_db"] - lufs_t) / 20), np.float32)
        fi, fo_ = int(c["fade_in"] * SR), int(c["fade_out"] * SR)
        if fi > 0:
            env[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)
        if fo_ > 0:   # fade out lineal en dB (0 a -48 dB): la musica se aparta rapido de la voz
            curva = 10 ** (-48 * np.linspace(0, 1, fo_, dtype=np.float32) / 20) if fo_ > SR // 2 else \
                np.linspace(1, 0, fo_, dtype=np.float32)
            curva[-1] = 0
            env[-fo_:] *= curva
        mix[a0:a0 + n] += trozo * env[:, None]
    mix.flush()
    return os.path.join(tmp, "mezcla.f32"), NS


# ---------- principal ----------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("vlog")
    ap.add_argument("--preview", action="store_true", help="960x540 rapido")
    ap.add_argument("--nota", default="")
    ap.add_argument("--conservar", action="store_true", help="no borrar los temporales")
    args = ap.parse_args()

    vlog = os.path.abspath(args.vlog)
    raw, cfg = comun.cargar_vlog(vlog)
    ed = comun.dir_edicion(vlog)
    carpeta = comun.carpeta_dia(vlog, cfg)
    plan_path = os.path.join(ed, "plan.json")
    if not os.path.exists(plan_path):
        import plan as plan_mod
        plan_mod.armar(vlog)
    plan = comun.leer_json(plan_path)
    if not plan or not plan.get("segmentos"):
        sys.exit("El plan no tiene segmentos (revisar historia / clips descartados)")
    comun.marcar_paso(vlog, "exportar")
    comun.abrir_log(ed, "render")

    fo = Fraction(plan["fps"])
    if args.preview:
        W, H, preset, crf, abr = 960, 540, "ultrafast", "28", "160k"
    else:
        W, H = RESOLUCIONES.get(str(cfg["exportar"].get("resolucion", "1080p")).lower(), (1920, 1080))
        preset, crf, abr = cfg["exportar"].get("preset", "medium"), str(cfg["exportar"].get("crf", 18)), "320k"
    slug = comun.slug(cfg.get("titulo", "vlog"))
    N = siguiente_version(ed, slug, cfg["estado"].get("versiones"))
    nombre = f"Vlog_{slug}_v{N}.mp4"
    salida = os.path.join(ed, nombre)
    tmp = os.path.join(ed, f"tmp_render_v{N}")
    os.makedirs(tmp, exist_ok=True)
    clips = {c["archivo"]: c for c in cfg["material"]["clips"]}

    # LUTs por perfil (copiadas a tmp con nombre simple: evita lios de espacios en el filtro)
    luts = {}
    for perfil, look in (cfg["color"].get("looks") or {}).items():
        ruta = resolver_lut((look or {}).get("lut"))
        if (look or {}).get("lut") and not ruta:
            print(f"AVISO no encuentro la LUT {look.get('lut')} ({perfil}): va sin LUT", flush=True)
        inten = float((look or {}).get("intensidad", 100)) / 100.0
        if ruta and inten > 0.001:
            shutil.copy(ruta, os.path.join(tmp, f"lut_{perfil}.cube"))
            luts[perfil] = (f"lut_{perfil}.cube", min(1.0, inten))
    barras_cfg = cfg["color"].get("barras") or {}
    bh = alto_barras(barras_cfg.get("formato"), W, H)
    donde = barras_cfg.get("donde", "montajes")

    # 1. audio por clip
    usados = sorted({s["clip"] for s in plan["segmentos"]})
    audios = {}
    for i, a in enumerate(usados, 1):
        comun.progreso("audio", i, len(usados), a)
        if clips.get(a, {}).get("audio", True):
            audios[a] = extraer_audio(clips[a], carpeta, tmp, cfg["audio"].get("reducir_ruido", True))

    # 2. video por tramos
    subs = eventos_subtitulos(plan["segmentos"]) if cfg["textos"].get("subtitulos", True) else []
    textos = plan.get("textos", [])
    tramos = agrupar_tramos(plan["segmentos"])
    hw = ["-hwaccel", "videotoolbox"] if sys.platform == "darwin" and os.environ.get("EDITOR_VLOGS_HWACCEL", "1") != "0" else []
    lista = []
    for i, tr in enumerate(tramos, 1):
        comun.progreso("render", i, len(tramos), f"{tr[0]['clip']} {comun.tc(tr[0]['entrada'])}")
        clip = clips[tr[0]["clip"]]
        T0 = tr[0]["t"]
        T1 = tr[-1]["t"] + tr[-1]["dur"]
        nfr = sum(s["frames"] for s in tr)
        eventos = lineas_textos(textos, subs, T0, T1, W, H)
        ass = None
        if eventos:
            ass = f"tramo_{i:04d}.ass"
            with open(os.path.join(tmp, ass), "w", encoding="utf-8") as f:
                f.write(cabecera_ass(W, H, cfg) + "\n".join(eventos) + "\n")
        lut = luts.get(tr[0].get("perfil") or clip.get("perfil"))
        barras = bh if (bh and (donde == "todo" or tr[0]["tipo"] in ("teaser", "montaje"))) else 0
        ss = max(0.0, tr[0]["entrada"] - 0.5)
        tt = tr[-1]["salida"] - ss + 0.5
        grafo = filtro_tramo(tr, clip, ss, W, H, fo, lut[0] if lut else None, lut[1] if lut else 1.0, barras, ass)
        out = f"tramo_{i:04d}.mp4"
        cmd = (["ffmpeg", "-v", "error", "-nostdin", "-y"] + hw +
               ["-ss", f"{ss:.4f}", "-t", f"{tt:.4f}", "-i", os.path.join(carpeta, clip["archivo"]),
                "-filter_complex", grafo, "-map", "[out]", "-frames:v", str(nfr),
                "-c:v", "libx264", "-preset", preset, "-crf", crf, "-pix_fmt", "yuv420p",
                "-r", f"{fo.numerator}/{fo.denominator}", "-an",
                "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
                out])
        comun.correr(cmd, cwd=tmp)
        lista.append(out)
    with open(os.path.join(tmp, "lista.txt"), "w") as f:
        f.write("".join(f"file '{x}'\n" for x in lista))
    comun.correr(["ffmpeg", "-v", "error", "-nostdin", "-y", "-f", "concat", "-safe", "0", "-i", "lista.txt",
                  "-c", "copy", "video.mp4"], cwd=tmp)

    # 3. mezcla
    comun.progreso("mezcla", 0, max(1, len(plan.get("musica", []))), "voz y ambiente")
    mix, NS = mezclar(plan, cfg, audios, tmp, fo)
    raw_in = ["-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", mix]

    # 4. master: ganancia + limitador, 2 mediciones para clavar el LUFS
    objetivo = float(cfg["exportar"].get("lufs", -14))

    def limitador(lim):   # sobremuestreado x4 para frenar tambien los picos entre muestras
        return f"aresample=192000,alimiter=limit={lim:.4f}:level=0:attack=5:release=60,aresample={SR}"
    lim = 0.84
    comun.progreso("master", 1, 3, "midiendo loudness")
    i1, _ = comun.medir_lufs(raw_in)
    g = objetivo - i1 if i1 > -69 else 0.0
    comun.progreso("master", 2, 3, f"ajuste {g:+.1f} dB")
    i2, _ = comun.medir_lufs(raw_in, f"volume={g:.2f}dB,{limitador(lim)}")
    if i2 > -69:
        g += objetivo - i2
    for intento in range(3):
        comun.progreso("master", 3, 3, "exportando" + (f" (reintento {intento})" if intento else ""))
        comun.correr(["ffmpeg", "-v", "error", "-nostdin", "-y", "-i", os.path.join(tmp, "video.mp4")] + raw_in +
                     ["-map", "0:v", "-map", "1:a", "-af", f"volume={g:.2f}dB,{limitador(lim)}", "-c:v", "copy",
                      "-c:a", "aac", "-b:a", abr, "-ar", str(SR), "-movflags", "+faststart", salida])
        lufs_f, pico_f = comun.medir_lufs(["-i", salida])
        if pico_f <= -1.0:
            break
        if abs(objetivo - lufs_f) > 0.3:
            g += objetivo - lufs_f
        lim *= 10 ** ((-1.0 - pico_f - 0.2) / 20)   # el AAC sube algo los picos: bajar el techo y repetir
    info = comun.ffprobe(salida)
    dur = float(info["format"]["duration"]) if info else 0.0

    # 5. versiones (nunca se pisa nada)
    os.makedirs(os.path.join(ed, "planes"), exist_ok=True)
    shutil.copy(plan_path, os.path.join(ed, "planes", f"plan_v{N}.json"))
    entrada = {"archivo": f"_edicion/{nombre}", "fecha": comun.ahora(), "nota": args.nota,
               "preview": bool(args.preview), "resolucion": f"{W}x{H}", "duracion": round(dur, 2),
               "lufs": round(lufs_f, 1), "plan": f"_edicion/planes/plan_v{N}.json"}

    def guardar(d):
        d.setdefault("estado", {}).setdefault("versiones", []).append(entrada)
        d["estado"]["paso"] = "revision"
    comun.actualizar_vlog(vlog, guardar)
    if not args.conservar:
        shutil.rmtree(tmp, ignore_errors=True)
    comun.progreso("listo", 1, 1, nombre)
    comun.fin_log(f"FIN OK render _edicion/{nombre}")
    print(f"OK {salida} | {comun.tc(dur)} | {W}x{H} | {lufs_f:.1f} LUFS | pico {pico_f:.1f} dBTP | v{N}", flush=True)


if __name__ == "__main__":
    main()
