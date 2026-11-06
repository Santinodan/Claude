import Foundation
import SwiftData

/// Compras en cuotas y créditos.
@Model
final class Cuota {
    var nombre: String = ""
    var tipoRaw: String = TipoCuota.compraEnCuotas.rawValue
    var valorCuota: Double = 0
    var cantidad: Int = 1
    var pagadas: Int = 0
    var primerVencimiento: Date = Date()
    var avisar: Bool = true
    var creada: Date = Date()

    /// Cuenta desde la que se paga.
    var cuenta: Cuenta?

    /// Si se borra la cuota, los pagos registrados quedan como movimientos.
    @Relationship(deleteRule: .nullify, inverse: \Movimiento.cuota)
    var pagos: [Movimiento] = []

    init(nombre: String, tipo: TipoCuota = .compraEnCuotas, valorCuota: Double, cantidad: Int, pagadas: Int = 0, primerVencimiento: Date, avisar: Bool = true) {
        self.nombre = nombre
        self.tipoRaw = tipo.rawValue
        self.valorCuota = valorCuota
        self.cantidad = cantidad
        self.pagadas = pagadas
        self.primerVencimiento = primerVencimiento
        self.avisar = avisar
        self.creada = Date()
    }

    var tipo: TipoCuota {
        get { TipoCuota(rawValue: tipoRaw) ?? .otro }
        set { tipoRaw = newValue.rawValue }
    }

    var restantes: Int { max(0, cantidad - pagadas) }
    var terminada: Bool { pagadas >= cantidad }
    var total: Double { valorCuota * Double(cantidad) }
    var pendiente: Double { valorCuota * Double(restantes) }
    var progreso: Double { cantidad > 0 ? min(1, Double(pagadas) / Double(cantidad)) : 0 }

    /// Vencimiento de la próxima cuota a pagar (nil si ya se pagó todo).
    var proximoVencimiento: Date? {
        terminada ? nil : Fechas.sumarMeses(pagadas, a: primerVencimiento)
    }

    var vencida: Bool {
        guard let fecha = proximoVencimiento else { return false }
        return Fechas.diasDesdeHoy(fecha) < 0
    }

    var pagosOrdenados: [Movimiento] {
        pagos.sorted { $0.fecha > $1.fecha }
    }
}
