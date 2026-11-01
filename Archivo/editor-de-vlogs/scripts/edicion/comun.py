"""Funciones compartidas por los scripts de edicion (vlog.json, ffmpeg, progreso).

No se corre solo: lo importan escanear.py, transcribir.py, plan.py, musica.py y render.py.
"""
import copy
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime
from fractions import Fraction

import numpy as np

# ---------- Valores por defecto (ver references/vlog_json.md) ----------
DEFAULTS = {
    "version": 1,
    "titulo": "Vlog",
    "material": {"clips": []},
    "historia": {"teaser": {"activo": True, "duracion_s": 20}, "capitulos_lugar_hora": True,
                 "notas": "", "bloques": []},
    "cortes": {"silencio_max_s": 0.25, "muletillas": True, "correcciones": True,
               "punch_in": True, "agresividad": "normal"},
    "color": {"looks": {"dlog": {"lut": "", "intensidad": 100},
                        "dlog2": {"lut": "", "intensidad": 100},
                        "rec709": {"lut": "", "intensidad": 100}},
              "barras": {"formato": None, "donde": "montajes"}},
    "audio": {"fuente_voz": "auto", "reducir_ruido": True, "ambiente_montajes_db": -18},
    "musica": {"temas": [], "en_charla": "nada", "fade_s": 4, "corte_en_beat": True,
               "volumen_montaje_db": -10},
    "textos": {"subtitulos": True, "titulo_episodio": {"activo": False, "numero": "", "texto": ""},
               "lugar_hora": True},
    "exportar": {"resolucion": "1080p", "lufs": -14, "preview": True},
    "revision": {"notas": []},
    "estado": {"paso": "", "versiones": []},
}

VIDEO_EXT = (".mp4", ".mov")


def _mezclar(base, extra):
    """Mezcla recursiva: lo de 'extra' pisa a 'base'. None en extra se respeta."""
    out = copy.deepcopy(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _mezclar(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def leer_json(path, defecto=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return copy.deepcopy(defecto)


def escribir_json(path, data):
    """Escritura atomica (archivo temporal + rename) para que la app nunca lea un json a medias."""
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=float)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def cargar_vlog(vlog_path):
    """Devuelve (crudo, cfg): crudo = lo que hay en disco, cfg = crudo + defaults."""
    crudo = leer_json(vlog_path, {})
    if crudo is None:
        sys.exit(f"No encuentro {vlog_path}")
    return crudo, _mezclar(DEFAULTS, crudo)


def actualizar_vlog(vlog_path, fn):
    """Relee vlog.json justo antes de escribir (la app puede haberlo cambiado), aplica fn(crudo)."""
    crudo = leer_json(vlog_path, {}) or {}
    fn(crudo)
    escribir_json(vlog_path, crudo)
    return crudo


def marcar_paso(vlog_path, paso):
    actualizar_vlog(vlog_path, lambda d: d.setdefault("estado", {}).__setitem__("paso", paso))


def dir_edicion(vlog_path):
    return os.path.dirname(os.path.abspath(vlog_path))


def carpeta_dia(vlog_path, cfg):
    c = cfg.get("carpeta")
    if c and os.path.isdir(c):
        return c
    return os.path.dirname(dir_edicion(vlog_path))


def repo_root():
    """Sube desde este script hasta encontrar el repo (carpeta con .git o Powergrade/)."""
    env = os.environ.get("EDITOR_VLOGS_REPO")
    if env:
        return env
    d = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.isdir(os.path.join(d, ".git")) or os.path.isdir(os.path.join(d, "Powergrade")):
            return d
        p = os.path.dirname(d)
        if p == d:
            return os.getcwd()
        d = p


LOG = None   # si se fija (abrir_log), las lineas PASO tambien van a _edicion/progreso.log


def abrir_log(edicion, script):
    """Arranca _edicion/progreso.log de cero para este script (la app/Claude lo pueden leer en vivo)."""
    global LOG
    LOG = os.path.join(edicion, "progreso.log")
    try:
        with open(LOG, "w", encoding="utf-8") as f:
            f.write(f"INICIO {script} {ahora()}\n")
    except OSError:
        LOG = None


def progreso(etapa, i, n, detalle=""):
    """Linea que la app lee para mostrar avance:  PASO <etapa> <i>/<n> <detalle>"""
    linea = f"PASO {etapa} {i}/{n} {detalle}".rstrip()
    print(linea, flush=True)
    if LOG:
        try:
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(linea + "\n")
        except OSError:
            pass


def fin_log(texto):
    """Ultima linea: 'FIN OK ...' o 'FIN ERROR ...'."""
    print(texto, flush=True)
    if LOG:
        try:
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(texto + "\n")
        except OSError:
            pass


def slug(texto, largo=40):
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Za-z0-9]+", "_", t).strip("_")
    return (t[:largo].rstrip("_") or "vlog")


def nombre_seguro(archivo):
    """'broll/x.mp4' -> 'broll__x.mp4' (para caches por clip)."""
    return archivo.replace("/", "__").replace("\\", "__")


def ahora():
    return datetime.now().replace(microsecond=0).isoformat()


# ---------- ffmpeg / ffprobe ----------
def correr(cmd, cwd=None, silencioso=True):
    """Corre un comando; si falla muestra el final de stderr y corta."""
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write("ERROR en: " + " ".join(cmd)[:1500] + "\n" + r.stderr[-3000:] + "\n")
        fin_log("FIN ERROR " + (r.stderr.strip().splitlines() or ["ffmpeg"])[-1][:300])
        raise SystemExit(1)
    return r


def ffprobe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format",
                        "-show_streams", path], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return json.loads(r.stdout)


def fps_frac(clip):
    """Fraccion exacta de fps del clip (fps_frac del escaneo o aproximacion del float)."""
    f = clip.get("fps_frac")
    if f:
        try:
            return Fraction(f)
        except (ValueError, ZeroDivisionError):
            pass
    x = float(clip.get("fps") or 30)
    for cand in (Fraction(24000, 1001), Fraction(30000, 1001), Fraction(60000, 1001),
                 Fraction(120000, 1001)):
        if abs(float(cand) - x) < 0.01:
            return cand
    return Fraction(x).limit_denominator(1001)


def decodificar_audio(path, sr=16000, canales=1, filtros=None):
    """Decodifica audio con ffmpeg a numpy float32 (evita el error de 'av' de faster-whisper)."""
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-i", path, "-vn"]
    if filtros:
        cmd += ["-af", filtros]
    cmd += ["-ac", str(canales), "-ar", str(sr), "-f", "f32le", "-"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        return np.zeros((0,) if canales == 1 else (0, canales), np.float32)
    a = np.frombuffer(r.stdout, np.float32)
    return a if canales == 1 else a.reshape(-1, canales)


def medir_lufs(entrada_args, filtros=None):
    """Loudness integrado (LUFS) y true peak (dBTP) con ebur128. entrada_args = ['-i', x] o raw."""
    af = (filtros + "," if filtros else "") + "ebur128=peak=true"
    r = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-nostats"] + entrada_args +
                       ["-af", af, "-f", "null", "-"], capture_output=True, text=True)
    txt = r.stderr
    resumen = txt[txt.rfind("Summary:"):] if "Summary:" in txt else txt
    mi = re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", resumen)
    mp = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", resumen)
    i = float(mi.group(1)) if mi and mi.group(1) != "-inf" else -70.0
    p = float(mp.group(1)) if mp and mp.group(1) != "-inf" else -70.0
    return i, p


def tc(seg):
    """Segundos -> 'm:ss.d'"""
    seg = max(0.0, float(seg))
    return f"{int(seg // 60)}:{seg % 60:04.1f}"


def tc_a_seg(txt):
    """'02:14' / '1:02:14' / '134.5' -> segundos"""
    partes = [float(p) for p in str(txt).strip().split(":")]
    s = 0.0
    for p in partes:
        s = s * 60 + p
    return s
