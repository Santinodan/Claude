import Foundation

/// Cálculos de resumen que usan Inicio, Cuentas y Cuotas.
enum Finanzas {

    struct Patrimonio {
        /// Suma de las cuentas en positivo.
        var tenes: Double
        /// Tarjetas (y cuentas en rojo) más las cuotas que faltan pagar.
        var debes: Double
        var neto: Double { tenes - debes }
    }

    struct Compromisos {
        var cuotas: Double
        var suscripciones: Double
        var total: Double { cuotas + suscripciones }
    }

    struct Vencimiento: Identifiable {
        let id: String
        let emoji: String
        let nombre: String
        let detalle: String
        let fecha: Date
        let monto: Double
        var vencido: Bool { Fechas.diasDesdeHoy(fecha) < 0 }
    }

    static func patrimonio(cuentas: [Cuenta], cuotas: [Cuota]) -> Patrimonio {
        var tenes = 0.0
        var debes = 0.0
        for cuenta in cuentas {
            let saldo = cuenta.saldo
            if saldo >= 0 { tenes += saldo } else { debes += -saldo }
        }
        debes += cuotas.reduce(0) { $0 + $1.pendiente }
        return Patrimonio(tenes: tenes, debes: debes)
    }

    static func compromisos(cuotas: [Cuota], suscripciones: [Suscripcion]) -> Compromisos {
        Compromisos(
            cuotas: cuotas.filter { !$0.terminada }.reduce(0) { $0 + $1.valorCuota },
            suscripciones: suscripciones.reduce(0) { $0 + $1.montoMensual }
        )
    }

    /// Cuotas y suscripciones que vencen en los próximos `dias` días (incluye las vencidas).
    static func vencimientos(cuotas: [Cuota], suscripciones: [Suscripcion], dias: Int = 30) -> [Vencimiento] {
        var lista: [Vencimiento] = []
        for cuota in cuotas {
            guard let fecha = cuota.proximoVencimiento, Fechas.diasDesdeHoy(fecha) <= dias else { continue }
            lista.append(Vencimiento(
                id: "c-\(cuota.persistentModelID.hashValue)",
                emoji: cuota.tipo.emoji,
                nombre: cuota.nombre,
                detalle: "Cuota \(cuota.pagadas + 1) de \(cuota.cantidad)",
                fecha: fecha,
                monto: cuota.valorCuota
            ))
        }
        for sub in suscripciones where sub.activa && Fechas.diasDesdeHoy(sub.proximoCobro) <= dias {
            lista.append(Vencimiento(
                id: "s-\(sub.persistentModelID.hashValue)",
                emoji: sub.emoji,
                nombre: sub.nombre,
                detalle: sub.frecuencia.nombre,
                fecha: sub.proximoCobro,
                monto: sub.monto
            ))
        }
        return lista.sorted { $0.fecha < $1.fecha }
    }
}
