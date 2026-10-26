#!/usr/bin/env python3
"""Convierte una foto normal (sRGB / Rec709) a como se veria grabada en LOG por la DJI Osmo Pocket 4P.

Sirve para tener fotos de prueba de looks cuando no hay una captura real:
  sRGB -> lineal -> expansion suave de altas luces (para que las LUTs tengan rango) ->
  gamut D-Gamut / D-Gamut2 -> curva D-Log / D-Log 2.

Uso:
  python3 foto_a_log.py foto.jpg salida_dlog.jpg --perfil dlog
  python3 foto_a_log.py foto.jpg salida_dlog2.jpg --perfil dlog2
"""
import argparse, os, sys
import numpy as np
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "..", "creador-de-luts", "scripts"))
import lutlib  # noqa: E402  (curvas y matrices DJI que ya usamos para crear las LUTs)


def srgb_a_lineal(v):
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def lin_a_dlog(y):
    """Inversa exacta de lutlib.dlog_to_lin (paper oficial de DJI)."""
    y = np.maximum(y, 0)
    corte = (0.14 - 0.0929) / 6.025
    return np.where(y <= corte, y * 6.025 + 0.0929, (np.log10(y * 0.9892 + 0.0108) + 2.27752) / 3.89616)


def convertir(src, perfil, expansion=0.72, exposicion=1.0):
    rgb = np.asarray(Image.open(src).convert("RGB"), dtype=np.float64) / 255.0
    lin = srgb_a_lineal(rgb) * exposicion
    # una foto ya viene "tonemapeada": le devolvemos algo de rango a las altas luces (1.0 -> ~3.6)
    lin = lin / np.maximum(1e-4, 1.0 - expansion * np.clip(lin, 0, 0.999))
    if perfil == "dlog2":
        dg = lin @ lutlib._709_TO_DG2.T
        code = lutlib.lin_to_dlog2(np.maximum(dg, 0))
    else:
        dg = lin @ np.linalg.inv(lutlib.DG_TO_709).T
        code = lin_a_dlog(dg)
    return Image.fromarray((np.clip(code, 0, 1) * 255 + 0.5).astype(np.uint8))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entrada")
    ap.add_argument("salida")
    ap.add_argument("--perfil", choices=["dlog", "dlog2"], default="dlog")
    ap.add_argument("--exposicion", type=float, default=1.0, help="multiplicador de exposicion lineal")
    a = ap.parse_args()
    convertir(a.entrada, a.perfil, exposicion=a.exposicion).save(a.salida, quality=92)
    print("OK", a.salida)


if __name__ == "__main__":
    main()
