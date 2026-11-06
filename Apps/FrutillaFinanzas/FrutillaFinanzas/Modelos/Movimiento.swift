import Foundation
import SwiftData

@Model
final class Movimiento {
    var monto: Double = 0
    var tipoRaw: String = TipoMovimiento.gasto.rawValue
    var fecha: Date = Date()
    var nota: String = ""
    var creado: Date = Date()

    /// Cuenta de origen (o la cuenta del gasto / ingreso).
    var cuenta: Cuenta?
    /// Solo en transferencias.
    var cuentaDestino: Cuenta?
    var categoria: Categoria?
    /// Cuota o suscripción que generó este movimiento (si la hay).
    var cuota: Cuota?
    var suscripcion: Suscripcion?

    init(monto: Double = 0, tipo: TipoMovimiento = .gasto, fecha: Date = .now, nota: String = "") {
        self.monto = monto
        self.tipoRaw = tipo.rawValue
        self.fecha = fecha
        self.nota = nota
        self.creado = Date()
    }

    var tipo: TipoMovimiento {
        get { TipoMovimiento(rawValue: tipoRaw) ?? .gasto }
        set { tipoRaw = newValue.rawValue }
    }

    /// Para totales del mes: ingresos suman, gastos restan, transferencias no cuentan.
    var impactoNeto: Double {
        switch tipo {
        case .ingreso: monto
        case .gasto: -monto
        case .transferencia: 0
        }
    }
}
