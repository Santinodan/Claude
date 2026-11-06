import Foundation
import SwiftData

@Model
final class Cuenta {
    var nombre: String = ""
    var tipoRaw: String = TipoCuenta.efectivo.rawValue
    /// En tarjetas de crédito se guarda en negativo (es deuda).
    var saldoInicial: Double = 0
    var colorHex: String = "#E32B4A"
    var orden: Int = 0
    var creada: Date = Date()

    /// Si se borra la cuenta, se borran sus movimientos.
    @Relationship(deleteRule: .cascade, inverse: \Movimiento.cuenta)
    var movimientos: [Movimiento] = []

    /// Transferencias que llegan a esta cuenta. También se borran con la cuenta.
    @Relationship(deleteRule: .cascade, inverse: \Movimiento.cuentaDestino)
    var transferenciasEntrantes: [Movimiento] = []

    @Relationship(deleteRule: .nullify, inverse: \Cuota.cuenta)
    var cuotas: [Cuota] = []

    @Relationship(deleteRule: .nullify, inverse: \Suscripcion.cuenta)
    var suscripciones: [Suscripcion] = []

    init(nombre: String, tipo: TipoCuenta = .efectivo, saldoInicial: Double = 0, colorHex: String = "#E32B4A", orden: Int = 0) {
        self.nombre = nombre
        self.tipoRaw = tipo.rawValue
        self.saldoInicial = saldoInicial
        self.colorHex = colorHex
        self.orden = orden
        self.creada = Date()
    }

    var tipo: TipoCuenta {
        get { TipoCuenta(rawValue: tipoRaw) ?? .efectivo }
        set { tipoRaw = newValue.rawValue }
    }

    var esTarjeta: Bool { tipo == .tarjetaCredito }

    /// Saldo actual: saldo inicial más todo lo que entró y menos todo lo que salió.
    var saldo: Double {
        var total = saldoInicial
        for m in movimientos {
            switch m.tipo {
            case .ingreso: total += m.monto
            case .gasto, .transferencia: total -= m.monto
            }
        }
        for m in transferenciasEntrantes where m.tipo == .transferencia {
            total += m.monto
        }
        return total
    }

    /// Lo que se debe (tarjetas o cuentas en rojo).
    var deuda: Double { max(0, -saldo) }

    /// Movimientos propios más transferencias entrantes, del más nuevo al más viejo.
    var historial: [Movimiento] {
        let entrantes = transferenciasEntrantes.filter { $0.tipo == .transferencia }
        return (movimientos + entrantes).sorted { $0.fecha > $1.fecha }
    }
}
