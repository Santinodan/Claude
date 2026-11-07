# Cómo cargar las finanzas del mes

Guía para Snati y para Claude. Si arrancás una sesión nueva, leé esto primero.

## La idea en una línea

Snati manda capturas de lo que gasta, cobra y ahorra. Claude lo pasa a un CSV, arma el Excel del mes
con la plantilla de siempre y actualiza el dashboard. Al final del mes Snati sube el Excel a su Drive
personal.

## Dónde vive cada cosa

| Qué | Dónde |
|---|---|
| Plantilla vacía del Excel | `Finanzas/_Herramientas/Plantilla_Finanzas.xlsx` (copia de "Plantilla - Finanzas personales" del Drive) |
| Script que arma el Excel | `Finanzas/_Herramientas/armar_planilla.py` |
| Carpeta de Drive (cuenta personal) | https://drive.google.com/drive/folders/1spneYExxL9MmlLOMD8zEre9nmkXQ3SEI |
| Dashboard para ver el mes en Claude | Artifact privado "Finanzas Noviembre 2026" (Claude lo actualiza en cada carga) |

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
4. **Agregar las filas al CSV del mes** (separador `;`, coma decimal):

   ```
   Hoja;Fecha;Detalle;Categoria;Pesos;USD;Metodo;Cuota;Cantidad;PrecioEntrada;PrecioHoy
   Gasto;06/11/2026;Movistar;Personal;10500;6,34;Mercado Pago;;;;
   Ingreso;02/11/2026;Rendimientos Mercado Pago;;2,61;0;;;;;
   Inversion;07/11/2026;USDT;Earn Binance;;;;;455,58;1;1
   ```

5. **Armar el Excel:**

   ```bash
   python3 Finanzas/_Herramientas/armar_planilla.py 2026-11 movimientos_2026-11.csv
   ```

   Sale `Noviembre 2026 - Finanzas personales.xlsx`, con el mes puesto, los gastos, ingresos e
   inversiones cargados, y el gráfico de torta actualizado.
6. **Revisar** recalculando con LibreOffice (`soffice --headless --convert-to xlsx`) que los totales
   den igual que la suma del CSV.
7. **Mandarle el Excel a Snati** y actualizar el dashboard (subir los CSV nuevos y apuntar cada fuente
   al archivo nuevo).

## Criterios de carga

- **Categorías:** Salud, Gusto, Suscripciones, Educación, Comidas y bebidas, Regalo, Personal, Transporte.
  Si aparece una nueva, el script la agrega sola a la tabla y al gráfico.
  - Gimnasio → Salud. Ropa de marca para Snati → Gusto. Regalos (Tizi, su familia) → Regalo.
  - Celular (Movistar), Wi-Fi de vuelo → Personal. Uber, DiDi, taxis → Transporte.
- **Cuotas:** columna Cuota como `3/6`. Si una cuota se debita en partes, va como un solo gasto
  (cada parte se pasa a USD con su propio día).
- **No es ingreso:** pasar plata de Binance a Mercado Pago (aparece como "Transferencia recibida").
- **Ahorro:** lo que hay en Binance (USDT en Earn) va como `Inversion`, con precio 1.
- **Fecha del Excel:** dd/mm. **Detalle:** corto y claro; si fue en otra moneda, poner la moneda y el país.

## Al cerrar el mes

1. Snati sube el Excel a la carpeta de Drive desde su cuenta personal.
   Para reemplazar una versión sin cambiar el link: clic derecho → Administrar versiones → Subir nueva versión.
2. Para el mes siguiente se arranca un CSV nuevo y el script arma un Excel nuevo desde la plantilla.

## Privacidad

- Los montos reales **no se suben a este repo** hasta que Snati confirme que el repo es privado.
  Hasta entonces, los CSV con datos viven en la sesión y en el Excel/Drive de Snati.
- El dashboard es privado: solo lo ve la cuenta de Claude de Snati, salvo que lo comparta desde el botón Compartir.
