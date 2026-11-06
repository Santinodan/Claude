"""Genera el icono de Frutilla Finanzas (1024x1024, sin transparencia).

Uso: python3 Herramientas/generar_icono.py [salida.png]
Dibuja una frutilla simple sobre fondo rosa. Se renderiza a 4x y se achica para suavizar bordes.
"""
import math
import sys
from PIL import Image, ImageDraw, ImageFilter

TAM = 1024
K = 4  # supersampling
W = TAM * K

FRUTILLA = (227, 43, 74)
FRUTILLA_OSCURA = (190, 26, 58)
HOJA = (47, 168, 90)
HOJA_OSCURA = (31, 132, 68)
SEMILLA = (255, 226, 150)


def degradado_vertical(w, h, arriba, abajo):
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / (h - 1)
        c = tuple(int(arriba[i] + (abajo[i] - arriba[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = c
    return img


def casco_convexo(puntos):
    pts = sorted(set(puntos))
    def cruz(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    abajo, arriba = [], []
    for p in pts:
        while len(abajo) >= 2 and cruz(abajo[-2], abajo[-1], p) <= 0:
            abajo.pop()
        abajo.append(p)
    for p in reversed(pts):
        while len(arriba) >= 2 and cruz(arriba[-2], arriba[-1], p) <= 0:
            arriba.pop()
        arriba.append(p)
    return abajo[:-1] + arriba[:-1]


def forma_frutilla(cx, cy, s):
    """Elipse ancha arriba + círculo chico abajo, unidos por su casco convexo."""
    pts = []
    for i in range(720):
        a = 2 * math.pi * i / 720
        pts.append((cx + 0.40 * s * math.cos(a), cy - 0.10 * s + 0.27 * s * math.sin(a)))
        pts.append((cx + 0.11 * s * math.cos(a), cy + 0.33 * s + 0.11 * s * math.sin(a)))
    return casco_convexo([(round(x, 2), round(y, 2)) for x, y in pts])


def main(salida):
    # Fondo rosa (degradado suave).
    fondo = degradado_vertical(W // 8, W // 8, (255, 214, 221), (255, 160, 176)).resize((W, W), Image.BICUBIC)
    img = fondo.convert("RGBA")

    cx, cy, s = W / 2, W * 0.535, W * 0.80
    cuerpo = forma_frutilla(cx, cy, s)

    # Sombra suave debajo.
    sombra = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    ImageDraw.Draw(sombra).polygon([(x, y + W * 0.025) for x, y in cuerpo], fill=(160, 20, 50, 90))
    sombra = sombra.filter(ImageFilter.GaussianBlur(W * 0.02))
    img = Image.alpha_composite(img, sombra)

    # Cuerpo con un leve degradado (más oscuro abajo).
    mascara = Image.new("L", (W, W), 0)
    ImageDraw.Draw(mascara).polygon(cuerpo, fill=255)
    relleno = degradado_vertical(W // 8, W // 8, FRUTILLA, FRUTILLA_OSCURA).resize((W, W), Image.BICUBIC).convert("RGBA")
    capa = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    capa.paste(relleno, (0, 0), mascara)
    img = Image.alpha_composite(img, capa)

    # Semillas en filas escalonadas, solo dentro del cuerpo.
    d = ImageDraw.Draw(img)
    paso = 0.115 * s
    fila = 0
    y = cy - 0.24 * s
    while y < cy + 0.38 * s:
        desfase = (paso / 2) if fila % 2 else 0
        x = cx - 0.45 * s + desfase
        while x < cx + 0.45 * s:
            margen = 0.035 * s
            dentro = all(mascara.getpixel((int(x + dx), int(y + dy))) > 0
                         for dx, dy in ((margen, 0), (-margen, 0), (0, margen), (0, -margen)))
            if dentro:
                rx, ry = 0.013 * s, 0.02 * s
                d.ellipse([x - rx, y - ry, x + rx, y + ry], fill=SEMILLA)
            x += paso
        y += paso * 0.86
        fila += 1

    # Hojas (cáliz) arriba: 5 hojas puntiagudas.
    hojas = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    dh = ImageDraw.Draw(hojas)
    hx, hy = cx, cy - 0.33 * s
    angulos = [-160, -120, -90, -60, -20]
    largos = [0.25, 0.22, 0.16, 0.22, 0.25]
    for ang, largo in zip(angulos, largos):
        a = math.radians(ang)
        punta = (hx + largo * s * math.cos(a), hy + largo * s * math.sin(a) + 0.07 * s)
        perp = a + math.pi / 2
        ancho = 0.07 * s
        base1 = (hx + ancho * math.cos(perp), hy + ancho * math.sin(perp) + 0.03 * s)
        base2 = (hx - ancho * math.cos(perp), hy - ancho * math.sin(perp) + 0.03 * s)
        dh.polygon([base1, punta, base2], fill=HOJA)
    dh.ellipse([hx - 0.11 * s, hy - 0.02 * s, hx + 0.11 * s, hy + 0.09 * s], fill=HOJA)
    # Cabito.
    dh.rounded_rectangle([hx - 0.025 * s, hy - 0.13 * s, hx + 0.025 * s, hy + 0.03 * s], radius=0.025 * s, fill=HOJA_OSCURA)
    img = Image.alpha_composite(img, hojas)

    final = img.convert("RGB").resize((TAM, TAM), Image.LANCZOS)
    final.save(salida, "PNG")
    print("Icono guardado en", salida, final.size, final.mode)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "icono.png")
