#!/usr/bin/env python3
"""Arma _edicion/plan.json: la lista ordenada de segmentos a renderizar + mapa de musica + textos.

Uso:
  python3 plan.py <vlog.json>                      arma el plan
  python3 plan.py <vlog.json> --forzar             lo arma aunque Snati lo haya editado a mano en la
                                                   linea de tiempo (antes guarda copia en
                                                   _edicion/planes/plan_manual_<fecha>.json)
  python3 plan.py <vlog.json> --tc 02:14 [--version 3]   dice que clip/tiempo hay en ese minuto
                                                   de una version (para aplicar notas de revision)

De donde sale la historia (en este orden):
  1) _edicion/historia.json (lo escribe Claude: ver references/historia_json.md)
  2) historia.bloques de vlog.json (si la app/Claude ya los dejo ahi)
  3) por defecto: clips no descartados en orden de carpeta; los que tienen charla -> bloque
     'charla'; b-roll / sin habla -> 'montaje' (los seguidos se juntan). Sin teaser.

Lo mecanico (lo hace este script):
  - charla: saca pausas > cortes.silencio_max_s (deja 3 frames de aire), saca muletillas
    sueltas, saca los rangos 'quitar' de historia.json y alterna punch-in (1.0 / 1.12) en
    cada jump cut.
  - montajes/teaser: largo de plano encajado al beat del tema (1/2/4/8 beats) si corte_en_beat.
  - musica: fuerte en montajes, nada o baja en charla, fades al volver a hablar.
  - todo se redondea a frames de salida (audio y video no se desfasan).
"""
import argparse
import os
import re
import shutil
import sys
from datetime import datetime
import unicodedata
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402
import musica  # noqa: E402

# ---------- Muletillas ----------
SIEMPRE = {"eh", "ehh", "ehhh", "ehm", "em", "emm", "emmm", "mm", "mmm", "hmm", "mhm", "aa", "aah", "eee"}
CONTEXTO = {"normal": ["este", "bueno", "o sea", "digamos"],
            "fuerte": ["este", "bueno", "o sea", "digamos", "tipo", "nada", "viste", "como que"],
            "suave": []}
AGRESIVIDAD = {"suave": (2.0, 4), "normal": (1.0, 3), "fuerte": (0.8, 2)}   # (x silencio, frames de aire)
NIVEL_BAJO_DB = -28.0      # musica "baja" debajo de la voz
ZOOM = 1.12


def norm(w):
    w = unicodedata.normalize("NFKD", w.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", w)


class Plan:
    def __init__(self, vlog):
        self.vlog = os.path.abspath(vlog)
        _, self.cfg = comun.cargar_vlog(self.vlog)
        self.ed = comun.dir_edicion(self.vlog)
        self.clips = {c["archivo"]: c for c in self.cfg["material"]["clips"]}
        self.tx = {}
        self.avisos = []
        cor = self.cfg["cortes"]
        mult, pad_frames = AGRESIVIDAD.get(cor.get("agresividad", "normal"), (1.0, 3))
        self.umbral = float(cor.get("silencio_max_s") or 0.25) * mult
        self.pad_frames = pad_frames
        m = cor.get("muletillas", True)
        if isinstance(m, list):
            self.contexto = [norm_frase(x) for x in m]
        elif m:
            self.contexto = [norm_frase(x) for x in CONTEXTO.get(cor.get("agresividad", "normal"), CONTEXTO["normal"])]
        else:
            self.contexto = None   # muletillas apagadas
        self.punch = bool(cor.get("punch_in", True))
        self.zoom = float(cor.get("punch_in_zoom", ZOOM))
        usados = [c for c in self.cfg["material"]["clips"] if not c.get("descartado")]
        self.fo = fps_salida(usados, self.cfg)
        self.F = 0              # frames de salida acumulados
        self.segs = []
        self.bloques_out = []
        self.spans = []         # tramos de musica: [t0, t1, tema_idx, nivel, desde]
        self.stats = {"silencios_s": 0.0, "muletillas": 0, "quitado_s": 0.0}
        self.quitar = []
        mus = self.cfg["musica"]
        self.temas = [t for t in mus.get("temas", []) if t.get("archivo") and os.path.exists(t["archivo"])]
        for t in mus.get("temas", []):
            if t.get("archivo") and not os.path.exists(t["archivo"]):
                self.avisos.append(f"no encuentro el tema {t['archivo']}")
        self.info_temas = [musica.analizar(t["archivo"], os.path.join(self.ed, "musica")) for t in self.temas]
        self.cursor = [0.0] * len(self.temas)
        self.ultimo_tema = None
        self.rot_montaje = 0

    # ----- utilidades -----
    def t(self):
        return float(self.F / self.fo)

    def palabras(self, archivo):
        if archivo not in self.tx:
            tx = comun.leer_json(os.path.join(self.ed, "transcripciones", comun.nombre_seguro(archivo) + ".json"))
            pal = []
            for s in (tx or {}).get("segmentos", []):
                for w in s.get("palabras", []):
                    if w["fin"] > w["inicio"]:
                        pal.append({"i": w["inicio"], "f": w["fin"], "w": w["palabra"], "n": norm(w["palabra"])})
            self.tx[archivo] = pal if tx else None
        return self.tx[archivo]

    def emitir(self, clip, s, e, tipo, bloque, audio, zoom=1.0, palabras=None, fin_abs=None):
        """Agrega un segmento redondeado a frames. fin_abs = tiempo de salida exacto donde cortar."""
        c = self.clips[clip]
        fc = comun.fps_frac(c)
        s = round(s * fc) / fc
        s = max(0.0, float(s))
        if fin_abs is not None:
            n = round(fin_abs * self.fo) - self.F
        else:
            n = round((e - s) * self.fo)
        dur_clip = float(c.get("duracion") or 0)
        if dur_clip and s + n / self.fo > dur_clip - 0.5 / float(fc):
            n = int((dur_clip - s - 0.5 / float(fc)) * self.fo)
        if n < 1:
            return None
        seg = {"n": len(self.segs) + 1, "bloque": bloque, "tipo": tipo, "clip": clip,
               "entrada": round(s, 4), "salida": round(s + n / float(self.fo), 4),
               "t": round(self.F / float(self.fo), 4), "dur": round(n / float(self.fo), 4), "frames": n,
               "zoom": zoom, "perfil": c.get("perfil", "desconocido"), "audio": audio}
        if palabras:
            seg["palabras"] = [[round(w["i"], 3), round(w["f"], 3), w["w"]] for w in palabras
                               if s - 0.05 <= (w["i"] + w["f"]) / 2 <= s + n / float(self.fo)]
        self.F += n
        self.segs.append(seg)
        return seg

    # ----- charla: silencios, muletillas, quitar -----
    def es_muletilla(self, pal, k):
        w = pal[k]["n"]
        if self.contexto is None:
            return 0
        if w in SIEMPRE:
            return 1
        antes = pal[k]["i"] - pal[k - 1]["f"] if k > 0 else 9
        for frase in self.contexto:
            n = len(frase)
            if [p["n"] for p in pal[k:k + n]] != frase:
                continue
            despues = pal[k + n]["i"] - pal[k + n - 1]["f"] if k + n < len(pal) else 9
            if frase == ["bueno"]:
                if antes >= 0.3:            # "bueno" al arrancar una frase
                    return n
            elif antes >= 0.12 and despues >= 0.12:   # suelta entre pausas
                return n
        return 0

    def piezas_charla(self, clip, a, b, cortar=True):
        """Rangos [(s, e, palabras)] a conservar de un tramo hablado."""
        quitar = [(q[0], q[1]) for q in self.quitar if q[2] == clip and q[1] > a and q[0] < b]
        pal_all = self.palabras(clip)
        if not cortar or not pal_all:
            if cortar and pal_all is None:
                self.avisos.append(f"{clip}: sin transcripcion, va sin cortes")
            return restar([(a, b, [])], quitar)
        pal = [w for w in pal_all if a - 0.05 <= (w["i"] + w["f"]) / 2 <= b + 0.05]
        if not pal:
            return []
        pad = self.pad_frames / float(self.fo)
        marcas, k = [], 0          # marcas[k] = True si la palabra se saca
        while k < len(pal):
            mid = (pal[k]["i"] + pal[k]["f"]) / 2
            if any(q0 <= mid <= q1 for q0, q1 in quitar):
                marcas.append(True)
                k += 1
                continue
            n = self.es_muletilla(pal, k)
            if n:
                self.stats["muletillas"] += 1
                marcas += [True] * n
                k += n
            else:
                marcas.append(False)
                k += 1
        piezas, actual, removidos = [], None, []
        for w, saca in zip(pal, marcas):
            if saca:
                removidos.append((w["i"], w["f"]))
                continue
            if actual is None:
                actual = [max(a, w["i"] - pad), w["f"], [w]]
                removidos = []
                continue
            hueco = w["i"] - actual[1]
            if removidos or hueco > self.umbral or any(actual[1] < q1 and q0 < w["i"] for q0, q1 in quitar):
                fin = actual[1] + pad
                ini = w["i"] - pad
                zonas = removidos + [q for q in quitar if actual[1] < q[1] and q[0] < w["i"]]
                if zonas:
                    fin = min(fin, min(z[0] for z in zonas))
                    ini = max(ini, max(z[1] for z in zonas))
                if fin > ini:
                    fin = ini = (fin + ini) / 2
                piezas.append((actual[0], fin, actual[2]))
                actual = [ini, w["f"], [w]]
                removidos = []
            else:
                actual[1] = w["f"]
                actual[2].append(w)
        if actual:
            piezas.append((actual[0], min(b, actual[1] + pad), actual[2]))
        piezas = restar(piezas, quitar)
        conservado = sum(e - s for s, e, _ in piezas)
        self.stats["silencios_s"] += max(0.0, (b - a) - conservado)
        return [p for p in piezas if p[1] - p[0] >= 2 / float(self.fo)]

    # ----- musica -----
    def tema_para(self, tipo, bloque):
        if not self.temas or bloque.get("musica") is False:
            return None
        pedido = bloque.get("tema")
        if isinstance(pedido, int) and 0 <= pedido < len(self.temas):
            return pedido
        if isinstance(pedido, str):
            for i, t in enumerate(self.temas):
                if os.path.basename(t["archivo"]) == os.path.basename(pedido):
                    return i
        usos = {"teaser": ["teaser", "montajes"], "montaje": ["montajes"], "cierre": ["cierre", "montajes"]}
        for uso in usos.get(tipo, ["montajes"]):
            cands = [i for i, t in enumerate(self.temas) if t.get("uso", "montajes") == uso]
            if cands:
                if tipo == "montaje":
                    self.rot_montaje += 1
                    return cands[(self.rot_montaje - 1) % len(cands)]
                return cands[0]
        return 0

    def span(self, t0, t1, tema, nivel, desde):
        if tema is None or t1 <= t0:
            return
        if self.spans:
            p = self.spans[-1]
            if p[2] == tema and p[3] == nivel and abs(p[1] - t0) < 2e-3 and abs(p[4] + (p[1] - p[0]) - desde) < 0.01:
                p[1] = t1
                return
        self.spans.append([t0, t1, tema, nivel, desde])

    # ----- bloques -----
    def bloque(self, idx, b):
        tipo = b.get("tipo", "charla")
        tomas = b.get("tomas") or [{"clip": b.get("clip"), "entrada": b.get("entrada"), "salida": b.get("salida"),
                                    "audio": b.get("audio")}]
        tomas = [t for t in tomas if t.get("clip") in self.clips and not self.clips[t["clip"]].get("descartado")]
        if not tomas:
            self.avisos.append(f"bloque {idx} ({tipo}) sin clips validos, lo salteo")
            return
        T0 = self.t()
        mus = self.cfg["musica"]
        nivel_alto = float(mus.get("volumen_montaje_db", -10))
        bajo = float(mus.get("volumen_charla_db", NIVEL_BAJO_DB))
        tema = None
        if tipo in ("teaser", "montaje", "cierre"):
            tema = self.tema_para(tipo, b)
        elif mus.get("en_charla") == "baja" and b.get("musica") is not False and self.temas:
            tema = self.ultimo_tema if self.ultimo_tema is not None else self.tema_para("montaje", {})
        info = self.info_temas[tema] if tema is not None else None
        desde0 = self.cursor[tema] if tema is not None else 0.0
        if info and tipo in ("teaser", "montaje", "cierre"):
            desde0 = musica.primer_beat(info, desde0)
        beats = []
        if info and mus.get("corte_en_beat", True) and tipo in ("teaser", "montaje"):
            bs = musica.beats_desde(info, desde0, desde0 + 3600)
            beats = [T0 + (x - desde0) for x in bs]
        zoom_toggle = False
        for toma in tomas:
            c = self.clips[toma["clip"]]
            dur = float(c.get("duracion") or 0)
            a = float(toma.get("entrada") or 0)
            e = toma.get("salida")
            e = float(e) if e is not None else dur
            e = min(e, dur) if dur else e
            audio = toma.get("audio") or ("voz" if tipo in ("charla", "cierre") else "ambiente")
            if audio == "voz":
                for s, fin, pal in self.piezas_charla(toma["clip"], a, e, cortar=b.get("cortar", True)):
                    z = self.zoom if (self.punch and zoom_toggle and tipo in ("charla", "cierre")) else 1.0
                    seg = self.emitir(toma["clip"], s, fin, tipo, idx, "voz", z, self.palabras(toma["clip"]) or [])
                    if seg:
                        zoom_toggle = not zoom_toggle
                        self.span(seg["t"], seg["t"] + seg["dur"], tema,
                                  bajo,
                                  desde0 + seg["t"] - T0)
                continue
            # toma de montaje (ambiente): largo encajado al beat
            explicito = toma.get("salida") is not None
            deseado = (e - a) if explicito else (1.0 if tipo == "teaser" else 2.0)
            if not explicito and toma.get("entrada") is None:   # sin tiempos: plano del medio del clip
                a = max(0.0, dur / 2 - deseado / 2)
            disponible = min(dur - a, (e - a) + 0.6) if dur else (e - a) + 0.6
            t_cur = self.t()
            fin_abs = None
            if beats:
                fin_abs = musica.elegir_fin(t_cur, beats, deseado, disponible, b.get("beats_por_plano"),
                                            en_beat=any(abs(t_cur - x) < 1.5 / float(self.fo) for x in beats))
            seg = self.emitir(toma["clip"], a, a + min(deseado, disponible), tipo, idx, "ambiente",
                              1.0, None, fin_abs=fin_abs)
            if seg:
                self.span(seg["t"], seg["t"] + seg["dur"], tema, nivel_alto, desde0 + seg["t"] - T0)
        T1 = self.t()
        if tema is not None:
            self.cursor[tema] = desde0 + (T1 - T0)
            self.ultimo_tema = tema
        primero = tomas[0]
        hora = b.get("hora") or ""
        if b.get("lugar") and not hora:
            hora = self.clips[primero["clip"]].get("hora", "")
        self.bloques_out.append({"n": idx, "tipo": tipo, "t": round(T0, 3), "dur": round(T1 - T0, 3),
                                 "clip": primero["clip"], "entrada": primero.get("entrada"),
                                 "salida": primero.get("salida"), "resumen": b.get("resumen", ""),
                                 "lugar": b.get("lugar", ""), "hora": hora,
                                 "tema": os.path.basename(self.temas[tema]["archivo"]) if tema is not None else "",
                                 "tomas": [{k: t.get(k) for k in ("clip", "entrada", "salida", "audio") if t.get(k) is not None}
                                           for t in tomas]})

    def cues(self):
        """Convierte tramos de musica en cues con fades: subir = 0.1 s en el corte, bajar/salir = fade_s
        despues del corte (fade_out en render es en dB: cae rapido y termina suave)."""
        fade = float(self.cfg["musica"].get("fade_s", 4))
        total = self.t()
        sp = [s for s in self.spans if s[3] is not None]
        out = []
        for i, (t0, t1, tema, nivel, desde) in enumerate(sp):
            prev = sp[i - 1] if i > 0 and abs(sp[i - 1][1] - t0) < 2e-3 else None
            nxt = sp[i + 1] if i + 1 < len(sp) and abs(sp[i + 1][0] - t1) < 2e-3 else None
            # entrada: si viene de algo mas fuerte, sube despacio DESPUES del corte (mientras el otro baja)
            if prev:
                if nivel < prev[3]:
                    pre, fin_in = 0.0, min(fade, t1 - t0)
                else:
                    pre, fin_in = min(0.05, prev[1] - prev[0]), 0.1
            else:
                pre = 0.0
                fin_in = 0.03 if nivel > NIVEL_BAJO_DB + 3 else min(fade, (t1 - t0) / 2)
            # salida: la musica fuerte queda a full hasta el corte y baja en los primeros fade_s de la charla
            if nxt:
                if nxt[3] < nivel:
                    post = fout = min(fade, nxt[1] - nxt[0])
                else:
                    post, fout = 0.05, 0.1
            elif t1 >= total - 1e-3:
                post, fout = 0.0, min(fade, t1 - t0)
            else:
                siguiente = next((x[0] for x in sp[i + 1:]), total)
                post = fout = max(0.05, min(fade, siguiente - t1, total - t1))
            ini = t0 - pre
            d0 = desde - pre
            if d0 < 0:
                ini, d0 = ini - d0, 0.0
            dur = (t1 + post) - ini
            if dur <= 0:
                continue
            out.append({"tema": self.temas[tema]["archivo"], "t": round(ini, 4), "dur": round(dur, 4),
                        "desde": round(d0, 4), "nivel_db": nivel, "fade_in": round(min(fin_in, dur), 3),
                        "fade_out": round(min(fout, dur), 3), "lufs_tema": self.info_temas[tema]["lufs"]})
        return out


def norm_frase(x):
    return [norm(p) for p in str(x).split() if norm(p)]


def restar(piezas, zonas):
    """Saca de cada (s, e, pal) los intervalos 'zonas'."""
    out = []
    for s, e, pal in piezas:
        partes = [(s, e)]
        for q0, q1 in zonas:
            nuevas = []
            for x0, x1 in partes:
                if q1 <= x0 or q0 >= x1:
                    nuevas.append((x0, x1))
                else:
                    if q0 > x0:
                        nuevas.append((x0, q0))
                    if q1 < x1:
                        nuevas.append((q1, x1))
            partes = nuevas
        for x0, x1 in partes:
            out.append((x0, x1, [w for w in pal if x0 <= (w["i"] + w["f"]) / 2 <= x1]))
    return out


def fps_salida(clips, cfg):
    pedido = cfg.get("exportar", {}).get("fps")
    if pedido:
        return Fraction(str(pedido)).limit_denominator(1001)
    peso = {}
    for c in clips:
        if c.get("broll"):
            continue
        f = comun.fps_frac(c)
        peso[f] = peso.get(f, 0) + float(c.get("duracion") or 0)
    if not peso:
        for c in clips:
            f = comun.fps_frac(c)
            peso[f] = peso.get(f, 0) + float(c.get("duracion") or 0)
    f = max(peso, key=peso.get) if peso else Fraction(30000, 1001)
    if f > 60:   # camara lenta / 120 fps: exportar a 30
        f = Fraction(30000, 1001) if f.denominator == 1001 else Fraction(30)
    return f


def bloques_fuente(p):
    """Devuelve (bloques, quitar, fuente)."""
    hj = comun.leer_json(os.path.join(p.ed, "historia.json"))
    if hj and hj.get("bloques"):
        return hj["bloques"], hj.get("quitar", []), "historia.json"
    hb = p.cfg["historia"].get("bloques") or []
    if hb:
        bloques = []
        for b in hb:   # junta entradas seguidas del mismo 'grupo' (o teaser/montaje seguidos) en un bloque
            if b.get("tomas"):
                bloques.append(b)
                continue
            prev = bloques[-1] if bloques else None
            mismo = prev is not None and prev.get("_junto") and prev.get("tipo") == b.get("tipo") and (
                (b.get("grupo") is not None and b.get("grupo") == prev.get("grupo")) or
                (b.get("grupo") is None and prev.get("grupo") is None and b.get("tipo") in ("teaser", "montaje")))
            if mismo:
                prev["tomas"].append(b)
            else:
                nb = {k: v for k, v in b.items() if k not in ("clip", "entrada", "salida", "audio")}
                nb.update({"tomas": [b], "_junto": True})
                bloques.append(nb)
        return bloques, (hj or {}).get("quitar", []), "vlog.json historia.bloques"
    # por defecto: orden de carpeta
    bloques = []
    clips = sorted([c for c in p.cfg["material"]["clips"] if not c.get("descartado")],
                   key=lambda c: (c.get("orden") or 0, c["archivo"]))
    for c in clips:
        pal = p.palabras(c["archivo"]) if not c.get("broll") else None
        if pal and len(pal) >= 8:
            bloques.append({"tipo": "charla", "clip": c["archivo"], "entrada": 0, "salida": c.get("duracion")})
        else:
            dur = float(c.get("duracion") or 0)
            n = max(1, min(3, int(dur // 6)))
            tomas = [{"clip": c["archivo"], "entrada": round(dur * (k + 0.5) / n - 1.0, 2), "salida": None}
                     for k in range(n)]
            for tm in tomas:
                tm["entrada"] = max(0.0, tm["entrada"])
                tm["salida"] = min(dur, tm["entrada"] + 2.0)
            if bloques and bloques[-1]["tipo"] == "montaje":
                bloques[-1]["tomas"] += tomas
            else:
                bloques.append({"tipo": "montaje", "tomas": tomas})
    return bloques, (hj or {}).get("quitar", []), "orden de carpeta (sin historia.json)"


def proteger_manual(vlog, forzar):
    """Si plan.json fue editado a mano (linea de tiempo de la app) no se pisa salvo --forzar.
    Devuelve el plan existente si hay que respetarlo, o None si se puede armar uno nuevo."""
    ed = comun.dir_edicion(os.path.abspath(vlog))
    ruta = os.path.join(ed, "plan.json")
    try:
        actual = comun.leer_json(ruta)
    except ValueError:
        actual = None
    if not (isinstance(actual, dict) and actual.get("editado_a_mano")):
        return None
    if not forzar:
        comun.abrir_log(ed, "plan")
        print("El plan.json lo edito Snati a mano en la linea de tiempo"
              + (f" ({actual['editado']})" if actual.get("editado") else "")
              + ": NO lo piso. Para renderizarlo: render.py. Para rehacerlo desde la historia: "
              "plan.py --forzar (guarda una copia antes).", flush=True)
        comun.fin_log("FIN OK plan sin cambios (plan.json editado a mano)")
        return actual
    os.makedirs(os.path.join(ed, "planes"), exist_ok=True)
    copia = os.path.join(ed, "planes", f"plan_manual_{datetime.now():%Y%m%d_%H%M%S}.json")
    shutil.copy(ruta, copia)
    print(f"plan.json editado a mano: copia en {os.path.relpath(copia, ed)} y lo rehago (--forzar)", flush=True)
    return None


def armar(vlog, forzar=False):
    manual = proteger_manual(vlog, forzar)
    if manual is not None:
        return manual
    p = Plan(vlog)
    comun.marcar_paso(p.vlog, "plan")
    comun.abrir_log(p.ed, "plan")
    bloques, quitar, fuente = bloques_fuente(p)
    p.quitar = [(float(q["entrada"]), float(q["salida"]), q["clip"]) for q in quitar
                if q.get("clip") and q.get("entrada") is not None and q.get("salida") is not None]
    p.stats["quitado_s"] = round(sum(q[1] - q[0] for q in p.quitar), 2)
    for i, b in enumerate(bloques):
        comun.progreso("plan", i + 1, len(bloques), b.get("tipo", ""))
        p.bloque(i, b)
    total = p.t()
    textos = []
    tx_cfg = p.cfg["textos"]
    te = tx_cfg.get("titulo_episodio") or {}
    if te.get("activo") and (te.get("texto") or te.get("numero")):
        ini = float(te.get("inicio_s", 0.4))
        textos.append({"tipo": "titulo", "t": ini, "dur": float(te.get("duracion_s", 3.6)),
                       "numero": str(te.get("numero") or ""), "texto": str(te.get("texto") or "")})
    if tx_cfg.get("lugar_hora", True) and p.cfg["historia"].get("capitulos_lugar_hora", True):
        for b in p.bloques_out:
            if b.get("lugar"):
                textos.append({"tipo": "lugar_hora", "t": b["t"] + 0.3, "dur": min(3.5, max(1.0, b["dur"] - 0.3)),
                               "lugar": b["lugar"], "hora": b.get("hora", "")})
    teaser = sum(b["dur"] for b in p.bloques_out if b["tipo"] == "teaser")
    obj = float(p.cfg["historia"]["teaser"].get("duracion_s", 20))
    if teaser and teaser > obj * 1.5:
        p.avisos.append(f"el teaser dura {teaser:.0f}s (objetivo {obj:.0f}s)")
    if total > 50 * 60:
        p.avisos.append(f"el video dura {comun.tc(total)}: pasa el maximo de 50 min")
    plan = {"version": 1, "creado": comun.ahora(), "fuente_historia": fuente,
            "fps": f"{p.fo.numerator}/{p.fo.denominator}", "duracion": round(total, 3),
            "bloques": p.bloques_out, "segmentos": p.segs, "musica": p.cues(), "textos": textos,
            "stats": {k: round(v, 2) if isinstance(v, float) else v for k, v in p.stats.items()},
            "avisos": p.avisos}
    comun.escribir_json(os.path.join(p.ed, "plan.json"), plan)

    def guardar(raw):
        # historia.bloques en el formato del contrato (una entrada por toma; 'grupo' = bloque)
        if fuente != "vlog.json historia.bloques":
            out = []
            for b in p.bloques_out:
                for k, t in enumerate(b["tomas"]):
                    e = {"tipo": b["tipo"], "grupo": b["n"], **t}
                    if k == 0:
                        e.update({x: b[x] for x in ("resumen", "lugar", "hora") if b.get(x)})
                    out.append(e)
            raw.setdefault("historia", {})["bloques"] = out
        raw.setdefault("estado", {})["paso"] = "plan"
    comun.actualizar_vlog(p.vlog, guardar)
    tipos = {}
    for s in p.segs:
        tipos[s["tipo"]] = tipos.get(s["tipo"], 0) + 1
    print(f"OK plan: {len(p.segs)} segmentos {tipos} | {comun.tc(total)} | historia: {fuente} | "
          f"silencio sacado {p.stats['silencios_s']:.1f}s, {p.stats['muletillas']} muletillas, "
          f"quitado {p.stats['quitado_s']}s | {len(plan['musica'])} cues de musica", flush=True)
    for a in p.avisos:
        print("AVISO " + a, flush=True)
    comun.fin_log(f"FIN OK plan {len(p.segs)} segmentos {comun.tc(total)}")
    return plan


def buscar_tc(vlog, tc_txt, version=None):
    ed = comun.dir_edicion(os.path.abspath(vlog))
    ruta = os.path.join(ed, "planes", f"plan_v{version}.json") if version else os.path.join(ed, "plan.json")
    plan = comun.leer_json(ruta)
    if not plan:
        sys.exit(f"No encuentro {ruta}")
    t = comun.tc_a_seg(tc_txt)
    for s in plan["segmentos"]:
        if s["t"] <= t < s["t"] + s["dur"]:
            en_clip = s["entrada"] + (t - s["t"])
            txt = " ".join(w[2] for w in s.get("palabras", []))
            print(f"{tc_txt} -> segmento {s['n']} (bloque {s['bloque']}, {s['tipo']}) | {s['clip']} "
                  f"{comun.tc(en_clip)} (segmento {comun.tc(s['entrada'])}-{comun.tc(s['salida'])}) | {txt[:200]}")
            return s
    print(f"{tc_txt}: fuera del video ({comun.tc(plan['duracion'])})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("vlog")
    ap.add_argument("--tc", help="buscar que hay en ese minuto (ej 02:14) en vez de armar el plan")
    ap.add_argument("--version", type=int, help="con --tc: version N (usa planes/plan_vN.json)")
    ap.add_argument("--forzar", action="store_true",
                    help="rehacer plan.json aunque este editado a mano (guarda copia antes)")
    args = ap.parse_args()
    if args.tc:
        buscar_tc(args.vlog, args.tc, args.version)
    else:
        armar(args.vlog, forzar=args.forzar)


if __name__ == "__main__":
    main()
