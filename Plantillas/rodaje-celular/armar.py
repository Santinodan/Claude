#!/usr/bin/env python3
"""Arma la hoja de rodaje para celular a partir de un reels.json.

Uso:
    python3 Plantillas/rodaje-celular/armar.py Clientes/<cliente>/<rodaje>/reels.json

Genera rodaje_celular.html al lado del reels.json.
"""
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    datos_path = Path(sys.argv[1]).resolve()
    datos = json.loads(datos_path.read_text(encoding="utf-8"))

    # Chequeos rápidos para no publicar algo roto
    ids = {p["id"] for p in datos["piezas"]}
    for p in datos["piezas"]:
        for k in p["lugares"]:
            if k not in datos["lugares"]:
                sys.exit(f"{p['id']}: lugar '{k}' no está en 'lugares'")
    for bloque in datos.get("plan", []) + datos.get("pendientes", []):
        faltan = set(bloque.get("piezas", [])) - ids
        if faltan:
            sys.exit(f"Piezas inexistentes referenciadas: {sorted(faltan)}")

    plantilla = (AQUI / "plantilla.html").read_text(encoding="utf-8")
    js = json.dumps(datos, ensure_ascii=False).replace("</", "<\\/")
    if datos.get("titulo"):
        plantilla = plantilla.replace("<title>Rodaje China</title>", f"<title>{datos['titulo']}</title>", 1)
    salida = datos_path.parent / "rodaje_celular.html"
    salida.write_text(plantilla.replace("__DATOS__", js, 1), encoding="utf-8")
    print(f"OK -> {salida} ({len(datos['piezas'])} piezas)")


if __name__ == "__main__":
    main()
