#!/usr/bin/env python3
"""Junta los CSV mensuales y arma los archivos del dashboard "Finanzas personales".

Uso:
    python3 _Herramientas/exportar_dashboard.py carpeta_salida mes1.csv [mes2.csv ...]

Cada CSV de entrada es el mismo que usa armar_planilla.py
(Hoja;Fecha;Detalle;Categoria;Pesos;USD;Metodo;Cuota;Cantidad;PrecioEntrada;PrecioHoy).
Sale:
    gastos.csv    id,mes,fecha,detalle,categoria,pesos,usd,metodo,cuota
    ingresos.csv  id,mes,fecha,quien_pago,pesos,usd
    ahorro.csv    id,mes,fecha,activo,tipo,cantidad,precio_usd,valor_usd
Después se suben al dashboard y cada fuente pasa a apuntar al archivo nuevo.
"""
import csv
import datetime as dt
import sys
from pathlib import Path


def numero(t):
    t = (t or "").strip()
    if not t:
        return ""
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    return float(t)


def iso(f):
    return dt.datetime.strptime(f.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    salida = Path(sys.argv[1])
    salida.mkdir(parents=True, exist_ok=True)
    filas = []
    for ruta in sys.argv[2:]:
        with open(ruta, encoding="utf-8-sig", newline="") as f:
            filas += [r for r in csv.DictReader(f, delimiter=";") if any(r.values())]
    filas.sort(key=lambda r: iso(r["Fecha"]))

    def tipo(r):
        return r["Hoja"].strip().lower()[:3]

    with open(salida / "gastos.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "mes", "fecha", "detalle", "categoria", "pesos", "usd", "metodo", "cuota"])
        for i, r in enumerate([r for r in filas if tipo(r) == "gas"], 1):
            d = iso(r["Fecha"])
            w.writerow([i, d[:7], d, r["Detalle"], r["Categoria"], numero(r["Pesos"]), numero(r["USD"]),
                        r.get("Metodo") or "Mercado Pago", r.get("Cuota") or ""])
    with open(salida / "ingresos.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "mes", "fecha", "quien_pago", "pesos", "usd"])
        for i, r in enumerate([r for r in filas if tipo(r) == "ing"], 1):
            d = iso(r["Fecha"])
            w.writerow([i, d[:7], d, r["Detalle"], numero(r["Pesos"]) or 0, numero(r["USD"]) or 0])
    with open(salida / "ahorro.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "mes", "fecha", "activo", "tipo", "cantidad", "precio_usd", "valor_usd"])
        for i, r in enumerate([r for r in filas if tipo(r) == "inv"], 1):
            d = iso(r["Fecha"])
            c, p = numero(r.get("Cantidad")) or 0, numero(r.get("PrecioHoy")) or 0
            w.writerow([i, d[:7], d, r["Detalle"], r["Categoria"], c, p, round(c * p, 2)])
    print(f"Listo en {salida}")


if __name__ == "__main__":
    main()
