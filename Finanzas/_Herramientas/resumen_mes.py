#!/usr/bin/env python3
"""Arma el resumen de un mes a partir de los CSV de Finanzas/.

Uso:
    python3 _Herramientas/resumen_mes.py            # mes actual
    python3 _Herramientas/resumen_mes.py 2026-11    # un mes puntual

Lee todos los .csv de Movimientos/ (mismo formato que exporta Frutilla Finanzas:
"Fecha;Tipo;Monto;Moneda;Categoría;Cuenta;Cuenta destino;Nota", fecha dd/mm/aaaa,
coma decimal, gastos en negativo), más Cobros_Clientes.csv y Gastos_Fijos.csv.
Escribe Resumenes/AAAA-MM.md y lo muestra en pantalla.
Las monedas no se mezclan: cada una tiene su propio total.
"""
import argparse
import csv
import datetime as dt
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def leer_csv(ruta):
    if not ruta.exists():
        return []
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        return [
            {(k or "").strip(): (v or "").strip() for k, v in fila.items()}
            for fila in csv.DictReader(f, delimiter=";")
            if any((v or "").strip() for v in fila.values())
        ]


def monto(texto):
    """'-12.500,50' -> -12500.5 ; '12500.5' -> 12500.5"""
    t = texto.replace("$", "").replace(" ", "")
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    return float(t) if t else 0.0


def fecha(texto):
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(texto, formato).date()
        except ValueError:
            pass
    return None


def plata(valor, moneda):
    signo = "-" if valor < 0 else ""
    entero, dec = f"{abs(valor):.2f}".split(".")
    entero = f"{int(entero):,}".replace(",", ".")
    return f"{signo}{moneda} {entero}" + ("" if dec == "00" else f",{dec}")


def movimientos_del_mes(anio, mes):
    vistos, filas = set(), []
    for ruta in sorted((BASE / "Movimientos").glob("*.csv")):
        for m in leer_csv(ruta):
            f = fecha(m.get("Fecha", ""))
            if not f or (f.year, f.month) != (anio, mes):
                continue
            clave = tuple(m.get(k, "") for k in ("Fecha", "Tipo", "Monto", "Moneda", "Categoría", "Cuenta", "Nota"))
            if clave in vistos:  # el mismo movimiento en dos exportaciones
                continue
            vistos.add(clave)
            filas.append(m)
    return filas


def armar(anio, mes):
    nombre_mes = f"{anio}-{mes:02d}"
    movs = movimientos_del_mes(anio, mes)

    ingresos = defaultdict(float)
    gastos = defaultdict(float)
    por_categoria = defaultdict(lambda: defaultdict(float))
    for m in movs:
        tipo = m.get("Tipo", "").lower()
        if tipo == "transferencia":
            continue
        valor = monto(m.get("Monto", "0"))
        mon = m.get("Moneda") or "ARS"
        cat = m.get("Categoría") or "Sin categoría"
        if tipo == "ingreso" or (tipo != "gasto" and valor > 0):
            ingresos[mon] += abs(valor)
        else:
            gastos[mon] += abs(valor)
            por_categoria[mon][cat] += abs(valor)

    out = [f"# Resumen {nombre_mes}", ""]
    out += [f"Generado el {dt.date.today():%d/%m/%Y} · {len(movs)} movimientos", ""]

    out += ["## Balance", "", "| Moneda | Ingresos | Gastos | Resultado |", "|---|---|---|---|"]
    for mon in sorted(set(ingresos) | set(gastos)) or ["ARS"]:
        i, g = ingresos[mon], gastos[mon]
        out.append(f"| {mon} | {plata(i, mon)} | {plata(g, mon)} | {plata(i - g, mon)} |")

    out += ["", "## Gastos por categoría", ""]
    if not por_categoria:
        out.append("Sin gastos cargados este mes.")
    for mon, cats in sorted(por_categoria.items()):
        total = sum(cats.values())
        out += [f"**{mon}**", "", "| Categoría | Monto | % |", "|---|---|---|"]
        for cat, v in sorted(cats.items(), key=lambda x: -x[1]):
            out.append(f"| {cat} | {plata(v, mon)} | {v / total:.0%} |")
        out.append("")

    hoy = dt.date.today()
    pendientes = [c for c in leer_csv(BASE / "Cobros_Clientes.csv") if c.get("Estado", "").lower() != "cobrado"]
    out += ["", "## Cobros pendientes de clientes", ""]
    if not pendientes:
        out.append("Nada pendiente.")
    else:
        out += ["| Cliente | Concepto | Monto | Vence | |", "|---|---|---|---|---|"]
        totales = defaultdict(float)
        for c in sorted(pendientes, key=lambda c: fecha(c.get("Fecha vencimiento", "")) or dt.date.max):
            mon = c.get("Moneda") or "ARS"
            v = monto(c.get("Monto", "0"))
            totales[mon] += v
            vence = fecha(c.get("Fecha vencimiento", ""))
            alerta = "VENCIDO" if vence and vence < hoy else ""
            out.append(f"| {c.get('Cliente', '')} | {c.get('Concepto', '')} | {plata(v, mon)} | "
                       f"{vence.strftime('%d/%m/%Y') if vence else '-'} | {alerta} |")
        out += ["", "Total a cobrar: " + " · ".join(plata(v, m) for m, v in sorted(totales.items()))]

    fijos = [g for g in leer_csv(BASE / "Gastos_Fijos.csv") if g.get("Activo", "si").lower() not in ("no", "n", "0")]
    out += ["", "## Gastos fijos del mes", ""]
    if not fijos:
        out.append("No hay gastos fijos cargados.")
    else:
        totales = defaultdict(float)
        for g in fijos:
            totales[g.get("Moneda") or "ARS"] += monto(g.get("Monto", "0"))
        out.append(f"{len(fijos)} fijos activos: " + " · ".join(plata(v, m) for m, v in sorted(totales.items())))

    return nombre_mes, "\n".join(out) + "\n"


def main():
    p = argparse.ArgumentParser(description="Resumen mensual de Finanzas/")
    p.add_argument("mes", nargs="?", help="AAAA-MM (por defecto, el mes actual)")
    args = p.parse_args()
    if args.mes:
        anio, mes = (int(x) for x in args.mes.split("-"))
    else:
        anio, mes = dt.date.today().year, dt.date.today().month

    nombre_mes, texto = armar(anio, mes)
    destino = BASE / "Resumenes" / f"{nombre_mes}.md"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(texto, encoding="utf-8")
    print(texto)
    print(f"Guardado en {destino.relative_to(BASE.parent)}")


if __name__ == "__main__":
    main()
