import Foundation
import SwiftData

/// Categorías y cuenta que se crean la primera vez que se abre la app.
enum DatosIniciales {
    static let clave = "datosInicialesCreados.v1"

    static let categoriasGasto: [(nombre: String, emoji: String, color: String)] = [
        ("Supermercado", "🛒", "#26A69A"),
        ("Comida", "🍔", "#FF9800"),
        ("Transporte", "🚌", "#2196F3"),
        ("Hogar", "🏠", "#8D6E63"),
        ("Servicios", "💡", "#FFC107"),
        ("Salud", "💊", "#EC407A"),
        ("Salidas", "🎉", "#AB47BC"),
        ("Ropa", "👕", "#5C6BC0"),
        ("Educación", "📚", "#00897B"),
        ("Suscripciones", "📺", "#7E57C2"),
        ("Cuotas", "💳", "#E32B4A"),
        ("Mascotas", "🐶", "#A1887F"),
        ("Regalos", "🎁", "#F06292"),
        ("Otros", "📦", "#90A4AE"),
    ]

    static let categoriasIngreso: [(nombre: String, emoji: String, color: String)] = [
        ("Sueldo", "💼", "#2FA85A"),
        ("Freelance", "💻", "#26A69A"),
        ("Ventas", "🏷️", "#66BB6A"),
        ("Inversiones", "📈", "#43A047"),
        ("Regalos", "🎁", "#81C784"),
        ("Otros ingresos", "💰", "#9CCC65"),
    ]

    static func crearSiHaceFalta(_ context: ModelContext) {
        guard !UserDefaults.standard.bool(forKey: clave) else { return }
        crear(context)
        UserDefaults.standard.set(true, forKey: clave)
    }

    static func crear(_ context: ModelContext) {
        let categorias = (try? context.fetchCount(FetchDescriptor<Categoria>())) ?? 0
        if categorias == 0 {
            for (i, c) in categoriasGasto.enumerated() {
                context.insert(Categoria(nombre: c.nombre, emoji: c.emoji, colorHex: c.color, esIngreso: false, orden: i))
            }
            for (i, c) in categoriasIngreso.enumerated() {
                context.insert(Categoria(nombre: c.nombre, emoji: c.emoji, colorHex: c.color, esIngreso: true, orden: i))
            }
        }
        let cuentas = (try? context.fetchCount(FetchDescriptor<Cuenta>())) ?? 0
        if cuentas == 0 {
            context.insert(Cuenta(nombre: "Efectivo", tipo: .efectivo, colorHex: "#2FA85A", orden: 0))
        }
        try? context.save()
    }

    /// Busca una categoría de gasto por nombre (ej. "Cuotas"); si el usuario la borró, la vuelve a crear.
    static func categoria(_ nombre: String, en context: ModelContext) -> Categoria {
        let descriptor = FetchDescriptor<Categoria>(predicate: #Predicate { $0.nombre == nombre && $0.esIngreso == false })
        if let existente = try? context.fetch(descriptor).first {
            return existente
        }
        let base = categoriasGasto.first { $0.nombre == nombre }
        let total = (try? context.fetchCount(FetchDescriptor<Categoria>())) ?? 0
        let nueva = Categoria(nombre: nombre, emoji: base?.emoji ?? "🏷️", colorHex: base?.color ?? "#90A4AE", esIngreso: false, orden: total)
        context.insert(nueva)
        return nueva
    }

    /// Primera cuenta que no sea tarjeta, o la primera que haya. Si no hay ninguna, crea "Efectivo".
    static func cuentaPorDefecto(en context: ModelContext) -> Cuenta {
        let cuentas = (try? context.fetch(FetchDescriptor<Cuenta>(sortBy: [SortDescriptor(\.orden)]))) ?? []
        if let cuenta = cuentas.first(where: { !$0.esTarjeta }) ?? cuentas.first {
            return cuenta
        }
        let efectivo = Cuenta(nombre: "Efectivo", tipo: .efectivo, colorHex: "#2FA85A")
        context.insert(efectivo)
        return efectivo
    }
}
