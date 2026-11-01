#!/usr/bin/env python3
"""Arma un resumen legible de las transcripciones para que Claude elija historia y correcciones.

Uso:
  python3 resumen.py <vlog.json>        (escribe e imprime _edicion/transcripcion.txt)

Por clip: datos + frases con tiempos DEL CLIP. Marca con '!!' los posibles errores/arranques
falsos (frases repetidas cerca, "perdon", "mejor dicho", "de nuevo"...). Son CANDIDATOS:
decide Claude leyendo el contexto y los pone en historia.json -> "quitar".
"""
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402

MARCAS = ("perdon", "mejor dicho", "de nuevo", "otra vez", "corto", "arranco de nuevo",
          "lo digo de nuevo", "no no", "me equivoque", "repito")


def norm(w):
    w = unicodedata.normalize("NFKD", w.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", w)


def palabras_clip(tx):
    out = []
    for s in tx.get("segmentos", []):
        for w in s.get("palabras", []):
            out.append((w["inicio"], w["fin"], w["palabra"], norm(w["palabra"])))
    return out


def candidatos_correccion(pal):
    """Busca n-gramas (>=2 palabras con contenido) que se repiten a <= 8 s: tipico arranque falso."""
    res = []
    n = len(pal)
    i = 0
    while i < n:
        hallado = False
        for j in range(i + 2, min(n, i + 16)):
            if pal[j][0] - pal[i][0] > 8:
                break
            k = 0
            while j + k < n and i + k < j and pal[i + k][3] and pal[i + k][3] == pal[j + k][3]:
                k += 1
            contenido = sum(len(pal[i + q][3]) >= 4 for q in range(k))
            if k >= 3 or (k >= 2 and contenido >= 1):
                res.append((pal[i][0], pal[j][0], " ".join(p[2] for p in pal[i:i + k])))
                i = j
                hallado = True
                break
        if not hallado:
            i += 1
    texto = " ".join(p[3] for p in pal)
    for m in MARCAS:
        if m.replace(" ", "") and m in texto.replace("  ", " "):
            for idx in range(len(pal)):
                if " ".join(p[3] for p in pal[idx:idx + len(m.split())]) == m:
                    res.append((pal[idx][0], pal[idx][1], f'dice "{m}"'))
    return sorted(res)


def armar(cfg, edicion):
    lineas = [f"# Transcripcion - {cfg.get('titulo', '')}",
              "Tiempos = segundos DEL CLIP (m:ss.s). '!!' = posible correccion (decidir con el contexto).", ""]
    total = 0.0
    for c in cfg["material"]["clips"]:
        if c.get("descartado"):
            continue
        total += c.get("duracion", 0)
        cab = (f"## [{c.get('orden', '')}] {c['archivo']} | {comun.tc(c.get('duracion', 0))} | "
               f"{c.get('perfil', '')}{' | BROLL' if c.get('broll') else ''}"
               f"{' | hora ' + c['hora'] if c.get('hora') else ''}")
        lineas.append(cab)
        tx = comun.leer_json(os.path.join(edicion, "transcripciones",
                                          comun.nombre_seguro(c["archivo"]) + ".json"))
        if not tx:
            lineas.append("   (sin transcripcion: b-roll / sin audio / falta transcribir)\n")
            continue
        pal = palabras_clip(tx)
        habla = sum(s["fin"] - s["inicio"] for s in tx["segmentos"])
        lineas.append(f"   habla {habla:.0f}s de {c.get('duracion', 0):.0f}s, {len(pal)} palabras")
        for s in tx["segmentos"]:
            lineas.append(f"   {comun.tc(s['inicio'])}-{comun.tc(s['fin'])}  {s['texto']}")
        for a, b, que in candidatos_correccion(pal):
            lineas.append(f"   !! {comun.tc(a)}..{comun.tc(b)}  {que}")
        lineas.append("")
    lineas.append(f"Total material (sin descartados): {comun.tc(total)}")
    return "\n".join(lineas) + "\n"


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return
    vlog = os.path.abspath(sys.argv[1])
    _, cfg = comun.cargar_vlog(vlog)
    edicion = comun.dir_edicion(vlog)
    txt = armar(cfg, edicion)
    with open(os.path.join(edicion, "transcripcion.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    print(txt)


if __name__ == "__main__":
    main()
