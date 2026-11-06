import SwiftUI

struct MovimientoFila: View {
    let movimiento: Movimiento
    /// Si se muestra dentro de una cuenta, las transferencias entrantes van con "+".
    var cuentaContexto: Cuenta? = nil
    var mostrarFecha = false

    private var esTransferencia: Bool { movimiento.tipo == .transferencia }

    private var titulo: String {
        if esTransferencia { return "Transferencia" }
        return movimiento.categoria?.nombre ?? "Sin categoría"
    }

    private var emoji: String {
        if esTransferencia { return "🔁" }
        return movimiento.categoria?.emoji ?? "❔"
    }

    private var color: Color {
        if esTransferencia { return .blue }
        return movimiento.categoria?.color ?? .gray
    }

    private var subtitulo: String {
        var partes: [String] = []
        if !movimiento.nota.isEmpty { partes.append(movimiento.nota) }
        if esTransferencia {
            partes.append("\(movimiento.cuenta?.nombre ?? "?") → \(movimiento.cuentaDestino?.nombre ?? "?")")
        } else if let cuenta = movimiento.cuenta {
            partes.append(cuenta.nombre)
        }
        if mostrarFecha { partes.append(Fechas.corta(movimiento.fecha)) }
        return partes.joined(separator: " · ")
    }

    /// Monto con signo según el tipo y la cuenta desde la que se mira.
    private var montoConSigno: Double {
        switch movimiento.tipo {
        case .gasto: return -movimiento.monto
        case .ingreso: return movimiento.monto
        case .transferencia:
            guard let contexto = cuentaContexto else { return movimiento.monto }
            return movimiento.cuentaDestino == contexto ? movimiento.monto : -movimiento.monto
        }
    }

    private var colorMonto: Color {
        switch movimiento.tipo {
        case .gasto: return .primary
        case .ingreso: return Marca.hoja
        case .transferencia:
            if cuentaContexto != nil && montoConSigno > 0 { return Marca.hoja }
            return .secondary
        }
    }

    var body: some View {
        HStack(spacing: 12) {
            CirculoEmoji(emoji: emoji, color: color, tamano: 40)
            VStack(alignment: .leading, spacing: 2) {
                Text(titulo)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.primary)
                    .lineLimit(1)
                if !subtitulo.isEmpty {
                    Text(subtitulo)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }
            Spacer(minLength: 8)
            MontoTexto(valor: montoConSigno, conSigno: movimiento.tipo == .ingreso || (cuentaContexto != nil && montoConSigno > 0))
                .font(.monto(16, peso: .semibold))
                .foregroundStyle(colorMonto)
                .lineLimit(1)
        }
        .contentShape(Rectangle())
    }
}
