#!/usr/bin/env python3
"""Exporta la edicion (plan.json) como proyecto para abrir en Adobe Premiere Pro.

Genera en <carpeta del dia>/_edicion/premiere/:
  <titulo>.xml        secuencia XML (Final Cut Pro 7 / xmeml v4): Premiere la abre con Archivo > Importar.
  subtitulos.srt      subtitulos (Archivo > Importar, se arrastran a la secuencia como subtitulos editables)
  textos/*.png        titulos, lugar/hora y textos con fondo transparente (pista V2)
  barras.png          barras negras (pista V3, solo donde van)
  LEEME.txt           como abrirlo y que revisar

Pistas: V1 clips (cortes, zoom, nombre con la LUT a aplicar) · V2 textos · V3 barras
        A1 voz (volumen y mute por clip) · A2 musica (volumen y fades) · A3 efectos
Marcadores: capitulos (lugar/hora), cambios de LUT y notas de revision.

Uso:  python3 premiere.py <vlog.json>
"""
import argparse, json, os, sys, urllib.parse
from fractions import Fraction
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402

W, H = 1920, 1080


# ---------- utilidades ----------
def rate_xml(fr):
    """Fraction -> (timebase, ntsc) como lo entiende Premiere."""
    fr = Fraction(fr)
    tb = round(float(fr))
    ntsc = abs(float(fr) - tb) > 0.001
    return tb, ntsc


def rate_tag(fr):
    tb, ntsc = rate_xml(fr)
    return f"<rate><timebase>{tb}</timebase><ntsc>{'TRUE' if ntsc else 'FALSE'}</ntsc></rate>"


def path_url(p):
    return "file://localhost" + urllib.parse.quote(os.path.abspath(p))


def db_lin(db):
    return max(0.0, min(3.98109, 10 ** (db / 20.0)))


def nombre_lut(look):
    if not look or not look.get("lut"):
        return ""
    inten = look.get("intensidad", 100)
    base = os.path.splitext(os.path.basename(str(look["lut"])))[0]
    return f"{base}{'' if int(inten) >= 100 else f' {int(inten)}%'}"


def lut_efectiva(s, clip, cfg, capas):
    if isinstance(s.get("color"), dict) and s["color"].get("lut"):
        return s["color"]
    for c in reversed(capas):
        if c.get("t", 0) - 1e-4 <= s["t"] < c.get("t", 0) + c.get("dur", 0):
            return c
    return (cfg["color"].get("looks") or {}).get(s.get("perfil") or clip.get("perfil")) or {}


# ---------- imagenes (textos y barras) ----------
def fuente(nombres, tam):
    from PIL import ImageFont
    cand = []
    for n in nombres:
        cand += [n, f"/System/Library/Fonts/Supplemental/{n}", f"/Library/Fonts/{n}", f"/System/Library/Fonts/{n}",
                 f"/usr/share/fonts/truetype/dejavu/{n}"]
    for c in cand:
        try:
            return ImageFont.truetype(c, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def png_texto(t, ruta):
    from PIL import Image, ImageDraw, ImageFilter
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    tipo, estilo = t.get("tipo"), t.get("estilo", "simple")

    def centrado(txt, f, y, color, capa=None):
        caja = d.textbbox((0, 0), txt, font=f)
        x = (W - (caja[2] - caja[0])) / 2
        (capa or d).text((x, y), txt, font=f, fill=color)
        return caja[3] - caja[1]

    if tipo == "titulo" or (tipo == "texto" and estilo == "titulo"):
        num = str(t.get("numero", "")) if tipo == "titulo" else ""
        txt = str(t.get("texto", "")).upper()
        fg, fn = fuente(["Impact.ttf", "Arial Narrow Bold.ttf", "DejaVuSans-Bold.ttf"], int(H * 0.13)), \
            fuente(["Impact.ttf", "DejaVuSans-Bold.ttf"], int(H * 0.07))
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        pos = {"arriba": H * 0.12, "abajo": H * 0.68}.get(t.get("pos"), H * 0.40)
        for capa, color in ((gd, (255, 40, 30, 255)), (d, (255, 74, 61, 255))):
            y = pos
            if num:
                caja = capa.textbbox((0, 0), "#" + num, font=fn)
                capa.text(((W - caja[2] + caja[0]) / 2, y - H * 0.08), "#" + num, font=fn, fill=color)
            caja = capa.textbbox((0, 0), txt, font=fg)
            capa.text(((W - caja[2] + caja[0]) / 2, y), txt, font=fg, fill=color)
        glow = glow.filter(ImageFilter.GaussianBlur(H // 60))
        img = Image.alpha_composite(glow, img)
    elif tipo == "lugar_hora" or (tipo == "texto" and estilo == "lugar"):
        f = fuente(["HelveticaNeue.ttc", "Helvetica.ttc", "Arial.ttf", "DejaVuSans.ttf"], int(H * 0.036))
        y = H * 0.46
        if tipo == "lugar_hora":
            if t.get("lugar"):
                d.text((W * 0.08, y), str(t["lugar"]), font=f, fill=(255, 255, 255, 255))
            if t.get("hora"):
                caja = d.textbbox((0, 0), str(t["hora"]), font=f)
                d.text((W * 0.92 - (caja[2] - caja[0]), y), str(t["hora"]), font=f, fill=(255, 255, 255, 255))
        else:
            centrado(str(t.get("texto", "")), f, {"arriba": H * 0.10, "centro": H * 0.47}.get(t.get("pos"), H * 0.80), (255, 255, 255, 255))
    else:   # texto simple
        f = fuente(["HelveticaNeue.ttc", "Helvetica.ttc", "Arial.ttf", "DejaVuSans.ttf"], int(H * 0.045))
        sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        y = {"arriba": H * 0.10, "centro": H * 0.47}.get(t.get("pos"), H * 0.80)
        centrado(str(t.get("texto", "")), f, y + 3, (0, 0, 0, 170), ImageDraw.Draw(sombra))
        sombra = sombra.filter(ImageFilter.GaussianBlur(4))
        centrado(str(t.get("texto", "")), f, y, (255, 255, 255, 255))
        img = Image.alpha_composite(sombra, img)
    img.save(ruta)


def png_barras(formato, ruta):
    from PIL import Image, ImageDraw
    a, _, b = str(formato).partition(":")
    r = float(a) / float(b or 1)
    alto = max(0, int(round((H - W / r) / 2)))
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, alto], fill=(0, 0, 0, 255))
    d.rectangle([0, H - alto, W, H], fill=(0, 0, 0, 255))
    img.save(ruta)


def srt(eventos, ruta):
    def tcs(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    with open(ruta, "w", encoding="utf-8") as f:
        for i, e in enumerate(eventos, 1):
            f.write(f"{i}\n{tcs(e['t'])} --> {tcs(e['fin'])}\n{e['texto']}\n\n")


# ---------- XML ----------
class Xml:
    def __init__(self, fo):
        self.fo = fo
        self.files = {}     # ruta -> id
        self.n = 0

    def fr(self, seg):
        return int(round(seg * float(self.fo)))

    def file(self, ruta, fr, dur_seg, video=True, audio=True, w=None, h=None, still=False):
        if ruta in self.files:
            return f'<file id="{self.files[ruta]}"/>'
        fid = f"file-{len(self.files) + 1}"
        self.files[ruta] = fid
        dur = int(round(dur_seg * float(fr))) if dur_seg else 0
        media = ""
        if video:
            media += (f"<video><samplecharacteristics>{rate_tag(fr)}<width>{w or W}</width><height>{h or H}</height>"
                      f"<pixelaspectratio>square</pixelaspectratio><fielddominance>none</fielddominance></samplecharacteristics></video>")
        if audio:
            media += ("<audio><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate></samplecharacteristics>"
                      "<channelcount>2</channelcount></audio>")
        return (f'<file id="{fid}"><name>{escape(os.path.basename(ruta))}</name><pathurl>{path_url(ruta)}</pathurl>'
                f"{rate_tag(fr)}<duration>{dur}</duration>{'<timecode><string>00:00:00:00</string></timecode>' if not still else ''}"
                f"<media>{media}</media></file>")

    def clip(self, nombre, archivo_xml, fr, start, end, cin, cout, filtros="", extra=""):
        self.n += 1
        cid = f"clipitem-{self.n}"
        x = (f'<clipitem id="{cid}"><name>{escape(nombre)}</name><enabled>TRUE</enabled><duration>{max(cout, end - start)}</duration>'
             f"{rate_tag(fr)}<start>{start}</start><end>{end}</end><in>{cin}</in><out>{cout}</out>{archivo_xml}{filtros}{extra}</clipitem>")
        return cid, x


def filtro_escala(pct):
    return ("<filter><effect><name>Basic Motion</name><effectid>basic</effectid><effectcategory>motion</effectcategory>"
            "<effecttype>motion</effecttype><mediatype>video</mediatype><parameter authoringApp=\"PremierePro\">"
            f"<parameterid>scale</parameterid><name>Scale</name><valuemin>0</valuemin><valuemax>1000</valuemax><value>{pct:.1f}</value>"
            "</parameter></effect></filter>")


def filtro_nivel(gain, keyframes=None):
    kf = "".join(f"<keyframe><when>{w}</when><value>{v:.5f}</value></keyframe>" for w, v in (keyframes or []))
    return ("<filter><effect><name>Audio Levels</name><effectid>audiolevels</effectid><effectcategory>audiolevels</effectcategory>"
            "<effecttype>audiolevels</effecttype><mediatype>audio</mediatype><parameter authoringApp=\"PremierePro\">"
            f"<parameterid>level</parameterid><name>Level</name><valuemin>0</valuemin><valuemax>3.98109</valuemax>"
            f"<value>{gain:.5f}</value>{kf}</parameter></effect></filter>")


def repartir(items):
    """[(start, end, xml)] -> lista de pistas sin superposiciones (lo que se cruza va a otra pista)."""
    pistas = []
    for st, en, x in sorted(items, key=lambda i: i[0]):
        for p in pistas:
            if p[-1][1] <= st:
                p.append((st, en, x)); break
        else:
            pistas.append([(st, en, x)])
    return [[x for _, _, x in p] for p in pistas] or [[]]


def marcador(nombre, comentario, frame):
    return (f"<marker><name>{escape(nombre)}</name><comment>{escape(comentario)}</comment>"
            f"<in>{frame}</in><out>-1</out></marker>")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("vlog")
    a = ap.parse_args()
    vlog = os.path.abspath(a.vlog)
    raw, cfg = comun.cargar_vlog(vlog)
    ed = comun.dir_edicion(vlog)
    carpeta = comun.carpeta_dia(vlog, cfg)
    plan = comun.leer_json(os.path.join(ed, "plan.json"))
    if not plan or not plan.get("segmentos"):
        sys.exit("Todavia no hay edicion (plan.json). Pedile a Claude que arme el vlog primero.")
    import render   # reusa la normalizacion y los subtitulos del motor
    clips = {c["archivo"]: c for c in cfg["material"]["clips"]}
    if hasattr(render, "normalizar_plan"):
        r = render.normalizar_plan(plan, clips)
        plan = r if isinstance(r, dict) else plan
    comun.abrir_log(ed, "premiere")
    out = os.path.join(ed, "premiere")
    os.makedirs(os.path.join(out, "textos"), exist_ok=True)
    fo = Fraction(plan["fps"])
    X = Xml(fo)
    titulo = cfg.get("titulo") or "Vlog"
    slug = comun.slug(titulo)
    capas = [c for c in (plan.get("capas_color") or []) if not c.get("mute") and not c.get("oculto")]

    # ---- V1 video + A1 voz ----
    v1, a1, marcas = [], [], []
    ultima_lut = None
    segs = plan["segmentos"]
    comun.progreso("premiere", 1, 5, "clips")
    for s in segs:
        clip = clips.get(s["clip"], {})
        ruta = os.path.join(carpeta, s["clip"])
        cf = comun.fps_frac(clip) if clip else fo
        start, end = X.fr(s["t"]), X.fr(s["t"] + s["dur"])
        cin = int(round(s["entrada"] * float(cf)))
        cout = cin + int(round((end - start) * float(cf) / float(fo)))
        look = lut_efectiva(s, clip, cfg, capas)
        nl = nombre_lut(look)
        if nl != ultima_lut:
            marcas.append(marcador(f"LUT: {nl or 'sin LUT'}", f"Desde aca: aplicar {look.get('lut', 'sin LUT')} "
                                   f"al {look.get('intensidad', 100)}% (Lumetri > Creativo > Look)", start))
            ultima_lut = nl
        nombre = f"{os.path.basename(s['clip'])}{'  [' + nl + ']' if nl else ''}"
        fxml = X.file(ruta, cf, clip.get("duracion") or 0, True, clip.get("audio", True), clip.get("ancho"), clip.get("alto"))
        filtros = filtro_escala(100 * float(s.get("zoom") or 1.0)) if (s.get("zoom") or 1) > 1.001 else ""
        vid, vx = X.clip(nombre, fxml, cf, start, end, cin, cout, filtros)
        v1.append(vx)
        if clip.get("audio", True):
            g = 0.0 if s.get("mute") else db_lin(float(s.get("vol_db") or 0) + (0 if s.get("audio") == "voz" else -12))
            _, ax = X.clip(os.path.basename(s["clip"]), f'<file id="{X.files[ruta]}"/>', cf, start, end, cin, cout,
                           filtro_nivel(g), "<sourcetrack><mediatype>audio</mediatype><trackindex>1</trackindex></sourcetrack>")
            a1.append(ax)

    total = X.fr(plan["duracion"])
    # ---- A2 musica / A3 efectos ----
    comun.progreso("premiere", 2, 5, "musica y efectos")

    def pista_audio(items, clave, defecto_db):
        res, lufs_cache = [], {}
        for c in items:
            ruta = c.get(clave)
            if c.get("mute") or not ruta or not os.path.exists(ruta):
                continue
            if c.get("lufs_tema", -70) > -60:
                lufs = c["lufs_tema"]
            else:
                if ruta not in lufs_cache:
                    lufs_cache[ruta] = comun.medir_lufs(["-i", ruta])[0]
                lufs = lufs_cache[ruta] if lufs_cache[ruta] > -60 else -14.0
            info = comun.ffprobe(ruta) or {}
            durf = float((info.get("format") or {}).get("duration") or 0)
            dur = float(c.get("dur") or max(0.1, durf - float(c.get("desde") or 0)))
            start, end = X.fr(c["t"]), min(X.fr(c["t"] + dur), total)
            if end - start < 1:
                continue
            cin = X.fr(float(c.get("desde") or 0))
            g = db_lin(float(c.get("nivel_db", defecto_db)) - lufs)
            kf = []
            n = end - start
            fi, fo_ = X.fr(float(c.get("fade_in") or 0)), X.fr(float(c.get("fade_out") or 0))
            if fi > 1 or fo_ > 1:
                kf = [(cin, 0.0 if fi > 1 else g), (cin + max(fi, 1), g), (cin + n - max(fo_, 1), g), (cin + n, 0.0 if fo_ > 1 else g)]
            fxml = X.file(ruta, fo, durf, video=False)
            _, x = X.clip(os.path.basename(ruta), fxml, fo, start, end, cin, cin + n, filtro_nivel(g, kf))
            res.append((start, end, x))
        return res
    a2 = pista_audio(plan.get("musica") or [], "tema", -10)
    a3 = pista_audio(plan.get("sfx") or [], "archivo", -14)

    # ---- V2 textos (PNG) ----
    comun.progreso("premiere", 3, 5, "textos")
    v2 = []
    for i, t in enumerate(x for x in (plan.get("textos") or []) if not x.get("oculto")):
        ruta = os.path.join(out, "textos", f"texto_{i + 1:02d}.png")
        png_texto(t, ruta)
        start, end = X.fr(t["t"]), min(X.fr(t["t"] + t["dur"]), total)
        if end - start < 1:
            continue
        fxml = X.file(ruta, fo, 0, True, False, still=True)
        nombre = t.get("texto") or t.get("lugar") or "texto"
        _, x = X.clip(f"Texto: {nombre}", fxml, fo, start, end, 0, end - start)
        v2.append((start, end, x))
        if t.get("tipo") == "lugar_hora":
            marcas.append(marcador(f"{t.get('lugar', '')} {t.get('hora', '')}".strip(), "capitulo", start))

    # ---- V3 barras ----
    v3 = []
    barras = cfg["color"].get("barras") or {}
    if barras.get("formato"):
        rb = os.path.join(out, "barras.png")
        png_barras(barras["formato"], rb)
        tramos = []
        for s in segs:
            if barras.get("donde", "montajes") == "todo" or s["tipo"] in ("teaser", "montaje"):
                a0, b0 = X.fr(s["t"]), X.fr(s["t"] + s["dur"])
                if tramos and tramos[-1][1] == a0:
                    tramos[-1][1] = b0
                else:
                    tramos.append([a0, b0])
        for a0, b0 in tramos:
            _, x = X.clip(f"Barras {barras['formato']}", X.file(rb, fo, 0, True, False, still=True), fo, a0, b0, 0, b0 - a0)
            v3.append(x)

    # ---- subtitulos y notas ----
    comun.progreso("premiere", 4, 5, "subtitulos")
    if cfg["textos"].get("subtitulos", True):
        srt(render.eventos_subtitulos(segs), os.path.join(out, "subtitulos.srt"))
    for n in (cfg.get("revision") or {}).get("notas", []) or []:
        if not n.get("hecha"):
            try:
                marcas.append(marcador("Nota", n.get("texto", ""), X.fr(comun.tc_a_seg(n.get("tc", "0")))))
            except ValueError:
                pass

    tb, ntsc = rate_xml(fo)
    pista = lambda items: f"<track>{''.join(items)}</track>"  # noqa: E731
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4">'
           f'<sequence id="sequence-1"><name>{escape(titulo)}</name><duration>{total}</duration>{rate_tag(fo)}'
           "<timecode><rate><timebase>%d</timebase><ntsc>%s</ntsc></rate><string>00:00:00:00</string><frame>0</frame><displayformat>NDF</displayformat></timecode>"
           % (tb, "TRUE" if ntsc else "FALSE") +
           f"<media><video><format><samplecharacteristics>{rate_tag(fo)}<width>{W}</width><height>{H}</height>"
           "<pixelaspectratio>square</pixelaspectratio><fielddominance>none</fielddominance></samplecharacteristics></format>"
           f"{pista(v1)}{''.join(pista(p) for p in repartir(v2))}{pista(v3)}</video>"
           "<audio><numOutputChannels>2</numOutputChannels><format><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate>"
           f"</samplecharacteristics></format>{pista(a1)}{''.join(pista(p) for p in repartir(a2))}{''.join(pista(p) for p in repartir(a3))}</audio></media>"
           f"{''.join(marcas)}</sequence></xmeml>\n")
    ruta_xml = os.path.join(out, f"{slug}.xml")
    with open(ruta_xml, "w", encoding="utf-8") as f:
        f.write(xml)
    with open(os.path.join(out, "LEEME.txt"), "w", encoding="utf-8") as f:
        f.write(f"""ABRIR EN PREMIERE PRO
=====================
1. Premiere: Archivo > Importar > {os.path.basename(ruta_xml)}  (se crea la secuencia "{titulo}").
2. Si pide ubicar medios, elegi la carpeta del dia: {carpeta}
3. Color: cada clip dice en su nombre que LUT lleva y hay marcadores donde cambia.
   Aplicala en Lumetri > Creativo > Look (o en un Adjustment Layer) con la intensidad indicada.
4. Subtitulos: Archivo > Importar > subtitulos.srt y arrastralo a la secuencia.
5. Textos y barras van como imagenes PNG en V2 y V3.
Pistas: V1 clips · V2 textos · V3 barras · A1 voz · A2 musica · A3 efectos.
""")
    comun.progreso("premiere", 5, 5, os.path.basename(ruta_xml))
    comun.fin_log(f"FIN OK premiere _edicion/premiere/{os.path.basename(ruta_xml)}")
    print("OK", ruta_xml)


if __name__ == "__main__":
    main()
