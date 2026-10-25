"""Crea una LUT nueva aplicando ajustes ENCIMA de una LUT ya aprobada.

Es la forma segura de iterar: el look aprobado no se toca, solo se le suma un
retoque (mas calido, mas brillo, menos saturacion, etc.).

Uso:
  python ajustar_cube.py BASE.cube SALIDA.cube --titulo "MA Vivo - D-Log - Dia v2" \
      [--expo 0.3] [--contraste 1.1] [--sat 1.1] [--temp 0.01] [--tinte 0] \
      [--sombras-teal 0.01] [--piel 1.1] [--cielo 1.1] [--negro 0.02] [--mezcla 1.0]

Todos los ajustes se hacen en OKLab sobre la salida Rec.709 de la LUT base.
  --expo          stops de exposicion (+0.3 = un poco mas claro)
  --contraste     1.0 = igual; >1 mas contraste (pivote en medios)
  --sat           saturacion global (1.0 = igual)
  --temp          + calido / - frio (0.01 es sutil)
  --tinte         + magenta / - verde
  --sombras-teal  cuanto teal extra en sombras
  --piel          saturacion de naranjas/piel (hue ~60)
  --cielo         saturacion de azules/cielo (hue ~240)
  --negro         levanta negros (fade); 0.02 es sutil
  --mezcla        intensidad del retoque 0..1 (1 = completo)
"""
import argparse, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lutlib as L


def retoque(rgb709, a):
    lin = np.clip(rgb709, 0, 1) ** 2.4 * (2.0 ** a.expo)
    lab = L.lin_to_oklab(np.clip(lin, 0, None))
    Lc, A, B = lab[..., 0], lab[..., 1], lab[..., 2]
    C = np.hypot(A, B); h = np.degrees(np.arctan2(B, A)) % 360
    wp, _ = L._hue_w(h, 60.0, 25.0)
    wc, _ = L._hue_w(h, 240.0, 35.0)
    C = C * a.sat * (1 + wp * (a.piel - 1)) * (1 + wc * (a.cielo - 1))
    A, B = C * np.cos(np.radians(h)), C * np.sin(np.radians(h))
    Lc = 0.5 + (Lc - 0.5) * a.contraste
    Lc = a.negro + (1 - a.negro) * np.clip(Lc, 0, 1)
    ws = np.clip((0.6 - Lc) / 0.6, 0, 1) ** 1.3
    A = A + ws * a.sombras_teal * np.cos(np.radians(185)) + a.tinte
    B = B + ws * a.sombras_teal * np.sin(np.radians(185)) + a.temp
    out = L.encode_709(np.clip(L.oklab_to_lin(np.stack([Lc, A, B], -1)), 0, 1))
    return rgb709 + (out - rgb709) * a.mezcla


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('base'); ap.add_argument('salida')
    ap.add_argument('--titulo', default=None)
    for k, d in [('expo', 0.0), ('contraste', 1.0), ('sat', 1.0), ('temp', 0.0), ('tinte', 0.0),
                 ('sombras-teal', 0.0), ('piel', 1.0), ('cielo', 1.0), ('negro', 0.0), ('mezcla', 1.0)]:
        ap.add_argument('--' + k, type=float, default=d)
    a = ap.parse_args()
    n, lut = L.read_cube(a.base)
    nuevo = np.clip(retoque(lut.reshape(-1, 3), a), 0, 1)
    titulo = a.titulo or os.path.splitext(os.path.basename(a.salida))[0]
    with open(a.salida, 'w') as f:
        f.write(f'TITLE "{titulo}"\nLUT_3D_SIZE {n}\nDOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n\n')
        for r, g, b in nuevo:
            f.write(f'{r:.6f} {g:.6f} {b:.6f}\n')
    print('ok', a.salida)


if __name__ == '__main__':
    main()
