import Foundation
import SwiftData

/// Operaciones que tocan varios modelos a la vez.
enum Acciones {

    /// Registra el gasto de la próxima cuota en su cuenta (categoría Cuotas) y suma una cuota pagada.
    @discardableResult
    static func pagarCuota(_ cuota: Cuota, fecha: Date = .now, en context: ModelContext) -> Movimiento? {
        guard !cuota.terminada else { return nil }
        let numero = cuota.pagadas + 1
        let movimiento = Movimiento(
            monto: cuota.valorCuota,
            tipo: .gasto,
            fecha: fecha,
            nota: "\(cuota.nombre) · cuota \(numero) de \(cuota.cantidad)"
        )
        context.insert(movimiento)
        movimiento.cuenta = cuota.cuenta ?? DatosIniciales.cuentaPorDefecto(en: context)
        movimiento.categoria = DatosIniciales.categoria("Cuotas", en: context)
        movimiento.cuota = cuota
        cuota.pagadas = numero
        guardar(context)
        return movimiento
    }

    /// Crea el gasto de la suscripción y corre la fecha al próximo cobro.
    @discardableResult
    static func registrarCobro(_ suscripcion: Suscripcion, fecha: Date = .now, en context: ModelContext) -> Movimiento {
        let movimiento = Movimiento(monto: suscripcion.monto, tipo: .gasto, fecha: fecha, nota: suscripcion.nombre)
        context.insert(movimiento)
        movimiento.cuenta = suscripcion.cuenta ?? DatosIniciales.cuentaPorDefecto(en: context)
        movimiento.categoria = suscripcion.categoria ?? DatosIniciales.categoria("Suscripciones", en: context)
        movimiento.suscripcion = suscripcion
        suscripcion.proximoCobro = suscripcion.frecuencia.siguiente(a: suscripcion.proximoCobro)
        guardar(context)
        return movimiento
    }

    /// Borra un movimiento. Si era el pago de una cuota, descuenta esa cuota pagada.
    static func borrar(_ movimiento: Movimiento, en context: ModelContext) {
        if let cuota = movimiento.cuota, cuota.pagadas > 0 {
            cuota.pagadas -= 1
        }
        context.delete(movimiento)
        guardar(context)
    }

    /// Borra todo y vuelve a crear las categorías y la cuenta Efectivo.
    static func borrarTodo(en context: ModelContext) {
        try? context.delete(model: Movimiento.self)
        try? context.delete(model: Cuota.self)
        try? context.delete(model: Suscripcion.self)
        try? context.delete(model: Cuenta.self)
        try? context.delete(model: Categoria.self)
        try? context.save()
        DatosIniciales.crear(context)
        Recordatorios.reprogramar(context)
    }

    static func guardar(_ context: ModelContext) {
        try? context.save()
        Recordatorios.reprogramar(context)
    }
}
