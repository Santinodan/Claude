import Foundation
import SwiftData

@Model
final class Categoria {
    var nombre: String = ""
    var emoji: String = "🏷️"
    var colorHex: String = "#9E9E9E"
    var esIngreso: Bool = false
    var orden: Int = 0

    /// Si se borra la categoría, los movimientos quedan (sin categoría).
    @Relationship(deleteRule: .nullify, inverse: \Movimiento.categoria)
    var movimientos: [Movimiento] = []

    @Relationship(deleteRule: .nullify, inverse: \Suscripcion.categoria)
    var suscripciones: [Suscripcion] = []

    init(nombre: String, emoji: String, colorHex: String, esIngreso: Bool = false, orden: Int = 0) {
        self.nombre = nombre
        self.emoji = emoji
        self.colorHex = colorHex
        self.esIngreso = esIngreso
        self.orden = orden
    }
}
