import Foundation
import SwiftData

@Model
final class Suscripcion {
    var nombre: String = ""
    var emoji: String = "📺"
    var monto: Double = 0
    var frecuenciaRaw: String = Frecuencia.mensual.rawValue
    var proximoCobro: Date = Date()
    var diasAviso: Int = 1
    var activa: Bool = true
    var creada: Date = Date()

    var cuenta: Cuenta?
    var categoria: Categoria?

    /// Si se borra la suscripción, los cobros registrados quedan como movimientos.
    @Relationship(deleteRule: .nullify, inverse: \Movimiento.suscripcion)
    var cobros: [Movimiento] = []

    init(nombre: String, emoji: String, monto: Double, frecuencia: Frecuencia = .mensual, proximoCobro: Date, diasAviso: Int = 1, activa: Bool = true) {
        self.nombre = nombre
        self.emoji = emoji
        self.monto = monto
        self.frecuenciaRaw = frecuencia.rawValue
        self.proximoCobro = proximoCobro
        self.diasAviso = diasAviso
        self.activa = activa
        self.creada = Date()
    }

    var frecuencia: Frecuencia {
        get { Frecuencia(rawValue: frecuenciaRaw) ?? .mensual }
        set { frecuenciaRaw = newValue.rawValue }
    }

    /// Cuánto pesa por mes, para el resumen de compromisos.
    var montoMensual: Double { activa ? monto * frecuencia.factorMensual : 0 }

    var vencida: Bool { activa && Fechas.diasDesdeHoy(proximoCobro) < 0 }
}
