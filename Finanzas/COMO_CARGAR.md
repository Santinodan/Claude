# Cómo cargar las finanzas del mes

Guía técnica paso a paso. Si arrancás una sesión nueva, leé primero `PRINCIPIOS_FINANZAS.md`.

## Regla de oro

**El dashboard es la presentación gráfica del Excel.** Los dos salen de los mismos datos
(`Finanzas/Datos/`) y tienen que mostrar siempre lo mismo. Cada cambio se hace en el CSV del mes,
y de ahí se regeneran el Excel y el dashboard. Todo se commitea y se pushea (pedido explícito de Snati).

## La idea en una línea

Snati manda capturas de lo que gasta, cobra y ahorra. Claude lo pasa a un CSV, arma el Excel del mes
con la plantilla de siempre y actualiza el dashboard. Al final del mes Snati sube el Excel a su Drive
personal.

## Dónde vive cada cosa

| Qué | Dónde |
|---|---|
| **Datos de cada mes (la fuente de todo)** | `Finanzas/Datos/AAAA-MM.csv` (formato de carga, ver abajo) |
| Excel de cada mes (armado desde los datos) | `Finanzas/Planillas/<Mes>_2026_Finanzas_personales.xlsx` |
| Planillas originales bajadas del Drive (respaldo, no tocar) | `Finanzas/Planillas/Originales_Drive/` |
| Página del dashboard (copia del código) | `Finanzas/Dashboard/index.html` |
| Plantilla vacía del Excel | `Finanzas/_Herramientas/Plantilla_Finanzas.xlsx` (copia de "Plantilla - Finanzas personales" del Drive) |
| Script que arma el Excel | `Finanzas/_Herramientas/armar_planilla.py` |
| Carpeta de Drive (cuenta personal) | https://drive.google.com/drive/folders/1spneYExxL9MmlLOMD8zEre9nmkXQ3SEI |
| Dashboard para ver todo en Claude | Artifact privado "Finanzas personales": https://claude.ai/artifact/XpnyCv4DunkSYbZzL8dSfW (todos los meses, con selector) |
| Script que arma los datos del dashboard | `Finanzas/_Herramientas/exportar_dashboard.py` |

**Regla importante:** Claude no crea ni copia archivos en el Drive conectado (cuenta mediapeakbiz).
Todo se arma local y Snati lo sube desde su cuenta personal (dangelosantino29).

## Paso a paso (cada vez que llegan capturas)

1. **Leer la captura.** Anotar fecha, detalle, monto, moneda y medio de pago (Mercado Pago, Binance, Lemon, Efectivo).
2. **Preguntar lo que no se entiende.** Comercios raros (ej. "Alipay*OtherRetail601") se preguntan: qué fue y para quién.
3. **Pasar a dólares con la cotización del día del gasto, no la de hoy:**
   - Gasto en pesos: USD = pesos ÷ dólar cripto venta de ese día.
     Historial: `https://api.argentinadatos.com/v1/cotizaciones/dolares/cripto`
   - Gasto en otra moneda (CNY, HKD, BRL…): moneda → USD con el tipo de cambio oficial de ese día
     (`https://api.frankfurter.dev/v1/AAAA-MM-DD?base=USD`; para fin de semana
     `https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@AAAA-MM-DD/v1/currencies/usd.json`),
     y después pesos = USD × dólar cripto de ese día.
4. **Agregar las filas a `Finanzas/Datos/AAAA-MM.csv`** (separador `;`, coma decimal):

   ```
   Hoja;Fecha;Detalle;Categoria;Pesos;USD;Metodo;Cuota;Cantidad;PrecioEntrada;PrecioHoy
   Gasto;06/11/2026;Movistar;Personal;10500;6,34;Mercado Pago;;;;
   Ingreso;02/11/2026;Rendimientos Mercado Pago;;2,61;0;;;;;
   Inversion;07/11/2026;USDT;Earn Binance;;;;;455,58;1;1
   ```

5. **Armar el Excel:**

   ```bash
   python3 Finanzas/_Herramientas/armar_planilla.py 2026-11 Finanzas/Datos/2026-11.csv -o Finanzas/Planillas/Noviembre_2026_Finanzas_personales.xlsx
   ```

   Sale el Excel del mes en `Finanzas/Planillas/`, con el mes puesto, los gastos, ingresos e
   inversiones cargados, y el gráfico de torta actualizado.
6. **Revisar** recalculando con LibreOffice (`soffice --headless --convert-to xlsx`) que los totales
   den igual que la suma del CSV.
7. **Mandarle el Excel a Snati.**
8. **Actualizar el dashboard** con todos los meses juntos:

   ```bash
   python3 Finanzas/_Herramientas/exportar_dashboard.py salida/ Finanzas/Datos/2026-*.csv
   ```

   Sale `gastos.csv`, `ingresos.csv` y `ahorro.csv` (con columna `mes`). Se suben al dashboard como
   archivos y cada fuente (`gastos`, `ingresos`, `ahorro`) pasa a apuntar al archivo nuevo. El selector
   de mes muestra solo los meses que haya; por defecto abre el último.
9. **Commit y push** de `Finanzas/Datos/`, `Finanzas/Planillas/` y, si cambió, `Finanzas/Dashboard/index.html`.

## Criterios de carga

- **Categorías:** Salud, Gusto, Suscripciones, Educación, Comidas y bebidas, Regalo, Personal, Transporte.
  Si aparece una nueva, el script la agrega sola a la tabla y al gráfico.
  - Gimnasio → Salud. Ropa de marca para Snati → Gusto. Regalos (Tizi, su familia) → Regalo.
  - Celular (Movistar) → Suscripciones (como en los meses viejos). Wi-Fi de vuelo → Personal.
- **Ingresos de SOUL:** el cierre de mes de Gian se carga en la fecha en que entra la plata, con las cajas en el detalle. Uber, DiDi, taxis → Transporte.
- **Cuotas:** columna Cuota como `3/6`. Si una cuota se debita en partes, va como un solo gasto
  (cada parte se pasa a USD con su propio día).
- **No es ingreso:** pasar plata de Binance a Mercado Pago (aparece como "Transferencia recibida").
- **Ingresos del mes (desde noviembre 2026):** una línea "Saldo Binance + gastado en el mes"
  (USD = saldo actual de Binance + USD gastados en el mes; pesos = gastado en pesos + saldo × cripto del día)
  y otra con los dólares en efectivo. **Se recalcula cada vez que cambian los gastos o el saldo.**
  Así el "Restante" del Excel da exactamente lo que Snati tiene (Binance + efectivo).
- **Plata como un solo pozo:** no hace falta separar por cuenta (Binance, Mercado Pago). Un ingreso que
  entra a Binance se carga como ingreso del mes y listo; después Snati la va pasando a Mercado Pago.
- **Ahorro:** Binance (USDT en Earn) y dólares en efectivo van como `Ahorro` (precio 1): salen en el
  dashboard pero no en Inversiones del Excel, para no contarlos dos veces en el patrimonio.
  `Inversion` queda para inversiones reales (Cedears, acciones).
- **Fecha del Excel:** dd/mm. **Detalle:** corto y claro; si fue en otra moneda, poner la moneda y el país.

## Al cerrar el mes

1. Snati sube el Excel a la carpeta de Drive desde su cuenta personal.
   Para reemplazar una versión sin cambiar el link: clic derecho → Administrar versiones → Subir nueva versión.
2. Para el mes siguiente se arranca un CSV nuevo y el script arma un Excel nuevo desde la plantilla.

## Privacidad

- Snati pidió que los datos y planillas estén en este repo. Cualquiera con acceso al repo los ve:
  mantenerlo **privado** en GitHub.
- El dashboard es privado: solo lo ve la cuenta de Claude de Snati, salvo que lo comparta desde el botón Compartir.
