"""Genera la familia de LUTs "MA Vivo" (D-Log / D-Log 2, Dia / Noche).

Uso:
  python generar_familia.py --out CARPETA [--params final_params.json] [--boost boost_params.json]
                            [--size 33] [--prefijo MA_Vivo] [--titulo "MA Vivo"]
                            [--set '{"sat":1.1}'] [--set-boost '{"pivot":0.42}']
                            [--solo DLog_NOCHE,DLog_DIA]

Pipeline por cada pixel (codigo LOG 0-1):
  1. Decodificar con la curva D-Log2 -> lineal  (SIEMPRE D-Log2, tambien para clips D-Log:
     asi se aprobo el look; el D-Log se compensa con el multiplicador de exposicion)
  2. Matriz D-Gamut2 -> Rec.709 lineal, x multiplicador de exposicion de la variante
  3. tonemap (rodilla de altas + curva ACES aprox.)          -> params "final"
  4. grade en OKLab (contraste, tonos por color, split toning) -> params "final"
  5. encode Rec.709 (gamma 2.4)
  6. "boost": segundo grade sobre la imagen ya en 709          -> params "boost"
"""
import argparse, json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lutlib as L

AQUI = os.path.dirname(os.path.abspath(__file__))

# Base del "boost" (segundo pase). boost_params.json se aplica encima.
BOOST_BASE = dict(L.DEFAULT)
BOOST_BASE.update(dict(exposure=1, contrast=0.55, pivot=0.45, black=-0.07,
    shadow_hue=185, shadow_amt=0.030, high_hue=75, high_amt=0.030, sat=1.18,
    blue_center=240, blue_width=40, blue_shift=-35, blue_sat=1.25,
    green_center=138, green_width=25, green_shift=-8, green_sat=0.8, green_dark=0.03,
    warm_center=60, warm_width=25, warm_sat=1.12))

# El gris 18% de D-Log (codigo 0.3996) leido con la curva D-Log2 cae ~1.58 stops por encima.
DLOG_GREY_COMP = float(0.18 / L.dlog2_to_lin(np.array(0.3996)))

# clave: (multiplicador de exposicion, sufijo de titulo, subcarpeta)
VARIANTES = {
    # IDENTICA byte a byte a Powergrade/D-Log/MA_Vivo_DLog_NOCHE.cube (el look aprobado)
    'DLog_NOCHE':  (1.0,                  'D-Log - Noche',  'D-Log'),
    # ~= Powergrade/D-Log 2 (sin probar)/MA_Vivo_DLog2_NOCHE.cube (dif. max 0.028)
    'DLog2_NOCHE': (1.0 / DLOG_GREY_COMP, 'D-Log2 - Noche', 'D-Log 2 (sin probar)'),
    # OJO: las DIA aprobadas se retocaron a mano con params que no se guardaron.
    # Estas dos son solo un punto de partida; para trabajar sobre las DIA aprobadas
    # usar ajustar_cube.py sobre los .cube de Powergrade/.
    'DLog_DIA':    (DLOG_GREY_COMP,       'D-Log - Dia',    'D-Log'),
    'DLog2_DIA':   (1.0 / 2.0,            'D-Log2 - Dia',   'D-Log 2 (sin probar)'),
}


def cargar(path, base, extra):
    p = dict(base)
    if path:
        p.update(json.load(open(path)))
    if extra:
        p.update(json.loads(extra))
    return p


def hacer_fn(P, B, mult):
    def boost(v):
        return L.encode_709(L.grade(np.clip(v, 0, 1) ** 2.4, B))
    def vivo(codes):
        lin = L.dlog2_to_lin(codes) @ L.DG2_TO_709.T * mult
        return boost(L.encode_709(L.grade(L.tonemap(lin, P['exposure']), P)))
    return vivo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--params', default=os.path.join(AQUI, 'final_params.json'))
    ap.add_argument('--boost', default=os.path.join(AQUI, 'boost_params.json'))
    ap.add_argument('--set', default=None, help='JSON que pisa params "final"')
    ap.add_argument('--set-boost', default=None, help='JSON que pisa params "boost"')
    ap.add_argument('--size', type=int, default=33)
    ap.add_argument('--prefijo', default='MA_Vivo')
    ap.add_argument('--titulo', default='MA Vivo')
    ap.add_argument('--solo', default=None, help='lista separada por comas de variantes')
    ap.add_argument('--plano', action='store_true', help='no crear subcarpetas')
    ap.add_argument('--mult', type=float, default=None,
                    help='variante libre: multiplicador de exposicion (usa --nombre)')
    ap.add_argument('--nombre', default='Custom', help='nombre de la variante libre')
    a = ap.parse_args()

    P = cargar(a.params, L.DEFAULT, a.set)
    B = cargar(a.boost, BOOST_BASE, a.set_boost)
    if a.mult is not None:
        VARIANTES[a.nombre] = (a.mult, a.nombre.replace('_', ' - '), '')
        elegidas = [a.nombre]
    else:
        elegidas = a.solo.split(',') if a.solo else list(VARIANTES)
    for k in elegidas:
        mult, suf, sub = VARIANTES[k]
        d = a.out if a.plano else os.path.join(a.out, sub)
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f'{a.prefijo}_{k}.cube')
        L.write_cube(path, hacer_fn(P, B, mult), n=a.size, title=f'{a.titulo} - {suf}')
        print('ok', path)


if __name__ == '__main__':
    main()
