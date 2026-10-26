"""Crea (o re-ajusta) un look a partir de capturas/fotogramas de referencia.

Uso:
  python ajustar_look_a_referencias.py CARPETA_REFS --nombre High_Ticket --titulo "High Ticket" \
         --out ../looks/high_ticket.json [--rondas 14] [--base ../looks/otro_look.json]

Como funciona:
  1. Mide las referencias (analizar_referencias.medir): negros, medios, altas, contraste, saturacion,
     tintes por zona y piel.
  2. "Neutraliza" cada referencia (estira niveles, quita tintes por zona, devuelve saturacion normal)
     para simular el material crudo que tendria un video normal.
  3. Busca (descenso por coordenadas) los parametros de lutlib.grade que llevan ese material neutral
     a las metricas de las referencias.
  4. Guarda el JSON del look, listo para generar_look.py.
Tarda ~10-20 min con 25-30 imagenes. Correrlo en segundo plano.
"""
import argparse, glob, json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lutlib as L
import analizar_referencias as A

INICIAL = dict(contrast=1.0, pivot=0.45, black=0.06, white=0.86, sat=0.6,
               shadow_hue=222, shadow_amt=0.01, high_hue=85, high_amt=0.025,
               blue_center=245, blue_width=40, blue_shift=-30, blue_sat=0.8,
               green_center=138, green_width=30, green_shift=-25, green_sat=0.5, green_dark=0.03,
               warm_center=55, warm_width=25, warm_sat=1.6)
CLAVES = ['black', 'white', 'contrast', 'pivot', 'sat', 'warm_sat', 'shadow_amt', 'shadow_hue', 'high_amt',
          'high_hue', 'green_sat', 'blue_sat', 'blue_shift', 'green_shift']
PASO = dict(black=.02, white=.04, contrast=.2, pivot=.04, sat=.1, warm_sat=.2, shadow_amt=.005, shadow_hue=20,
            high_amt=.008, high_hue=15, green_sat=.15, blue_sat=.15, blue_shift=10, green_shift=8)
POSITIVOS = ('sat', 'warm_sat', 'green_sat', 'blue_sat', 'white', 'contrast')
GUARDAR = ['contrast', 'pivot', 'black', 'white', 'sat', 'shadow_hue', 'shadow_amt', 'high_hue', 'high_amt',
           'blue_center', 'blue_width', 'blue_shift', 'blue_sat', 'green_center', 'green_width', 'green_shift',
           'green_sat', 'green_dark', 'warm_center', 'warm_width', 'warm_sat']


def neutralizar(img):
    lab = L.lin_to_oklab(img ** 2.4); Lm, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    p1, p99 = np.percentile(Lm, [1, 99.5])
    Ln = np.clip((Lm - p1) / max(p99 - p1, 1e-3), 0, 1) ** 0.95 * 0.97
    for lo, hi in [(0, .35), (.35, .65), (.65, 1.01)]:
        k = (Lm >= lo) & (Lm < hi)
        if k.sum() > 10:
            a = np.where(k, a - a[k].mean() * 0.9, a); b = np.where(k, b - b[k].mean() * 0.9, b)
    a, b = a * 1.9, b * 1.9
    return np.clip(L.encode_709(np.clip(L.oklab_to_lin(np.stack([Ln, a, b], -1)), 0, 1)), 0, 1)


def _vec(t):
    return np.array([t['tinte'] * np.cos(np.radians(t['hue'])), t['tinte'] * np.sin(np.radians(t['hue']))])


def perdida(m, T):
    e = 0
    for k, w in [('L_negros', 4), ('L_medios', 3), ('L_altas', 3), ('contraste', 2), ('croma_media', 25)]:
        e += w * abs(m[k] - T[k])
    for bnd in ['sombras', 'medios', 'altas']:
        if bnd in m and bnd in T:
            e += 20 * np.abs(_vec(m[bnd]) - _vec(T[bnd])).sum()
    if 'piel' in m and 'piel' in T:
        e += 15 * abs(m['piel']['croma'] - T['piel']['croma']) + 0.01 * abs(m['piel']['hue'] - T['piel']['hue'])
    return e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('refs'); ap.add_argument('--nombre', required=True); ap.add_argument('--titulo', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--rondas', type=int, default=14)
    ap.add_argument('--base', default=None, help='JSON de look para arrancar desde ahi')
    ap.add_argument('--descripcion', default='')
    a = ap.parse_args()

    files = [f for f in sorted(glob.glob(os.path.join(a.refs, '*'))) if f.lower().endswith(A.IMAGEN)]
    refs = [A.cargar(f, 240) for f in files]
    T = A.promedio([A.medir(r) for r in refs])
    prox = [neutralizar(r) for r in refs]
    P = dict(L.DEFAULT); P.update(INICIAL)
    if a.base:
        P.update(json.load(open(a.base))['grade'])
    evalua = lambda P: A.promedio([A.medir(L.encode_709(L.grade(p ** 2.4, P))) for p in prox])
    paso = dict(PASO); e = perdida(evalua(P), T)
    print('referencias', len(refs), 'error inicial', round(e, 4), flush=True)
    for it in range(a.rondas):
        for k in CLAVES:
            for d in (1, -1):
                Q = dict(P); Q[k] = P[k] + d * paso[k]
                if k in POSITIVOS and Q[k] <= 0:
                    continue
                eq = perdida(evalua(Q), T)
                if eq < e:
                    e, P = eq, Q; break
        for k in paso: paso[k] *= 0.75
        print('ronda', it + 1, 'error', round(e, 4), flush=True)
    look = dict(nombre=a.nombre, titulo=a.titulo, descripcion=a.descripcion,
                fuente=f'Ajustado sobre {len(refs)} referencias', gris_display=0.117,
                metricas_referencia=T, metricas_resultado=evalua(P),
                grade={k: round(float(P[k]), 4) for k in GUARDAR})
    json.dump(look, open(a.out, 'w'), indent=1, ensure_ascii=False)
    print('ok', a.out)


if __name__ == '__main__':
    main()
