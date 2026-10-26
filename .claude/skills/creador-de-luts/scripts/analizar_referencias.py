"""Analiza el color de videos/imagenes de referencia (reels, capturas) y resume el look.

Uso:
  python analizar_referencias.py CARPETA_O_ARCHIVOS... --out CARPETA_SALIDA [--frames 6]

Para cada video saca N fotogramas repartidos (ffmpeg, saltando el primer/ultimo 10%),
para cada imagen la usa tal cual. Despues mide en OKLab:
  - luminancia: negros (p2), medios (p50), altas (p98) y contraste (p90-p10)
  - croma (saturacion) media y por banda de luz: sombras / medios / altas, con el tono (hue)
    -> muestra el split toning (ej. sombras teal @185, altas calidas @75)
  - piel: tono y saturacion de los pixeles con color de piel
  - distribucion de tonos (que colores dominan)
Genera: hoja de contactos (contactos.jpg), informe.md legible y metricas.json
(este ultimo lo puede usar despues el generador para ajustar la LUT al look).
"""
import argparse, glob, json, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lutlib as L

VIDEO = ('.mp4', '.mov', '.m4v', '.webm', '.mkv')
IMAGEN = ('.jpg', '.jpeg', '.png', '.webp')
# Angulos de tono en OKLab (rojo ~29, naranja ~60, amarillo ~110, verde ~142, cian ~195, azul ~264, magenta ~328)
NOMBRES_HUE = [(40, 'rojo'), (90, 'naranja/piel'), (125, 'amarillo'), (170, 'verde'),
               (225, 'teal/cian'), (290, 'azul'), (345, 'violeta/magenta'), (380, 'rojo')]


def nombre_hue(h):
    for lim, n in NOMBRES_HUE:
        if h < lim:
            return n
    return 'rojo'


def duracion(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def fotogramas(path, n, tmp):
    d = duracion(path)
    salida = []
    for i in range(n):
        t = d * (0.1 + 0.8 * (i + 0.5) / n) if d else 0
        f = os.path.join(tmp, f'{os.path.basename(path)}_{i}.png')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.2f}', '-i', path, '-frames:v', '1',
                        '-vf', 'scale=540:-2', f], check=False)
        if os.path.exists(f):
            salida.append(f)
    return salida


def recortar_franjas(a, umbral=0.06):
    """Saca franjas negras (letterbox/pillarbox) para no falsear la medicion de negros."""
    filas = np.where(a.max(axis=(1, 2)) > umbral)[0]
    cols = np.where(a.max(axis=(0, 2)) > umbral)[0]
    if len(filas) < a.shape[0] * 0.3 or len(cols) < a.shape[1] * 0.3:
        return a  # imagen muy oscura: no recortar
    return a[filas[0]:filas[-1] + 1, cols[0]:cols[-1] + 1]


def cargar(p, ancho=540):
    im = Image.open(p).convert('RGB')
    if im.width > ancho:
        im = im.resize((ancho, round(im.height * ancho / im.width)), Image.LANCZOS)
    return recortar_franjas(np.asarray(im).astype(np.float64) / 255.0)


def medir(img):
    lab = L.lin_to_oklab(img ** 2.4).reshape(-1, 3)   # 709 aprox. -> lineal -> OKLab
    Lm, a, b = lab[:, 0], lab[:, 1], lab[:, 2]
    C = np.hypot(a, b); h = np.degrees(np.arctan2(b, a)) % 360
    m = {}
    p = np.percentile(Lm, [2, 10, 50, 90, 98])
    m['L_negros'], m['L_p10'], m['L_medios'], m['L_p90'], m['L_altas'] = [round(float(x), 4) for x in p]
    m['contraste'] = round(float(p[3] - p[1]), 4)
    m['croma_media'] = round(float(C.mean()), 4)
    bandas = {}
    for nom, lo, hi in [('sombras', 0, .35), ('medios', .35, .65), ('altas', .65, 1.01)]:
        k = (Lm >= lo) & (Lm < hi)
        if k.sum() > 50:
            A, B = a[k].mean(), b[k].mean()
            bandas[nom] = dict(tinte=round(float(np.hypot(A, B)), 4),
                              hue=round(float(np.degrees(np.arctan2(B, A)) % 360), 1),
                              croma=round(float(C[k].mean()), 4), pct=round(float(k.mean()), 3))
    m['bandas'] = bandas
    # piel: tono naranja (hue 35-85), croma moderada, luz media
    sk = (h > 35) & (h < 85) & (C > 0.03) & (C < 0.16) & (Lm > 0.4) & (Lm < 0.9)
    if sk.sum() > 200:
        m['piel'] = dict(hue=round(float(np.median(h[sk])), 1), croma=round(float(np.median(C[sk])), 4),
                         L=round(float(np.median(Lm[sk])), 4), pct=round(float(sk.mean()), 3))
    col = C > 0.04
    if col.sum() > 100:
        hist, _ = np.histogram(h[col], bins=12, range=(0, 360), weights=C[col])
        top = np.argsort(hist)[::-1][:3]
        m['tonos_dominantes'] = [dict(hue=int(i * 30 + 15), nombre=nombre_hue(i * 30 + 15),
                                      peso=round(float(hist[i] / hist.sum()), 3)) for i in top]
    return m


def promedio(lista):
    out = {}
    for k in ['L_negros', 'L_p10', 'L_medios', 'L_p90', 'L_altas', 'contraste', 'croma_media']:
        out[k] = round(float(np.median([x[k] for x in lista])), 4)
    for banda in ['sombras', 'medios', 'altas']:
        v = [x['bandas'][banda] for x in lista if banda in x['bandas']]
        if v:
            A = np.mean([t['tinte'] * np.cos(np.radians(t['hue'])) for t in v])
            B = np.mean([t['tinte'] * np.sin(np.radians(t['hue'])) for t in v])
            out[banda] = dict(tinte=round(float(np.hypot(A, B)), 4),
                              hue=round(float(np.degrees(np.arctan2(B, A)) % 360), 1),
                              croma=round(float(np.median([t['croma'] for t in v])), 4))
    pv = [x['piel'] for x in lista if 'piel' in x]
    if pv:
        out['piel'] = {k: round(float(np.median([p[k] for p in pv])), 4) for k in ['hue', 'croma', 'L']}
    return out


def informe(res, glob_):
    t = ['# Analisis de color de referencias', '',
         f'Fotogramas analizados: {len(res)}', '', '## Resumen (mediana de todos)', '']
    g = glob_
    t.append(f"- Negros (p2): **{g['L_negros']}**  ·  Medios (p50): **{g['L_medios']}**  ·  Altas (p98): **{g['L_altas']}**")
    t.append(f"- Contraste (p90-p10): **{g['contraste']}**  ·  Saturacion media: **{g['croma_media']}**")
    for b in ['sombras', 'medios', 'altas']:
        if b in g:
            x = g[b]
            t.append(f"- {b.capitalize()}: tinte **{x['tinte']}** hacia **{nombre_hue(x['hue'])}** ({x['hue']}°), saturacion {x['croma']}")
    if 'piel' in g:
        p = g['piel']
        t.append(f"- Piel: tono {p['hue']}° ({nombre_hue(p['hue'])}), saturacion {p['croma']}, luz {p['L']}")
    t += ['', '## Guia de lectura', '',
          '- Negros > 0.15 = negros levantados (look "fade"/mate). < 0.08 = negros profundos.',
          '- Contraste > 0.45 = imagen contrastada; < 0.35 = suave.',
          '- Saturacion media: ~0.03 apagado, ~0.06 natural, > 0.09 muy saturado.',
          '- Tinte > 0.01 en una banda = hay color dominante en esa zona (split toning).',
          '- Hue (OKLab): ~29 rojo, ~60 piel/naranja, ~110 amarillo, ~142 verde, ~195 teal, ~264 azul.',
          '', '## Por fotograma', '', '| archivo | negros | medios | altas | contraste | sat | sombras | altas (tinte) |',
          '|---|---|---|---|---|---|---|---|']
    for nombre, m in res:
        s = m['bandas'].get('sombras', {}); a = m['bandas'].get('altas', {})
        t.append(f"| {nombre} | {m['L_negros']} | {m['L_medios']} | {m['L_altas']} | {m['contraste']} | {m['croma_media']} | "
                 f"{s.get('tinte', '-')}@{s.get('hue', '-')} | {a.get('tinte', '-')}@{a.get('hue', '-')} |")
    return '\n'.join(t) + '\n'


def contactos(paths, out, cols=4, ancho=270):
    ims = []
    for p in paths:
        im = Image.open(p).convert('RGB'); im = im.resize((ancho, round(im.height * ancho / im.width)))
        ims.append(im)
    alto = max(i.height for i in ims)
    filas = (len(ims) + cols - 1) // cols
    hoja = Image.new('RGB', (cols * ancho, filas * alto), (20, 20, 20))
    for i, im in enumerate(ims):
        hoja.paste(im, ((i % cols) * ancho, (i // cols) * alto))
    hoja.save(out, quality=88)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('entradas', nargs='+')
    ap.add_argument('--out', required=True)
    ap.add_argument('--frames', type=int, default=6)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    archivos = []
    for e in a.entradas:
        archivos += sorted(glob.glob(os.path.join(e, '*'))) if os.path.isdir(e) else [e]
    tmp = tempfile.mkdtemp()
    imagenes = []
    for f in archivos:
        ext = os.path.splitext(f)[1].lower()
        if ext in VIDEO:
            imagenes += fotogramas(f, a.frames, tmp)
        elif ext in IMAGEN:
            imagenes.append(f)
    if not imagenes:
        sys.exit('No encontre videos ni imagenes.')
    res = [(os.path.basename(p), medir(cargar(p))) for p in imagenes]
    g = promedio([m for _, m in res])
    json.dump(dict(resumen=g, fotogramas={n: m for n, m in res}), open(os.path.join(a.out, 'metricas.json'), 'w'), indent=1)
    open(os.path.join(a.out, 'informe.md'), 'w').write(informe(res, g))
    contactos(imagenes, os.path.join(a.out, 'contactos.jpg'))
    print(informe(res, g).split('## Guia')[0])
    print('ok ->', a.out)


if __name__ == '__main__':
    main()
