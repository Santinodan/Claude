"""Aplica una o varias LUT .cube a un fotograma LOG y arma una comparativa vertical.

Uso:
  python preview.py --frame frame_log.png --out comparativa.png \
         LUT1.cube [LUT2.cube ...] [--ref referencia.png] [--etiquetas "v1,v2"]

- El fotograma tiene que ser el clip LOG SIN ningun filtro (sacalo con
  `ffmpeg -ss 00:00:03 -i clip.mp4 -frames:v 1 frame_log.png`).
- Imprime ademas metricas OKLab (luminancia p2/p50/p98 y croma medio) por LUT,
  utiles para comparar contra la referencia sin tener que mirar la imagen.
"""
import argparse, os, sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lutlib as L


def cargar(path, ancho=None):
    im = Image.open(path).convert('RGB')
    if ancho and im.width != ancho:
        im = im.resize((ancho, round(im.height * ancho / im.width)), Image.LANCZOS)
    return np.asarray(im).astype(np.float64) / 255.0


def metricas(img709):
    lab = L.lin_to_oklab(np.clip(img709, 0, 1) ** 2.4).reshape(-1, 3)
    Lm = lab[:, 0]; C = np.hypot(lab[:, 1], lab[:, 2])
    s = f'L p2/p50/p98={np.round(np.percentile(Lm, [2, 50, 98]), 3)} croma={C.mean():.3f} |'
    for lo, hi in [(0, .3), (.3, .45), (.45, .6), (.6, .75), (.75, 1.01)]:
        m = (Lm >= lo) & (Lm < hi)
        if m.any():
            a, b = lab[m, 1].mean(), lab[m, 2].mean()
            s += f' {np.hypot(a, b):.3f}@{np.degrees(np.arctan2(b, a)) % 360:.0f}'
    return s


def rotulo(img, texto):
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    banda = Image.new('RGB', (im.width, 36), (17, 17, 17))
    ImageDraw.Draw(banda).text((10, 10), texto, fill=(240, 240, 240))
    out = Image.new('RGB', (im.width, im.height + 36))
    out.paste(banda, (0, 0)); out.paste(im, (0, 36))
    return np.asarray(out).astype(np.float64) / 255.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('luts', nargs='+')
    ap.add_argument('--frame', required=True)
    ap.add_argument('--ref', default=None)
    ap.add_argument('--out', required=True)
    ap.add_argument('--etiquetas', default=None)
    ap.add_argument('--ancho', type=int, default=960)
    a = ap.parse_args()

    frame = cargar(a.frame, a.ancho)
    etiquetas = a.etiquetas.split(',') if a.etiquetas else [os.path.basename(p) for p in a.luts]
    filas = [rotulo(frame, 'LOG original')]
    for p, et in zip(a.luts, etiquetas):
        n, lut = L.read_cube(p)
        o = L.apply_cube(frame, n, lut)
        print(f'{et:30s} {metricas(o)}')
        filas.append(rotulo(o, et))
    if a.ref:
        r = cargar(a.ref, a.ancho)
        print(f'{"REFERENCIA":30s} {metricas(r)}')
        filas.append(rotulo(r, 'Referencia'))
    Image.fromarray((np.concatenate(filas, 0) * 255).astype(np.uint8)).save(a.out)
    print('ok', a.out)


if __name__ == '__main__':
    main()
