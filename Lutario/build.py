#!/usr/bin/env python3
"""Arma Lutario: un solo index.html con las LUTs y las fotos adentro, y la app para Mac.

  python3 Lutario/build.py

Salida:
  Lutario/dist/index.html     la app (se abre en cualquier navegador, sin internet salvo las fuentes)
  Lutario/dist/Lutario.app    app para Mac (abre index.html en el navegador)
  Lutario/dist/Lutario.zip    la app comprimida, para pasarla o bajarla

Para sumar una LUT a la biblioteca de base: agregala en LOOKS (abajo) y volve a correr el script.
"""
import base64, gzip, io, json, os, shutil, stat, zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(AQUI)
DIST = os.path.join(AQUI, "dist")

LOOKS = [
    {"id": "ma-vivo-dia", "nombre": "MA Vivo Día", "estado": "aprobada",
     "descripcion": "Colores vivos, sombras teal, piel cálida y cielo turquesa. Para tomas con luz de día.",
     "variantes": [("dlog", "Powergrade/D-Log/MA_Vivo_DLog_DIA.cube"),
                   ("dlog2", "Powergrade/D-Log 2 (sin probar)/MA_Vivo_DLog2_DIA.cube")]},
    {"id": "ma-vivo-noche", "nombre": "MA Vivo Noche", "estado": "aprobada",
     "descripcion": "El mismo look vivo, pensado para noche e interiores oscuros.",
     "variantes": [("dlog", "Powergrade/D-Log/MA_Vivo_DLog_NOCHE.cube"),
                   ("dlog2", "Powergrade/D-Log 2 (sin probar)/MA_Vivo_DLog2_NOCHE.cube")]},
    {"id": "high-ticket", "nombre": "High Ticket", "estado": "sin probar",
     "descripcion": "Cine premium: saturación baja, piel protegida, negros mate y altas doradas.",
     "variantes": [("dlog", "Powergrade/High Ticket/High_Ticket_DLog.cube"),
                   ("dlog2", "Powergrade/High Ticket/High_Ticket_DLog2.cube"),
                   ("rec709", "Powergrade/High Ticket/High_Ticket_Rec709.cube")]},
]


def b64(data):
    return base64.b64encode(data).decode()


def data_uri(path, mime):
    with open(path, "rb") as f:
        return f"data:{mime};base64,{b64(f.read())}"


def armar_html():
    looks = []
    for l in LOOKS:
        vs = []
        for fmt, ruta in l["variantes"]:
            with open(os.path.join(REPO, ruta), "rb") as f:
                crudo = f.read()
            vs.append({"formato": fmt, "archivo": os.path.basename(ruta), "bytes": len(crudo), "gz": b64(gzip.compress(crudo, 9, mtime=0))})
        looks.append({**{k: v for k, v in l.items() if k != "variantes"}, "variantes": vs})
    data = {"looks": looks,
            "muestras": {k: data_uri(os.path.join(AQUI, "muestras", f"muestra_{k}.jpg"), "image/jpeg")
                         for k in ("dlog", "dlog2", "rec709")}}
    html = open(os.path.join(AQUI, "app.html"), encoding="utf-8").read()
    html = html.replace("__LOGO__", data_uri(os.path.join(AQUI, "logo_128.png"), "image/png"))
    html = html.replace("const DATA=__DATA__;", "const DATA=" + json.dumps(data, ensure_ascii=False) + ";")
    return html


def icono_icns(destino):
    """Icono de la app: el logo sobre un cuadrado redondeado verde menta."""
    from PIL import Image, ImageDraw
    S = 1024
    logo = Image.open(os.path.join(AQUI, "logo.png")).convert("RGBA").resize((640, 640), Image.LANCZOS)
    base = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    d.rounded_rectangle([64, 64, S - 64, S - 64], radius=210, fill=(232, 245, 233, 255), outline=(197, 225, 165, 255), width=8)
    base.alpha_composite(logo, ((S - 640) // 2, (S - 640) // 2 + 10))
    base.save(destino, sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)])
    base.resize((256, 256)).save(os.path.join(DIST, "icono.png"))


def armar_app(html):
    app = os.path.join(DIST, "Lutario.app")
    shutil.rmtree(app, ignore_errors=True)
    os.makedirs(os.path.join(app, "Contents", "MacOS"))
    os.makedirs(os.path.join(app, "Contents", "Resources"))
    with open(os.path.join(app, "Contents", "Info.plist"), "w") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Lutario</string>
  <key>CFBundleDisplayName</key><string>Lutario</string>
  <key>CFBundleIdentifier</key><string>com.snati.lutario</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>lutario</string>
  <key>CFBundleIconFile</key><string>icono</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>LSUIElement</key><true/>
</dict></plist>
""")
    exe = os.path.join(app, "Contents", "MacOS", "lutario")
    with open(exe, "w") as f:
        f.write('#!/bin/bash\n# Abre la biblioteca de LUTs en el navegador predeterminado.\n'
                'open "$(cd "$(dirname "$0")/../Resources" && pwd)/index.html"\n')
    os.chmod(exe, os.stat(exe).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    with open(os.path.join(app, "Contents", "Resources", "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    icono_icns(os.path.join(app, "Contents", "Resources", "icono.icns"))
    # zip conservando el permiso de ejecucion
    z = os.path.join(DIST, "Lutario.zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for raiz, _, archivos in os.walk(app):
            for a in archivos:
                p = os.path.join(raiz, a)
                info = zipfile.ZipInfo(os.path.relpath(p, DIST))
                info.external_attr = (os.stat(p).st_mode & 0xFFFF) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                with open(p, "rb") as fh:
                    zf.writestr(info, fh.read())
    return app, z


def main():
    os.makedirs(DIST, exist_ok=True)
    html = armar_html()
    with open(os.path.join(DIST, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    app, z = armar_app(html)
    print(f"OK index.html {len(html) / 1e6:.1f} MB · {app} · {z} {os.path.getsize(z) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
