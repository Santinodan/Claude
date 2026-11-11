#!/usr/bin/env python3
"""Arma la planilla mensual (.xlsx) a partir de la plantilla de Snati y un CSV de movimientos.

Uso:
    python3 _Herramientas/armar_planilla.py 2026-11 movimientos.csv [-o salida.xlsx]

El CSV (separador ";") tiene estas columnas:
    Hoja;Fecha;Detalle;Categoria;Pesos;USD;Metodo;Cuota;Cantidad;PrecioEntrada;PrecioHoy
  Hoja  = Gasto, Ingreso, Inversion o Ahorro.
  Ahorro (saldo en Binance, dólares en efectivo) va solo al dashboard: en el Excel ya está
  reflejado en "Restante" (ingresos - gastos), así que no se carga en Inversiones.
  Fecha = dd/mm/aaaa.  Números con punto o coma decimal (12500,50 o 12500.50).
  Ingreso:   "Detalle" es quién pagó; usa Pesos y USD.
  Inversion: "Detalle" es el ticker (ej. USDT), "Categoria" el tipo (ej. Earn);
             usa Cantidad, PrecioEntrada y PrecioHoy (en USD).
  Las últimas tres columnas pueden faltar si no hay inversiones.

Qué hace sobre la plantilla (Plantilla_Finanzas.xlsx, bajada del Drive):
  - Pone el mes en Ingresos!B4 y en el título de Resumen General.
  - Carga gastos desde Gastos!B5 e ingresos desde Ingresos!B7.
  - Corrige Ingresos!F4 (total en pesos sumaba la columna USD) y
    Resumen General!C30 (#REF!: ahora toma el valor actual de las inversiones).
  - Si un gasto usa una categoría que no está en la tabla de Gastos (ej. Transporte),
    la agrega a la tabla y al gráfico.
  - Cambia la foto fija del gráfico de torta por un gráfico real que lee Gastos!N6:O12.
El archivo que sale se sube a Drive desde la cuenta personal (Archivo > Importar, o arrastrarlo).
"""
import argparse
import csv
import datetime as dt
from copy import copy
from pathlib import Path

import openpyxl
from openpyxl.chart import DoughnutChart, Reference
from openpyxl.chart.label import DataLabelList

AQUI = Path(__file__).resolve().parent
PLANTILLA = AQUI / "Plantilla_Finanzas.xlsx"
MESES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO",
         "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]


def numero(texto):
    t = (texto or "").replace("$", "").replace("US", "").replace(" ", "")
    if not t:
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    return float(t)


def fecha(texto):
    return dt.datetime.strptime(texto.strip(), "%d/%m/%Y")


def agregar_categorias(gastos, usadas):
    """Suma a la tabla N6:Q12 las categorías usadas que falten. Devuelve la última fila de categoría."""
    existentes = [gastos.cell(r, 14).value for r in range(6, 13)]
    nuevas = []
    for c in usadas:
        if c and c not in existentes and c not in nuevas:
            nuevas.append(c)
    if not nuevas:
        return 12
    estilo_fila = [copy(gastos.cell(12, c)._style) for c in range(14, 18)]
    estilo_total = [copy(gastos.cell(13, c)._style) for c in range(14, 18)]
    ultima = 12 + len(nuevas)
    total = ultima + 1
    rango = "Gastos!$D$5:$D$100"
    for i, cat in enumerate(nuevas):
        f = 13 + i
        vals = [cat, f"=SUMIF({rango},N{f},Gastos!$E$5:$E$100)", "", f"=COUNTIF({rango},N{f})"]
        for j, v in enumerate(vals):
            celda = gastos.cell(f, 14 + j, v)
            celda._style = copy(estilo_fila[j])
    totales = ["TOTAL", f"=SUM(O6:O{ultima})", "", f"=SUM(Q6:Q{ultima})"]
    for j, v in enumerate(totales):
        celda = gastos.cell(total, 14 + j, v)
        celda._style = copy(estilo_total[j])
    for f in range(6, total + 1):
        gastos.cell(f, 16, f'=IFERROR(O{f}/$O${total},"")')
    return ultima


def armar(mes, csv_path, salida):
    anio, m = (int(x) for x in mes.split("-"))
    wb = openpyxl.load_workbook(PLANTILLA)
    gastos, ingresos, resumen = wb["Gastos"], wb["Ingresos"], wb["Resumen General"]

    ingresos["B4"] = dt.datetime(anio, m, 1)
    resumen["B2"] = f"RESUMEN GENERAL — {MESES[m - 1]} {anio}"
    ingresos["F4"] = "=SUM(D7:D14)"
    resumen["C30"] = "=D26"

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        filas = [r for r in csv.DictReader(f, delimiter=";") if any(r.values())]
    filas.sort(key=lambda r: fecha(r["Fecha"]))

    inversiones = wb["Inversiones"]
    fg, fi, fv = 5, 7, 5
    for r in filas:
        hoja = r["Hoja"].strip().lower()
        if hoja.startswith("aho"):
            continue
        if hoja.startswith("inv"):
            v = fv
            inversiones.cell(v, 1, fecha(r["Fecha"])).number_format = "dd/mm/yyyy"
            inversiones.cell(v, 2, r["Detalle"])
            inversiones.cell(v, 3, r["Categoria"])
            inversiones.cell(v, 4, numero(r.get("Cantidad")))
            inversiones.cell(v, 5, numero(r.get("PrecioEntrada")))
            inversiones.cell(v, 6, numero(r.get("PrecioHoy")))
            inversiones.cell(v, 7, f'=IF(AND(D{v}<>"",E{v}<>""),D{v}*E{v},"")')
            inversiones.cell(v, 8, f'=IF(AND(D{v}<>"",F{v}<>""),D{v}*F{v},"")')
            inversiones.cell(v, 9, f'=IFERROR(IF(AND(E{v}<>"",F{v}<>""),(F{v}-E{v})/E{v},""),"")')
            inversiones.cell(v, 10, f'=IF(AND(G{v}<>"",H{v}<>""),H{v}-G{v},"")')
            fv += 1
        elif hoja.startswith("ing"):
            if fi > 14:
                raise SystemExit("Ingresos: la plantilla tiene lugar hasta la fila 14.")
            ingresos.cell(fi, 2, fecha(r["Fecha"])).number_format = "dd/mm"
            ingresos.cell(fi, 3, r["Detalle"])
            ingresos.cell(fi, 4, numero(r.get("Pesos")))
            ingresos.cell(fi, 5, numero(r.get("USD")))
            fi += 1
        else:
            if fg > 99:
                raise SystemExit("Gastos: la plantilla tiene lugar hasta la fila 99.")
            gastos.cell(fg, 2, fecha(r["Fecha"])).number_format = "dd/mm"
            gastos.cell(fg, 3, r["Detalle"])
            gastos.cell(fg, 4, r["Categoria"])
            gastos.cell(fg, 5, numero(r.get("Pesos")))
            gastos.cell(fg, 6, numero(r.get("USD")))
            gastos.cell(fg, 7, r.get("Metodo") or "Mercado Pago")
            cuota = (r.get("Cuota") or "").strip()
            if cuota:
                c = gastos.cell(fg, 8, cuota)
                c.number_format = "@"
            fg += 1

    ultima = agregar_categorias(gastos, [r["Categoria"] for r in filas if r["Hoja"].strip().lower().startswith("gas")])

    # Gráfico de torta vivo en lugar de la imagen exportada por Google.
    gastos._images = []
    torta = DoughnutChart(holeSize=50)
    torta.title = "Gastos por categoría"
    torta.add_data(Reference(gastos, min_col=15, min_row=5, max_row=ultima), titles_from_data=True)
    torta.set_categories(Reference(gastos, min_col=14, min_row=6, max_row=ultima))
    torta.dataLabels = DataLabelList(showPercent=True, showVal=False, showCatName=False,
                                     showSerName=False, showLegendKey=False, showLeaderLines=False)
    torta.width, torta.height = 14, 9
    gastos.add_chart(torta, "R5")

    wb.save(salida)
    return fg - 5, fi - 7


def main():
    p = argparse.ArgumentParser(description="Arma la planilla mensual de finanzas")
    p.add_argument("mes", help="AAAA-MM")
    p.add_argument("csv", help="CSV con los movimientos del mes")
    p.add_argument("-o", "--salida", help="archivo .xlsx de salida")
    a = p.parse_args()
    anio, m = (int(x) for x in a.mes.split("-"))
    salida = a.salida or f"{MESES[m - 1].capitalize()} {anio} - Finanzas personales.xlsx"
    ng, ni = armar(a.mes, a.csv, salida)
    print(f"{salida}: {ng} gastos, {ni} ingresos")


if __name__ == "__main__":
    main()
