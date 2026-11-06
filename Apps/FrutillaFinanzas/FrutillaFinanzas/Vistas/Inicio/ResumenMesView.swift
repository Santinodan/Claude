import SwiftUI
import SwiftData
import Charts

/// Todo lo que depende del mes elegido en Inicio.
struct ResumenMesView: View {
    @Environment(\.moneda) private var moneda
    @Query private var movimientos: [Movimiento]

    let compromisos: Finanzas.Compromisos
    let vencimientos: [Finanzas.Vencimiento]

    @State private var editando: Movimiento?

    init(mes: Date, compromisos: Finanzas.Compromisos, vencimientos: [Finanzas.Vencimiento]) {
        let inicio = Fechas.inicioDeMes(mes)
        let fin = Fechas.sumarMeses(1, a: inicio)
        _movimientos = Query(
            filter: #Predicate<Movimiento> { $0.fecha >= inicio && $0.fecha < fin },
            sort: \Movimiento.fecha,
            order: .reverse
        )
        self.compromisos = compromisos
        self.vencimientos = vencimientos
    }

    private var gastos: [Movimiento] { movimientos.filter { $0.tipo == .gasto } }
    private var totalIngresos: Double { movimientos.filter { $0.tipo == .ingreso }.reduce(0) { $0 + $1.monto } }
    private var totalGastos: Double { gastos.reduce(0) { $0 + $1.monto } }

    var body: some View {
        VStack(spacing: 16) {
            TarjetaIngresosGastos(ingresos: totalIngresos, gastos: totalGastos)
            TarjetaCompromisos(compromisos: compromisos, ingresos: totalIngresos)
            TarjetaDona(gastos: gastos)
            TarjetaVencimientos(vencimientos: vencimientos)
            tarjetaMayoresGastos
        }
        .sheet(item: $editando) { movimiento in
            MovimientoFormView(movimiento: movimiento)
        }
    }

    private var tarjetaMayoresGastos: some View {
        VStack(alignment: .leading, spacing: 12) {
            TituloTarjeta(titulo: "Gastos más grandes", simbolo: "flame")
            let top = gastos.sorted { $0.monto > $1.monto }.prefix(5)
            if top.isEmpty {
                Text("Todavía no cargaste gastos este mes.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(Array(top)) { movimiento in
                    Button {
                        editando = movimiento
                    } label: {
                        MovimientoFila(movimiento: movimiento, mostrarFecha: true)
                    }
                    .buttonStyle(.plain)
                    if movimiento.id != top.last?.id { Divider() }
                }
            }
        }
        .tarjeta()
    }
}

// MARK: Ingresos vs gastos

struct TarjetaIngresosGastos: View {
    @Environment(\.moneda) private var moneda
    let ingresos: Double
    let gastos: Double

    private var balance: Double { ingresos - gastos }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            TituloTarjeta(titulo: "Ingresos vs gastos", simbolo: "chart.bar.xaxis")

            HStack {
                dato(titulo: "Ingresos", valor: ingresos, color: Marca.hoja)
                Spacer()
                dato(titulo: "Gastos", valor: gastos, color: Marca.frutilla)
                    .multilineTextAlignment(.trailing)
            }

            barra

            Divider()

            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Balance del mes")
                        .font(.subheadline.weight(.semibold))
                    Text(mensaje)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                MontoTexto(valor: balance, conSigno: true)
                    .font(.monto(22))
                    .foregroundStyle(balance >= 0 ? Marca.hoja : Marca.frutilla)
            }
        }
        .tarjeta()
    }

    private var mensaje: String {
        if ingresos == 0 && gastos == 0 { return "Sin movimientos este mes" }
        if ingresos == 0 { return "Todavía no cargaste ingresos" }
        if balance >= 0 {
            let porcentaje = Int((balance / ingresos * 100).rounded())
            return "Te queda el \(porcentaje)% de lo que ingresó"
        }
        return "Gastaste \(moneda.formatear(-balance)) más de lo que ingresó"
    }

    private func dato(titulo: String, valor: Double, color: Color) -> some View {
        VStack(alignment: titulo == "Gastos" ? .trailing : .leading, spacing: 2) {
            Text(titulo)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
            MontoTexto(valor: valor)
                .font(.monto(20))
                .foregroundStyle(color)
                .minimumScaleFactor(0.6)
                .lineLimit(1)
        }
    }

    private var barra: some View {
        GeometryReader { geo in
            let total = ingresos + gastos
            let anchoIngresos = total > 0 ? geo.size.width * ingresos / total : geo.size.width / 2
            HStack(spacing: 4) {
                Capsule()
                    .fill(total > 0 ? AnyShapeStyle(Marca.hoja.gradient) : AnyShapeStyle(Color.secondary.opacity(0.2)))
                    .frame(width: max(0, anchoIngresos - 2))
                Capsule()
                    .fill(total > 0 ? AnyShapeStyle(Marca.frutilla.gradient) : AnyShapeStyle(Color.secondary.opacity(0.2)))
            }
        }
        .frame(height: 12)
        .animation(.spring(duration: 0.4), value: ingresos)
        .animation(.spring(duration: 0.4), value: gastos)
    }
}

// MARK: Compromisos fijos

struct TarjetaCompromisos: View {
    let compromisos: Finanzas.Compromisos
    let ingresos: Double

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            TituloTarjeta(titulo: "Compromisos fijos por mes", simbolo: "pin")
            HStack {
                fila("Cuotas y créditos", compromisos.cuotas)
                Spacer()
                fila("Suscripciones", compromisos.suscripciones)
            }
            Divider()
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Total por mes").font(.subheadline.weight(.semibold))
                    if ingresos > 0 && compromisos.total > 0 {
                        Text("Es el \(Int((compromisos.total / ingresos * 100).rounded()))% de tus ingresos del mes")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer()
                MontoTexto(valor: compromisos.total)
                    .font(.monto(22))
            }
        }
        .tarjeta()
    }

    private func fila(_ titulo: String, _ valor: Double) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(titulo).font(.caption.weight(.semibold)).foregroundStyle(.secondary)
            MontoTexto(valor: valor).font(.monto(17, peso: .semibold))
        }
    }
}

// MARK: Dona por categoría

struct TarjetaDona: View {
    let gastos: [Movimiento]

    struct Porcion: Identifiable {
        let id: String
        let nombre: String
        let emoji: String
        let color: Color
        var total: Double
    }

    private var porciones: [Porcion] {
        var acumulado: [String: Porcion] = [:]
        for m in gastos {
            let clave = m.categoria.map { "\($0.persistentModelID.hashValue)" } ?? "sin"
            if acumulado[clave] == nil {
                acumulado[clave] = Porcion(
                    id: clave,
                    nombre: m.categoria?.nombre ?? "Sin categoría",
                    emoji: m.categoria?.emoji ?? "❔",
                    color: m.categoria?.color ?? .gray,
                    total: 0
                )
            }
            acumulado[clave]?.total += m.monto
        }
        return acumulado.values.sorted { $0.total > $1.total }
    }

    var body: some View {
        let datos = porciones
        let total = datos.reduce(0) { $0 + $1.total }

        VStack(alignment: .leading, spacing: 14) {
            TituloTarjeta(titulo: "Gastos por categoría", simbolo: "chart.pie")

            if datos.isEmpty {
                Text("Cuando cargues gastos, acá vas a ver en qué se te va la plata.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } else {
                Chart(datos) { porcion in
                    SectorMark(
                        angle: .value("Monto", porcion.total),
                        innerRadius: .ratio(0.62),
                        angularInset: 1.5
                    )
                    .cornerRadius(5)
                    .foregroundStyle(porcion.color)
                }
                .chartLegend(.hidden)
                .frame(height: 210)
                .overlay {
                    VStack(spacing: 2) {
                        Text("Gastos")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.secondary)
                        MontoTexto(valor: total)
                            .font(.monto(20))
                            .minimumScaleFactor(0.5)
                            .lineLimit(1)
                            .frame(maxWidth: 120)
                    }
                }

                VStack(spacing: 10) {
                    ForEach(datos) { porcion in
                        HStack(spacing: 10) {
                            Circle().fill(porcion.color).frame(width: 10, height: 10)
                            Text("\(porcion.emoji) \(porcion.nombre)")
                                .font(.subheadline)
                                .lineLimit(1)
                            Spacer()
                            Text(porcentaje(porcion.total, de: total))
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(.secondary)
                                .monospacedDigit()
                            MontoTexto(valor: porcion.total)
                                .font(.subheadline.weight(.semibold))
                                .frame(minWidth: 90, alignment: .trailing)
                        }
                    }
                }
            }
        }
        .tarjeta()
    }

    private func porcentaje(_ valor: Double, de total: Double) -> String {
        guard total > 0 else { return "0%" }
        let p = valor / total * 100
        return p < 1 && p > 0 ? "<1%" : "\(Int(p.rounded()))%"
    }
}

// MARK: Próximos vencimientos

struct TarjetaVencimientos: View {
    let vencimientos: [Finanzas.Vencimiento]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            TituloTarjeta(titulo: "Próximos vencimientos", simbolo: "calendar")
            if vencimientos.isEmpty {
                Text("No tenés vencimientos en los próximos 30 días.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(vencimientos) { v in
                    HStack(spacing: 12) {
                        CirculoEmoji(emoji: v.emoji, color: v.vencido ? Marca.frutilla : Marca.rosa, tamano: 38)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(v.nombre).font(.subheadline.weight(.semibold)).lineLimit(1)
                            Text("\(v.detalle) · \(Fechas.corta(v.fecha))")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        VStack(alignment: .trailing, spacing: 2) {
                            MontoTexto(valor: v.monto).font(.subheadline.weight(.semibold))
                            Text(v.vencido ? "Vencida" : Fechas.relativa(v.fecha))
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(color(v))
                        }
                    }
                    if v.id != vencimientos.last?.id { Divider() }
                }
            }
        }
        .tarjeta()
    }

    private func color(_ v: Finanzas.Vencimiento) -> Color {
        if v.vencido { return Marca.frutilla }
        return Fechas.diasDesdeHoy(v.fecha) <= 3 ? .orange : .secondary
    }
}
