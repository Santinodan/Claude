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
from urllib.parse import urlparse, parse_qs

SKILL = Path(__file__).resolve().parent
REPO = SKILL.parents[2]
APP = SKILL / "app"
SCRIPTS = SKILL / "scripts" / "edicion"
HERRAMIENTAS = ["Read", "Write", "Edit", "Glob", "Grep",
                "Bash(ffmpeg *)", "Bash(ffprobe *)", "Bash(python3 *)", "Bash(ls *)", "Bash(mkdir *)"]

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
            return self._json({"ok": True})
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
    srv = ThreadingHTTPServer(("127.0.0.1", a.puerto), H)
    print(f"Editor de Vlogs en http://localhost:{a.puerto}  (Ctrl+C para cerrar)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
