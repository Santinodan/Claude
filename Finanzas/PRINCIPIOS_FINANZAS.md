# Principios de finanzas de Snati

**Leer esto primero.** Es el punto de partida para cualquier chat que siga con las finanzas de Snati:
qué se hace, con qué reglas, dónde está cada cosa y en qué estado quedó. El paso a paso técnico
está en `COMO_CARGAR.md`.

---

## 1. Qué hacemos

Snati manda capturas (Mercado Pago, tarjeta Binance, saldos) y documentos (el cierre de mes de Gian).
Claude los convierte en datos, arma el **Excel del mes** con la plantilla de siempre y actualiza el
**dashboard**. Todo queda en este repo. Al cerrar el mes, Snati sube el Excel a su Drive personal.

## 2. Reglas de oro

1. **Una sola fuente:** `Finanzas/Datos/AAAA-MM.csv`. De ahí salen el Excel y el dashboard.
   Nunca se edita el Excel ni el dashboard a mano: se cambia el CSV y se regeneran los dos.
2. **El dashboard es la vista gráfica del Excel.** Tienen que mostrar exactamente los mismos números.
3. **Todo se guarda en GitHub** (pedido de Snati): datos, Excel, código del dashboard y estos documentos.
   Commit y push al terminar cada carga.
4. **No usar la memoria de Claude** para nada de finanzas. Lo que haga falta recordar va en este repo.
5. **No crear ni copiar archivos en el Drive conectado** (cuenta mediapeakbiz). El Excel se arma acá y
   Snati lo sube desde su cuenta personal.
6. **Dólar del día del movimiento, nunca el de hoy** (ver 4).
7. **Preguntar antes de inventar:** si un comercio, una categoría o una fecha no está clara, se pregunta.
8. No borrar ni pisar material aprobado: los originales del Drive viven en `Planillas/Originales_Drive/`.

## 3. Dónde está cada cosa

| Qué | Dónde |
|---|---|
| Datos de cada mes (fuente de todo) | `Finanzas/Datos/AAAA-MM.csv` |
| Excel de cada mes | `Finanzas/Planillas/<Mes>_2026_Finanzas_personales.xlsx` |
| Originales del Drive (respaldo, no tocar) | `Finanzas/Planillas/Originales_Drive/` |
| Plantilla vacía del Excel | `Finanzas/_Herramientas/Plantilla_Finanzas.xlsx` |
| Arma el Excel de un mes | `Finanzas/_Herramientas/armar_planilla.py` |
| Arma los datos del dashboard | `Finanzas/_Herramientas/exportar_dashboard.py` |
| Código del dashboard | `Finanzas/Dashboard/index.html` |
| Consejos de ahorro (los escribe Claude) | `Finanzas/Datos/consejos.csv` |
| Dashboard (artifact privado, tipo Dashboard) | https://claude.ai/artifact/XpnyCv4DunkSYbZzL8dSfW — "Finanzas personales" |
| Carpeta de Drive de Snati (cuenta personal dangelosantino29) | https://drive.google.com/drive/folders/1spneYExxL9MmlLOMD8zEre9nmkXQ3SEI |
| Paso a paso técnico | `Finanzas/COMO_CARGAR.md` |

**Rama:** todo está en la rama principal del repo `Santinodan/Claude` (el pull request #1 se unió el 11/11/2026). Un chat nuevo lo encuentra directo; cada chat trabaja en su propia rama y después se une con un pull request.

## 4. Cómo se carga cada cosa

### Formato del CSV (separador `;`, coma decimal, sin `;` dentro de los textos)

```
Hoja;Fecha;Detalle;Categoria;Pesos;USD;Metodo;Cuota;Cantidad;PrecioEntrada;PrecioHoy
Gasto;06/11/2026;Cuota gym Oxigeno;Salud;55000;33,23;Mercado Pago;;;;
Ingreso;08/11/2026;SOUL - comisiones cierre de noviembre (...);;1160693,82;702;;;;;
Ahorro;08/11/2026;USD;Efectivo (dolares);;;;;1000;1;1
```

- **Hoja:** `Gasto`, `Ingreso`, `Ahorro` (saldos de Binance y efectivo: van al dashboard, no a Inversiones
  del Excel) o `Inversion` (inversiones reales: Cedears, acciones).

### Cotizaciones

- **Pesos → USD:** dólar cripto **venta** del día del movimiento. Si la captura de Binance muestra cuántos USDT se descontaron, se usa ese monto exacto.
  Historial: `https://api.argentinadatos.com/v1/cotizaciones/dolares/cripto` · En vivo: `https://dolarapi.com/v1/dolares/cripto`.
- **Otra moneda (CNY, HKD, BRL…):** primero a USD con el tipo de cambio oficial de ese día
  (`https://api.frankfurter.dev/v1/AAAA-MM-DD?base=USD`; fin de semana:
  `https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@AAAA-MM-DD/v1/currencies/usd.json`),
  después a pesos con el dólar cripto de ese día.
- **Meses viejos (junio a agosto):** se respeta el USD que anotó Snati.

### Categorías

Salud, Gusto, Suscripciones, Educación, Comidas y bebidas, Regalo, Personal, Transporte, Equipo de trabajo.

- **Equipo de trabajo:** cosas que le sirven a Snati para trabajar mejor (accesorios y adaptador de la DJI, barra de luz para el monitor). Se trata como inversión, igual que Educación: no se recorta, se mide qué rinde.

- Gimnasio, boxeo → Salud · Ropa de marca, perfumes, juegos → Gusto · Regalos (Tizi, su familia) → Regalo
- Celular (Movistar), Spotify, YouTube, Google One, Adobe, Apple, Xbox Game Pass (se cobra el 12 de cada mes) → Suscripciones · LUTs → Gusto · Uber, DiDi, Cabify → Transporte
- Súper chino del barrio (Xiangmei Gao) → Comidas y bebidas · Peluquería (Federico Carranza) → Personal · EBANX = Uber → Transporte · Accesorios DJI → Equipo de trabajo
- Pauta de Meta, testeos, ebooks para testear → Educación · Wi-Fi de vuelo, peluquería, cuidado personal → Personal

### Ingresos

- **Plata como un solo pozo:** no se separa por cuenta. Lo que entra a Binance es ingreso del mes; después
  Snati la pasa a Mercado Pago.
- **Transferencias enviadas grandes a personas desconocidas suelen ser compra de USDT en Binance (P2P): no son gasto.** Preguntar si no está claro.
- **Transferencias recibidas en Mercado Pago = retiros de Binance (P2P), no ingreso.** Excepción: las de Mariana Calabrese sí son ingreso. Las de su papá (D'Angelo Claudio Javier) son regalo.
- **Resumen de Mercado Pago (PDF):** sirve para cargar un mes entero; los rendimientos se suman en una sola línea de ingreso.
- **Fuente principal: comisiones de SOUL.** Gian manda un documento de cierre cada mes con lo que cobra
  Snati. Se carga en la fecha en que **entra la plata** (entró el 8/11 → noviembre).
  En el detalle se pone de qué cajas sale. Snati lo llama por el mes en que cobra: el pago del 8/11 es el "cierre de noviembre".
- **Desde noviembre 2026, el ingreso del mes incluye:** una línea "Saldo Binance + gastado en el mes"
  (lo que había al empezar), los dólares en efectivo y los ingresos nuevos. Si después llega un saldo de
  Binance que ya incluye un ingreso nuevo, el saldo inicial es: saldo actual + gastado − ingresos nuevos.

### Cuotas y casos especiales

- Cuota como `3/6`. Una cuota debitada en partes es un solo gasto (cada parte al cripto de su día).
- Detalle corto; si fue en otra moneda, poner moneda y país.

## 5. El ciclo de cada carga

1. Leer capturas → anotar fecha, detalle, monto, moneda, medio de pago.
2. Preguntar lo que no se entiende.
3. Convertir con la cotización del día y agregar filas a `Datos/AAAA-MM.csv`.
4. `armar_planilla.py` → Excel del mes en `Planillas/`. Revisar totales con LibreOffice.
5. `exportar_dashboard.py` con todos los meses → subir los CSV al dashboard (asset) → apuntar cada fuente
   (`gastos`, `ingresos`, `ahorro`) al archivo nuevo → borrar el asset viejo.
6. Mandarle el Excel a Snati.
7. Commit y push.

## 5b. Consejos para ahorrar (los escribe Claude)

- Viven en `Finanzas/Datos/consejos.csv` (`id,mes,orden,titulo,detalle,ahorro_usd_mes`), con consejos para
  cada mes y para `todo` (todos los meses juntos). El dashboard los muestra en "Consejos para ahorrar".
- **En cada carga se revisan y reescriben** con los números nuevos: qué se repite (Uber, salidas con Tizi),
  compras de impulso grandes, suscripciones, y cuánto apartar del cobro de SOUL (meta: 30%).
- Cada número que aparece en un consejo sale de los datos; `ahorro_usd_mes` es una estimación.
- Tono: directo, sin retar, con una acción concreta. Las inversiones del negocio (pauta, testeos) no se
  tratan como gasto a recortar: se sugiere medir su retorno.
- Después de reescribirlos: subir `consejos.csv` al dashboard y apuntar la fuente `consejos` al archivo nuevo.

## 6. Estado al 8 de noviembre de 2026

| Mes | Gastado | USD | Ingresos USD | Nota |
|---|---|---|---|---|
| Junio | $931.440 | 622 | 677 | Importado del Drive |
| Julio | $924.830 | 617 | 680 | Importado del Drive |
| Agosto | $284.050 | 182 | 210 | Importado del Drive |
| Septiembre | $198.607 | 125 | — | Importado; solo hasta el 11/9 |
| Octubre | $611.752 | 376 | 745 | Dato histórico (no se suma a lo actual). Mercado Pago (resumen PDF) + tarjeta Binance (12 al 29/10, parte del viaje a China). Ingresos: monitor, regalo de papá, Mariana Calabrese |
| Noviembre (al 11) | $437.450 | 266 | 2.378 | En curso; patrimonio US$ 2.112 |

**Preguntas pendientes para Snati:**
- "Error de Pago" de junio ($40.900, mismo monto que el jogging) y "Aduana" de agosto ($7.000): sin categoría.
  ¿El error de pago se devolvió?
- "Uber vuelta madero" de junio está en Comidas y bebidas: ¿pasarlo a Transporte?
- Octubre: cerrado con lo que hay (solo falta confirmar si la tarjeta Binance tuvo movimientos antes del 12/10). Aclarado: Gumroad = LUTs (Gusto); Microsoft Store = Xbox Game Pass mensual; KLATCH no se recuerda; Ctrip = SIM del viaje; OtherRetail914 y 9142 no se recuerdan; los Alipay chicos fueron comida. Mercado Pago ya aclarado: Franco Pennella ($548.000) fue pase a Binance (no es gasto); Alejandra Matilla ($32.900) no se recuerda.
- El saldo de Binance + Mercado Pago al 11/11 (US$ 1.112,44) es estimado (saldo informado menos gastos): confirmar con captura.

- El cierre de Gian dice US$ 702,12; se cargó US$ 702 (lo que entró). Confirmar.

## 7. Privacidad

- El repo `Santinodan/Claude` **es público** (verificado el 8/11/2026). Snati dijo que no hay problema,
  pero conviene recordárselo si se suben cosas más sensibles.
- Los documentos de cierre de Gian dicen "personal y confidencial" e incluyen números del negocio de SOUL:
  **no subir el documento completo al repo sin confirmación de Snati.** Se carga solo lo que cobra Snati.
- El dashboard es privado: solo lo ve la cuenta de Claude de Snati, salvo que lo comparta.
