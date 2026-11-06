# Traspaso — Frutilla Finanzas

Contexto para seguir el proyecto en otra sesión de Claude Code (por ejemplo, en VS Code en la Mac).

## Qué es

App nativa de iOS para registrar gastos personales, inspirada en "Sandía Finanzas" pero con marca propia
(no copiar nombre, ícono ni textos de Sandía).

- SwiftUI + SwiftData, iOS 17+, solo iPhone, Swift 5 (language mode 5.0).
- Sin servidor, sin login, sin dependencias externas. Swift Charts + UserNotifications.
- Bundle ID: `com.soul.frutillafinanzas`.
- Textos en español rioplatense. Montos es_AR: `$ 12.500` / `$ 12.500,50`.
- Colores: frutilla `#E32B4A`, rosa `#FF7A8A`, verde hoja `#2FA85A` (ingresos). Tarjetas con radio 22pt.

## Estado actual

- Todo lo pedido en el brief está implementado (ver lista abajo).
- **Compila y pasan los 10 tests** en simulador de iPhone (GitHub Actions, macos-15, Xcode 16).
- **Nunca se vio en pantalla**: falta revisar diseño en modo claro/oscuro en un iPhone o simulador real.
- **Falta instalarla en el iPhone de Snati** (próximo paso, ver abajo).

## Cómo instalarla en el iPhone (próximo paso)

Requisitos que hace Snati a mano: Xcode instalado, Apple ID agregado en Xcode (Settings → Accounts),
iPhone por cable con "Confiar" y Modo de desarrollador activado.

```bash
cd Apps/FrutillaFinanzas
./generar_proyecto.sh            # instala XcodeGen con brew si falta y genera el .xcodeproj
open FrutillaFinanzas.xcodeproj  # Signing & Capabilities → Team → elegir el Apple ID → Run en el iPhone
```

O por terminal (con el Team ID del Apple ID):

```bash
xcodebuild -project FrutillaFinanzas.xcodeproj -scheme FrutillaFinanzas \
  -destination 'platform=iOS,name=<nombre del iPhone>' \
  -allowProvisioningUpdates DEVELOPMENT_TEAM=<TEAM_ID> build
# instalar: xcrun devicectl device install app --device <id> <ruta al .app en DerivedData>
```

- Con Apple ID gratis la app dura 7 días; se reinstala igual.
- Si el Bundle ID no está disponible, cambiarlo en `project.yml` (ej. `com.snati.frutillafinanzas`) y regenerar.
- Primera vez en el iPhone: Ajustes → General → VPN y gestión de dispositivos → Confiar.
- Si se regenera el proyecto con XcodeGen, el Team elegido en Xcode se pierde. Para fijarlo, poner
  `DEVELOPMENT_TEAM: <TEAM_ID>` en `project.yml` (settings → base).

## Reglas del proyecto

- **No editar el `.xcodeproj` a mano**: se genera con XcodeGen desde `project.yml`.
- Nombres de archivo sin tildes. Commits en español.
- Cada cambio en `Apps/FrutillaFinanzas/**` dispara `.github/workflows/frutilla-ios.yml`
  (compila + tests en simulador). Gasta minutos de macOS de GitHub.

## Qué hay implementado

**Modelos (SwiftData)** — `FrutillaFinanzas/Modelos/`
- `Cuenta`: nombre, tipo (efectivo, banco/débito, tarjeta de crédito, ahorro, billetera virtual), saldo inicial
  (en tarjetas se guarda negativo = deuda), color, orden. Saldo calculado con movimientos + transferencias entrantes.
- `Movimiento`: monto, tipo (gasto/ingreso/transferencia), fecha, nota, cuenta, cuentaDestino, categoría,
  cuota y suscripción opcionales.
- `Categoria`: nombre, emoji, color, esIngreso, orden.
- `Cuota`: nombre, tipo, valor de cada cuota, cantidad, pagadas, primer vencimiento, cuenta, avisar.
- `Suscripcion`: nombre, emoji, monto, frecuencia, próximo cobro, días de aviso, activa, cuenta, categoría.
- Enums guardados como String (`tipoRaw`, `frecuenciaRaw`) para poder filtrarlos.

**Reglas de borrado**
- Cuenta → borra sus movimientos y las transferencias que recibió (cascade).
- Categoría, cuota o suscripción → los movimientos quedan (nullify).
- Borrar el pago de una cuota descuenta una cuota pagada (`Acciones.borrar`).

**Datos iniciales** — `Servicios/DatosIniciales.swift`
- 14 categorías de gasto, 6 de ingreso y la cuenta "Efectivo" al primer arranque (flag en UserDefaults).

**Pantallas** — `FrutillaFinanzas/Vistas/`
- TabView con 4 pestañas y botón flotante "+" (`Diseno/Componentes.swift`, `.botonAgregar()`).
- Inicio: tarjeta degradé con patrimonio neto / Tenés / Debés, selector de mes, ingresos vs gastos con barra y
  balance, compromisos fijos, dona por categoría (Swift Charts), vencimientos 30 días, top 5 gastos, engranaje → Ajustes.
- Movimientos: agrupados por día con neto diario, chips Todos/Gastos/Ingresos/Transferencias, buscador,
  borrar deslizando, tocar para editar.
- Cuentas: saldo total, lista reordenable, detalle con botones Ingreso/Gasto/Transferir, historial
  (transferencias entrantes con +), editar y eliminar.
- Cuotas: selector Cuotas y créditos / Suscripciones, resumen de compromisos mensuales.
  Cuotas con barra de progreso, "3 de 12", próximo vencimiento, "Pagar cuota" (gasto con categoría Cuotas),
  detalle con lista de pagos (deslizar para anular). Suscripciones con sugerencias rápidas
  (Netflix, Spotify, YouTube Premium, Disney+, iCloud, Gimnasio, Internet, Celular), "Registrar cobro"
  (crea el gasto y avanza la fecha) y marca de vencida.
- Formulario de movimiento: segmentado Gasto/Ingreso/Transferencia, monto grande con teclado abierto,
  grilla de categorías con emoji, cuenta, fecha, nota.
- Formulario de cuota: carga por valor de cada cuota o total, atajos 1, 3, 6, 9, 12, 18, 24, 36.
- Ajustes: moneda (ARS por defecto, USD, EUR, UYU, CLP, MXN, COP, PEN, BRL), categorías editables
  (emoji, nombre, color, reordenar, borrar), recordatorios on/off + hora, exportar CSV, borrar todos los datos.

**Servicios** — `FrutillaFinanzas/Servicios/`
- `Formato.swift`: formato y parseo es_AR propio (no depende del idioma del teléfono).
  Acepta "12500", "12.500", "12.500,50"; formatea mientras se tipea.
- `Recordatorios.swift`: notificaciones locales (cuota: día antes; suscripción: N días antes) a la hora elegida.
  Se reprograman todas al volver a la app y después de cada cambio.
- `ExportadorCSV.swift`: separador ";", coma decimal, BOM UTF-8, períodos Todo / Este mes / Mes anterior / Este año,
  compartido con ShareLink.

**Ícono** — `Recursos/Assets.xcassets/AppIcon.appiconset/AppIcon.png` (1024x1024, RGB, sin transparencia).
Se regenera con `python3 Herramientas/generar_icono.py <salida.png>` (Pillow).

**Tests** — `FrutillaFinanzasTests/`: formato de montos, saldos con transferencias, deuda de tarjeta,
reglas de borrado, pagar cuota, registrar cobro, datos iniciales.

## Pendientes / ideas

- Ver la app en un iPhone real y ajustar diseño (claro/oscuro, tamaños, textos que se corten).
- El brief original se cortó en "exportar los movimientos a CSV con…": se resolvió con ShareLink + selector de período.
  Confirmar con Snati si quería algo más ahí.
- El nombre "Frutilla Finanzas" probablemente se corte debajo del ícono en la pantalla de inicio.
- Opcional: soporte iPad, Face ID para abrir la app, widgets, TestFlight (requiere cuenta de Apple Developer paga).
