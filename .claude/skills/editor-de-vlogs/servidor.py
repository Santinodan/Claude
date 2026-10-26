#!/usr/bin/env python3
"""Servidor local del Editor de Vlogs.

Sirve la app, guarda vlog.json en la carpeta del dia y lanza a Claude Code
(`claude -p "/editor-de-vlogs ..."`) mostrando el avance en vivo.

Uso:  python3 .claude/skills/editor-de-vlogs/servidor.py  [--puerto 8787]
Solo escucha en 127.0.0.1 (tu Mac). Abri http://localhost:8787
"""
import argparse, json, os, shutil, subprocess, sys, threading, time, uuid, mimetypes, re
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

SKILL = Path(__file__).resolve().parent
REPO = SKILL.parents[2]
APP = SKILL / "app"
SCRIPTS = SKILL / "scripts" / "edicion"
HERRAMIENTAS = ["Read", "Write", "Edit", "Glob", "Grep",
                "Bash(ffmpeg *)", "Bash(ffprobe *)", "Bash(python3 *)", "Bash(ls *)", "Bash(mkdir *)"]

PERFILES = Path(os.environ.get("EDITOR_VLOGS_PERFILES") or REPO / "Perfiles")  # para pruebas se puede apuntar a otra carpeta
JOBS = {}          # id -> {"eventos": [...], "proc": Popen, "fin": bool}
LOCK = threading.Lock()


# ---------- vlog.json ----------
def ruta_vlog(carpeta):
    return Path(carpeta).expanduser() / "_edicion" / "vlog.json"

def leer_vlog(carpeta):
    p = ruta_vlog(carpeta)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None

def guardar_vlog(carpeta, vlog):
    p = ruta_vlog(carpeta)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(vlog, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


# ---------- perfiles y looks ----------
import base64, unicodedata

def slug(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", t).strip("_") or "x"

def leer_perfil(pid):
    p = PERFILES / pid / "perfil.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

def guardar_perfil(perfil):
    d = PERFILES / perfil["id"]
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "perfil.tmp"
    tmp.write_text(json.dumps(perfil, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(d / "perfil.json")
    return perfil

def listar_perfiles():
    if not PERFILES.exists():
        return []
    out = []
    for d in sorted(PERFILES.iterdir()):
        p = leer_perfil(d.name) if d.is_dir() else None
        if p:
            out.append(p)
    return out

def rel(p: Path):
    """Ruta relativa al repo (asi la app la sirve por /repo/). Si esta fuera del repo, absoluta."""
    try:
        return str(p.resolve().relative_to(REPO))
    except ValueError:
        return str(p.resolve())

def guardar_dataurl(dataurl, destino: Path):
    """Guarda una imagen data:image/...;base64 como archivo. Devuelve ruta relativa al repo."""
    cab, _, datos = dataurl.partition(",")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(base64.b64decode(datos))
    return rel(destino)

def perfil_inicial():
    """Primer arranque: perfil 'Snati' con las LUTs aprobadas del repo."""
    if listar_perfiles():
        return
    looks = [
        ("ma_vivo_dia", "MA Vivo Día", "dlog", "Powergrade/D-Log/MA_Vivo_DLog_DIA.cube"),
        ("ma_vivo_noche", "MA Vivo Noche", "dlog", "Powergrade/D-Log/MA_Vivo_DLog_NOCHE.cube"),
        ("high_ticket", "High Ticket", "dlog", "Powergrade/High Ticket/High_Ticket_DLog.cube"),
        ("ma_vivo_dia_dl2", "MA Vivo Día", "dlog2", "Powergrade/D-Log 2 (sin probar)/MA_Vivo_DLog2_DIA.cube"),
        ("ma_vivo_noche_dl2", "MA Vivo Noche", "dlog2", "Powergrade/D-Log 2 (sin probar)/MA_Vivo_DLog2_NOCHE.cube"),
        ("high_ticket_dl2", "High Ticket", "dlog2", "Powergrade/High Ticket/High_Ticket_DLog2.cube"),
        ("high_ticket_709", "High Ticket", "rec709", "Powergrade/High Ticket/High_Ticket_Rec709.cube"),
    ]
    guardar_perfil({"id": "Snati", "nombre": "Snati", "color": "#C96442", "foto": None,
                    "camara": "DJI Osmo Pocket 4P",
                    "looks": [{"id": i, "nombre": n, "perfil_camara": c, "archivo": a, "intensidad": 100,
                               "foto": None, "foto_antes": None} for i, n, c, a in looks],
                    "predeterminados": {"dlog": "ma_vivo_dia", "dlog2": "ma_vivo_dia_dl2", "rec709": "high_ticket_709"},
                    "ajustes": {"barras": {"formato": "2.22:1", "donde": "montajes"}},
                    "proyectos": []})

def resumen_proyecto(carpeta):
    v = leer_vlog(carpeta)
    if not v:
        return {"carpeta": carpeta, "disponible": False}
    clips = v.get("material", {}).get("clips", [])
    thumb = next((c.get("thumb") for c in clips if c.get("thumb") and not c.get("descartado")), None)
    vers = v.get("estado", {}).get("versiones", [])
    return {"carpeta": carpeta, "disponible": True, "titulo": v.get("titulo", ""), "fecha": v.get("fecha", ""),
            "paso": v.get("estado", {}).get("paso", ""), "clips": len(clips), "versiones": len(vers),
            "thumb": str(Path(carpeta) / thumb) if thumb else None}


# ---------- linea de tiempo ----------
import hashlib

def ruta_plan(carpeta):
    return Path(carpeta).expanduser() / "_edicion" / "plan.json"

def guardar_plan(carpeta, plan):
    p = ruta_plan(carpeta)
    if p.exists():                      # la primera vez que se toca a mano, se guarda la version de Claude
        viejo = json.loads(p.read_text(encoding="utf-8"))
        if not viejo.get("editado_a_mano"):
            (p.parent / "planes").mkdir(exist_ok=True)
            shutil.copy(p, p.parent / "planes" / f"plan_claude_{time.strftime('%Y%m%d_%H%M%S')}.json")
    plan["editado_a_mano"] = True
    plan["editado"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)

def ondas(archivo, por_seg=20):
    """Picos del audio (0..1), por_seg valores por segundo. Se cachean."""
    f = Path(archivo).expanduser()
    if not f.is_file():
        return None
    clave = hashlib.sha1(f"{f}|{f.stat().st_mtime}|{por_seg}".encode()).hexdigest()[:16]
    cache = Path.home() / ".cache" / "editor_vlogs" / "ondas" / f"{clave}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    sr = por_seg * 50
    r = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(f), "-vn", "-ac", "1", "-ar", str(sr),
                        "-f", "f32le", "-"], capture_output=True)
    import array
    a = array.array("f"); a.frombytes(r.stdout[: len(r.stdout) // 4 * 4])
    picos = [round(min(1.0, max((abs(x) for x in a[i:i + 50]), default=0) * 1.4), 3) for i in range(0, len(a), 50)]
    out = {"por_seg": por_seg, "picos": picos}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out))
    return out

def lanzar_render(carpeta, preview):
    vp = ruta_vlog(carpeta)
    job = uuid.uuid4().hex[:10]
    JOBS[job] = {"eventos": [], "proc": None, "fin": False}
    def emitir(ev):
        ev["t"] = time.time()
        with LOCK:
            JOBS[job]["eventos"].append(ev)
    def correr():
        cmd = [sys.executable, str(SCRIPTS / "render.py"), str(vp)] + (["--preview"] if preview else []) + ["--nota", "desde la linea de tiempo"]
        proc = subprocess.Popen(cmd, cwd=str(REPO), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        JOBS[job]["proc"] = proc
        emitir({"tipo": "inicio", "texto": "Exportando " + ("preview" if preview else "versión final")})
        threading.Thread(target=seguir_progreso, args=(vp.parent / "progreso.log", job, emitir), daemon=True).start()
        ultimas = []
        for l in proc.stdout:
            ultimas = (ultimas + [l.strip()])[-8:]
        code = proc.wait()
        ok = code == 0
        emitir({"tipo": "fin", "ok": ok, "texto": ultimas[-1] if ok and ultimas else ("\n".join(ultimas) if not ok else "")})
        JOBS[job]["fin"] = True
    threading.Thread(target=correr, daemon=True).start()
    return job


# ---------- elegir carpetas y archivos ----------
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mts", ".mxf"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".aif", ".aiff", ".flac", ".ogg"}

def elegir_nativo(modo, titulo):
    """Selector de macOS (Finder). Devuelve ruta, "" si cancela, o None si no hay selector nativo."""
    if sys.platform != "darwin":
        return None
    titulo = (titulo or "Elegí").replace('"', "'")
    if modo == "archivo":
        orden = f'choose file with prompt "{titulo}" of type {{"public.audio"}}'
    else:
        orden = f'choose folder with prompt "{titulo}"'
    script = f'tell application "System Events"\nactivate\nset f to {orden}\nend tell\nPOSIX path of f'
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        return ""            # cancelado
    return r.stdout.strip().rstrip("/") or "/"

def explorar(carpeta, modo):
    """Lista carpetas (y audios si modo=archivo) para el explorador de la app."""
    d = Path(carpeta).expanduser() if carpeta else Path.home()
    if not d.is_dir():
        d = Path.home()
    carpetas, archivos, videos = [], [], 0
    try:
        for x in sorted(d.iterdir(), key=lambda x: x.name.lower()):
            if x.name.startswith("."):
                continue
            if x.is_dir():
                carpetas.append(x.name)
            elif x.suffix.lower() in VIDEO_EXT:
                videos += 1
            elif modo == "archivo" and x.suffix.lower() in AUDIO_EXT:
                archivos.append(x.name)
    except PermissionError:
        pass
    raices = [str(Path.home())] + ([str(v) for v in sorted(Path("/Volumes").iterdir())] if Path("/Volumes").is_dir() else [])
    return {"dir": str(d), "padre": str(d.parent) if d.parent != d else None, "carpetas": carpetas,
            "archivos": archivos, "videos": videos, "raices": raices}


# ---------- Claude Code ----------
def version_claude():
    exe = shutil.which("claude")
    if not exe:
        return None
    try:
        return subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=15).stdout.strip() or "instalado"
    except Exception:
        return "instalado"

def resumir_herramienta(nombre, entrada):
    if nombre == "Bash":
        cmd = entrada.get("command", "")
        return entrada.get("description") or cmd[:140]
    for k in ("file_path", "path", "pattern"):
        if k in entrada:
            return str(entrada[k])
    return ""

def seguir_progreso(log, job, emitir):
    """Los scripts escriben _edicion/progreso.log (PASO etapa i/n ...). Lo leemos en vivo
    porque en claude -p la salida de Bash llega recien cuando termina cada comando."""
    vistos = set()
    while not JOBS[job]["fin"]:
        try:
            for l in log.read_text(encoding="utf-8", errors="ignore").splitlines():
                l = l.strip()
                if l.startswith(("PASO", "FIN")) and l not in vistos:
                    vistos.add(l)
                    emitir({"tipo": "paso" if l.startswith("PASO") else ("fin_paso" if "OK" in l else "error"), "texto": l})
                elif l.startswith("INICIO"):
                    vistos = {x for x in vistos if not x.startswith(("PASO", "FIN"))} | {l}
        except FileNotFoundError:
            pass
        time.sleep(1.5)


def lanzar_claude(carpeta, pedido):
    vp = ruta_vlog(carpeta)
    sesion_f = vp.parent / "claude_sesion.txt"
    prompt = f'/editor-de-vlogs {vp} {pedido}'.strip()
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--permission-mode", "acceptEdits", "--allowedTools", *HERRAMIENTAS]
    if sesion_f.exists():
        cmd += ["--resume", sesion_f.read_text().strip()]
    job = uuid.uuid4().hex[:10]
    JOBS[job] = {"eventos": [], "proc": None, "fin": False}

    def emitir(ev):
        ev["t"] = time.time()
        with LOCK:
            JOBS[job]["eventos"].append(ev)

    def correr():
        try:
            proc = subprocess.Popen(cmd, cwd=str(REPO), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, bufsize=1)
        except FileNotFoundError:
            emitir({"tipo": "error", "texto": "No encontré Claude Code. Instalalo y logueate (ver LEEME)."})
            JOBS[job]["fin"] = True
            return
        JOBS[job]["proc"] = proc
        emitir({"tipo": "inicio", "texto": "Claude Code arrancó"})
        threading.Thread(target=seguir_progreso, args=(vp.parent / "progreso.log", job, emitir), daemon=True).start()
        for linea in proc.stdout:
            linea = linea.strip()
            if not linea:
                continue
            try:
                m = json.loads(linea)
            except json.JSONDecodeError:
                continue
            tipo = m.get("type")
            if tipo == "system" and m.get("subtype") == "init":
                emitir({"tipo": "inicio", "texto": f"Modelo {m.get('model', '')}"})
            elif tipo == "assistant":
                for b in m.get("message", {}).get("content", []):
                    if b.get("type") == "text" and b.get("text", "").strip():
                        emitir({"tipo": "texto", "texto": b["text"]})
                    elif b.get("type") == "tool_use":
                        emitir({"tipo": "herramienta", "nombre": b.get("name"),
                                "texto": resumir_herramienta(b.get("name"), b.get("input", {}))})
            elif tipo == "user":
                for b in m.get("message", {}).get("content", []) if isinstance(m.get("message", {}).get("content"), list) else []:
                    if b.get("type") == "tool_result":
                        c = b.get("content")
                        txt = c if isinstance(c, str) else " ".join(x.get("text", "") for x in (c or []) if isinstance(x, dict))
                        for paso in re.findall(r"PASO [^\n]+", txt or "")[-3:]:
                            emitir({"tipo": "paso", "texto": paso})
            elif tipo == "result":
                sid = m.get("session_id")
                if sid:
                    sesion_f.parent.mkdir(parents=True, exist_ok=True)
                    sesion_f.write_text(sid)
                emitir({"tipo": "fin", "ok": not m.get("is_error"), "texto": m.get("result", ""),
                        "costo": m.get("total_cost_usd")})
        err = proc.stderr.read()
        code = proc.wait()
        if code != 0 and err.strip():
            emitir({"tipo": "error", "texto": err.strip()[-600:]})
        JOBS[job]["fin"] = True

    threading.Thread(target=correr, daemon=True).start()
    return job


# ---------- HTTP ----------
class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def _archivo(self, p: Path):
        if not p.is_file():
            return self._json({"error": "no existe"}, 404)
        tam = p.stat().st_size
        tipo = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        rng = self.headers.get("Range")
        ini, fin = 0, tam - 1
        if rng and rng.startswith("bytes="):
            a, _, b = rng[6:].partition("-")
            ini = int(a) if a else 0
            fin = int(b) if b else min(tam - 1, ini + 8 * 1024 * 1024)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {ini}-{fin}/{tam}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(fin - ini + 1))
        self.end_headers()
        with open(p, "rb") as f:
            f.seek(ini)
            resto = fin - ini + 1
            try:
                while resto > 0:
                    chunk = f.read(min(1 << 20, resto))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    resto -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def do_GET(self):
        u = urlparse(self.path)
        u = u._replace(path=unquote(u.path))   # "High%20Ticket" -> "High Ticket"
        q = parse_qs(u.query)
        if u.path in ("/", "/index.html"):
            return self._archivo(APP / "index.html")
        if u.path.startswith("/app/"):
            return self._archivo(APP / u.path[5:])
        if u.path.startswith("/repo/"):            # LUTs y otros archivos del repo
            p = (REPO / u.path[6:]).resolve()
            if REPO in p.parents:
                return self._archivo(p)
            return self._json({"error": "fuera del repo"}, 403)
        if u.path == "/media":                    # clips, miniaturas, musica, versiones
            return self._archivo(Path(q.get("p", [""])[0]).expanduser())
        if u.path == "/api/estado":
            return self._json({"servidor": True, "claude": version_claude(),
                               "ffmpeg": bool(shutil.which("ffmpeg")), "repo": str(REPO)})
        if u.path == "/api/vlog":
            return self._json({"vlog": leer_vlog(q.get("carpeta", [""])[0])})
        if u.path == "/api/plan":
            p = ruta_plan(q.get("carpeta", [""])[0])
            return self._json({"plan": json.loads(p.read_text(encoding="utf-8")) if p.exists() else None})
        if u.path == "/api/ondas":
            o = ondas(q.get("p", [""])[0])
            return self._json(o or {"error": "no existe"}, 200 if o else 404)
        if u.path == "/api/perfiles":
            return self._json({"perfiles": listar_perfiles()})
        if u.path == "/api/explorar":
            return self._json(explorar(q.get("dir", [""])[0], q.get("modo", ["carpeta"])[0]))
        if u.path == "/api/proyectos":
            p = leer_perfil(q.get("perfil", [""])[0]) or {}
            return self._json({"proyectos": [resumen_proyecto(c) for c in p.get("proyectos", [])]})
        if u.path == "/api/claude/eventos":       # Server-Sent Events con el avance
            job = q.get("job", [""])[0]
            if job not in JOBS:
                return self._json({"error": "trabajo no encontrado"}, 404)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            i = 0
            try:
                while True:
                    with LOCK:
                        nuevos = JOBS[job]["eventos"][i:]
                    for ev in nuevos:
                        self.wfile.write(f"data: {json.dumps(ev, ensure_ascii=False)}\n\n".encode())
                    i += len(nuevos)
                    self.wfile.flush()
                    if JOBS[job]["fin"] and not nuevos:
                        self.wfile.write(b"event: fin\ndata: {}\n\n")
                        break
                    time.sleep(0.4)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return
        return self._json({"error": "no existe"}, 404)

    def do_POST(self):
        u = urlparse(self.path)
        d = self._body()
        carpeta = d.get("carpeta", "")
        if u.path == "/api/vlog":
            if not carpeta or not Path(carpeta).expanduser().is_dir():
                return self._json({"error": "La carpeta no existe"}, 400)
            guardar_vlog(carpeta, d["vlog"])
            pf = leer_perfil(d["vlog"].get("perfil") or "")
            if pf and carpeta not in pf.setdefault("proyectos", []):   # el proyecto queda en el perfil
                pf["proyectos"].insert(0, carpeta)
                guardar_perfil(pf)
            return self._json({"ok": True})
        if u.path == "/api/elegir":
            r = elegir_nativo(d.get("modo", "carpeta"), d.get("titulo"))
            return self._json({"nativo": r is not None, "ruta": r or None})
        if u.path == "/api/plan":
            if not ruta_plan(carpeta).parent.is_dir():
                return self._json({"error": "La carpeta no existe"}, 400)
            guardar_plan(carpeta, d["plan"])
            return self._json({"ok": True})
        if u.path == "/api/render":
            if not ruta_plan(carpeta).exists():
                return self._json({"error": "Todavía no hay edición para exportar"}, 400)
            return self._json({"job": lanzar_render(carpeta, bool(d.get("preview", True)))})
        if u.path == "/api/perfil":
            p = d["perfil"]
            if not p.get("id"):
                base = slug(p.get("nombre") or "perfil"); p["id"] = base; i = 2
                while (PERFILES / p["id"]).exists():
                    p["id"] = f"{base}_{i}"; i += 1
            if d.get("foto"):
                p["foto"] = guardar_dataurl(d["foto"], PERFILES / p["id"] / f"avatar_{int(time.time())}.jpg")
            return self._json({"perfil": guardar_perfil(p)})
        if u.path == "/api/look":
            p = leer_perfil(d["perfil_id"])
            if not p:
                return self._json({"error": "Perfil no encontrado"}, 404)
            look = d["look"]
            if not look.get("id"):
                look["id"] = slug(look.get("nombre", "look")).lower() + "_" + uuid.uuid4().hex[:4]
            base = PERFILES / p["id"]
            if d.get("cube"):                         # LUT subida: se guarda en el perfil
                destino = base / "luts" / (slug(look.get("archivo_original") or look["nombre"]) + ".cube")
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_text(d["cube"], encoding="utf-8")
                look["archivo"] = rel(destino)
            stamp = int(time.time())
            if d.get("foto"):
                look["foto"] = guardar_dataurl(d["foto"], base / "fotos" / f"{look['id']}_{stamp}.jpg")
            if d.get("foto_antes"):
                look["foto_antes"] = guardar_dataurl(d["foto_antes"], base / "fotos" / f"{look['id']}_{stamp}_antes.jpg")
            look.pop("archivo_original", None)
            looks = [x for x in p.get("looks", []) if x["id"] != look["id"]]
            idx = next((i for i, x in enumerate(p.get("looks", [])) if x["id"] == look["id"]), len(looks))
            looks.insert(idx, look)
            p["looks"] = looks
            return self._json({"perfil": guardar_perfil(p), "look": look})
        if u.path == "/api/look/quitar":             # saca el look del perfil; los archivos no se borran
            p = leer_perfil(d["perfil_id"])
            p["looks"] = [x for x in p.get("looks", []) if x["id"] != d["look_id"]]
            for k, v in list(p.get("predeterminados", {}).items()):
                if v == d["look_id"]:
                    p["predeterminados"][k] = None
            return self._json({"perfil": guardar_perfil(p)})
        if u.path == "/api/escanear":
            if not Path(carpeta).expanduser().is_dir():
                return self._json({"error": "La carpeta no existe"}, 400)
            r = subprocess.run([sys.executable, str(SCRIPTS / "escanear.py"), carpeta],
                               capture_output=True, text=True)
            if r.returncode != 0:
                return self._json({"error": (r.stderr or r.stdout)[-800:]}, 500)
            return self._json({"vlog": leer_vlog(carpeta)})
        if u.path == "/api/claude/editar":
            if not ruta_vlog(carpeta).exists():
                return self._json({"error": "Primero guardá el vlog"}, 400)
            return self._json({"job": lanzar_claude(carpeta, d.get("pedido", ""))})
        if u.path == "/api/claude/parar":
            j = JOBS.get(d.get("job"))
            if j and j["proc"] and j["proc"].poll() is None:
                j["proc"].send_signal(2)  # SIGINT: Claude cierra el turno prolijo
            return self._json({"ok": True})
        return self._json({"error": "no existe"}, 404)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--puerto", type=int, default=8787)
    a = ap.parse_args()
    perfil_inicial()
    srv = ThreadingHTTPServer(("127.0.0.1", a.puerto), H)
    print(f"Editor de Vlogs en http://localhost:{a.puerto}  (Ctrl+C para cerrar)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
