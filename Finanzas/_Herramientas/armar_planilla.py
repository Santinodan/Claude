#!/usr/bin/env python3
"""Arma la planilla mensual (.xlsx) a partir de la plantilla de Snati y un CSV de movimientos.

Uso:
    python3 _Herramientas/armar_planilla.py 2026-11 movimientos.csv [-o salida.xlsx]

El CSV (separador ";") tiene estas columnas:
    Hoja;Fecha;Detalle;Categoria;Pesos;USD;Metodo;Cuota
  Hoja  = Gasto o Ingreso.
  Fecha = dd/mm/aaaa.  Pesos/USD con punto o coma decimal (12500,50 o 12500.50).
  En Ingreso, "Detalle" es quién pagó; Categoria/Metodo/Cuota se ignoran.

Qué hace sobre la plantilla (Plantilla_Finanzas.xlsx, bajada del Drive):
  - Pone el mes en Ingresos!B4 y en el título de Resumen General.
  - Carga gastos desde Gastos!B5 e ingresos desde Ingresos!B7.
  - Corrige Ingresos!F4 (total en pesos sumaba la columna USD).
  - Cambia la foto fija del gráfico de torta por un gráfico real que lee Gastos!N6:O12.
El archivo que sale se sube a Drive desde la cuenta personal (Archivo > Importar, o arrastrarlo).
"""
import argparse
import csv
import datetime as dt
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


def armar(mes, csv_path, salida):
    anio, m = (int(x) for x in mes.split("-"))
    wb = openpyxl.load_workbook(PLANTILLA)
    gastos, ingresos, resumen = wb["Gastos"], wb["Ingresos"], wb["Resumen General"]

    ingresos["B4"] = dt.datetime(anio, m, 1)
    resumen["B2"] = f"RESUMEN GENERAL — {MESES[m - 1]} {anio}"
    ingresos["F4"] = "=SUM(D7:D14)"

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        filas = [r for r in csv.DictReader(f, delimiter=";") if any(r.values())]
    filas.sort(key=lambda r: fecha(r["Fecha"]))

    fg, fi = 5, 7
    for r in filas:
        if r["Hoja"].strip().lower().startswith("ing"):
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

    # Gráfico de torta vivo en lugar de la imagen exportada por Google.
    gastos._images = []
    torta = DoughnutChart(holeSize=50)
    torta.title = "Gastos por categoría"
    torta.add_data(Reference(gastos, min_col=15, min_row=5, max_row=12), titles_from_data=True)
    torta.set_categories(Reference(gastos, min_col=14, min_row=6, max_row=12))
    torta.dataLabels = DataLabelList()
    torta.dataLabels.showPercent = True
    torta.width, torta.height = 12, 7.5
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
