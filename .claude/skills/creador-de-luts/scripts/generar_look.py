"""Genera las LUTs de un look definido en un JSON (ej. looks/high_ticket.json).

Uso:
  python generar_look.py ../looks/high_ticket.json --out CARPETA [--perfiles dlog,dlog2,rec709] [--size 33]

El JSON tiene:
  "nombre":  prefijo de archivo (ej. "High_Ticket")
  "titulo":  titulo dentro del .cube (ej. "High Ticket")
  "grade":   parametros de lutlib.grade (ver references/parametros.md; incluye "white")
  "gris_display": brillo (display lineal) al que cae el gris 18% en los perfiles LOG (default 0.117,
                  = gris bien expuesto en Rec709)

Perfiles (entrada de la LUT):
  dlog   -> D-Log oficial DJI (curva + D-Gamut)      -> tonemap -> grade -> Rec709
  dlog2  -> D-Log 2 (DJI Osmo Pocket 4P)              -> tonemap -> grade -> Rec709
  rec709 -> material normal ya en Rec709 (celular, camara sin LOG) -> grade -> Rec709
A diferencia de MA Vivo, aca cada LOG se decodifica con SU curva correcta.
"""
import argparse, json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lutlib as L

SUFIJO = {'dlog': 'DLog', 'dlog2': 'DLog2', 'rec709': 'Rec709'}


def cargar_look(path):
    look = json.load(open(path))
    P = dict(L.DEFAULT); P.update(look['grade'])
    return look, P


def _tm_norm(lin, expo, lin_max):
    # tonemap normalizado: el maximo que puede grabar el LOG llega a 1.0 (asi el techo de
    # blancos lo pone el look con "white", igual que en Rec709, y no se aplastan las altas)
    tope = L.tonemap(np.full((1, 3), lin_max), expo)[0, 0]
    return np.clip(L.tonemap(lin, expo) / tope, 0, 1)


def _exposicion_para(gris_display, lin_max):
    # busca la exposicion para que el gris 18% caiga en gris_display (ya normalizado)
    lo, hi = 0.01, 20.0
    for _ in range(60):
        m = (lo * hi) ** 0.5
        v = _tm_norm(np.full((1, 3), 0.18), m, lin_max)[0, 0]
        lo, hi = (m, hi) if v < gris_display else (lo, m)
    return (lo * hi) ** 0.5


def hacer_fn(perfil, P, gris_display=0.117):
    if perfil == 'rec709':
        return lambda v: L.encode_709(L.grade(np.clip(v, 0, 1) ** 2.4, P))
    if perfil == 'dlog':
        dec = lambda c: L.dlog_to_lin(c) @ L.DG_TO_709.T
    elif perfil == 'dlog2':
        dec = lambda c: L.dlog2_to_lin(c) @ L.DG2_TO_709.T
    else:
        raise ValueError(perfil)
    lin_max = float(dec(np.ones((1, 3)))[0].max())
    expo = _exposicion_para(gris_display, lin_max)
    return lambda c: L.encode_709(L.grade(_tm_norm(dec(c), expo, lin_max), P))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('look')
    ap.add_argument('--out', required=True)
    ap.add_argument('--perfiles', default='dlog,dlog2,rec709')
    ap.add_argument('--size', type=int, default=33)
    ap.add_argument('--set', default=None, help='JSON que pisa parametros del grade')
    ap.add_argument('--version', default='', help='sufijo de version, ej. _v2')
    a = ap.parse_args()
    look, P = cargar_look(a.look)
    if a.set:
        P.update(json.loads(a.set))
    os.makedirs(a.out, exist_ok=True)
    for perfil in a.perfiles.split(','):
        nombre = f"{look['nombre']}_{SUFIJO[perfil]}{a.version}.cube"
        path = os.path.join(a.out, nombre)
        L.write_cube(path, hacer_fn(perfil, P, look.get('gris_display', 0.117)), n=a.size,
                     title=f"{look['titulo']} - {SUFIJO[perfil]}{a.version}")
        print('ok', path)


if __name__ == '__main__':
    main()
