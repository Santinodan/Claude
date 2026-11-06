import Foundation

// Enums que usan los modelos. En SwiftData se guardan como String (campo `...Raw`)
// para poder filtrarlos en consultas sin problemas.

enum TipoCuenta: String, CaseIterable, Identifiable, Codable {
    case efectivo
    case banco
    case tarjetaCredito
    case ahorro
    case billetera

    var id: String { rawValue }

    var nombre: String {
        switch self {
        case .efectivo: "Efectivo"
        case .banco: "Banco / Débito"
        case .tarjetaCredito: "Tarjeta de crédito"
        case .ahorro: "Ahorro"
        case .billetera: "Billetera virtual"
        }
    }

    var simbolo: String {
        switch self {
        case .efectivo: "banknote"
        case .banco: "building.columns"
        case .tarjetaCredito: "creditcard"
        case .ahorro: "dollarsign.circle"
        case .billetera: "iphone.gen3"
        }
    }
}

enum TipoMovimiento: String, CaseIterable, Identifiable, Codable {
    case gasto
    case ingreso
    case transferencia

    var id: String { rawValue }

    var nombre: String {
        switch self {
        case .gasto: "Gasto"
        case .ingreso: "Ingreso"
        case .transferencia: "Transferencia"
        }
    }
}

enum TipoCuota: String, CaseIterable, Identifiable, Codable {
    case compraEnCuotas
    case prestamoPersonal
    case hipotecario
    case otro

    var id: String { rawValue }

    var nombre: String {
        switch self {
        case .compraEnCuotas: "Compra en cuotas"
        case .prestamoPersonal: "Préstamo personal"
        case .hipotecario: "Crédito hipotecario"
        case .otro: "Otro"
        }
    }

    var emoji: String {
        switch self {
        case .compraEnCuotas: "🛍️"
        case .prestamoPersonal: "🏦"
        case .hipotecario: "🏠"
        case .otro: "📄"
        }
    }
}

enum Frecuencia: String, CaseIterable, Identifiable, Codable {
    case semanal
    case mensual
    case anual

    var id: String { rawValue }

    var nombre: String {
        switch self {
        case .semanal: "Semanal"
        case .mensual: "Mensual"
        case .anual: "Anual"
        }
    }

    var sufijo: String {
        switch self {
        case .semanal: "/sem"
        case .mensual: "/mes"
        case .anual: "/año"
        }
    }

    /// Cuánto pesa un cobro de esta frecuencia en un mes promedio.
    var factorMensual: Double {
        switch self {
        case .semanal: 52.0 / 12.0
        case .mensual: 1
        case .anual: 1.0 / 12.0
        }
    }

    func siguiente(a fecha: Date) -> Date {
        let cal = Fechas.calendario
        switch self {
        case .semanal: return cal.date(byAdding: .day, value: 7, to: fecha) ?? fecha
        case .mensual: return cal.date(byAdding: .month, value: 1, to: fecha) ?? fecha
        case .anual: return cal.date(byAdding: .year, value: 1, to: fecha) ?? fecha
        }
    }
}

enum Moneda: String, CaseIterable, Identifiable, Codable {
    case ARS, USD, EUR, UYU, CLP, MXN, COP, PEN, BRL

    var id: String { rawValue }

    var simbolo: String {
        switch self {
        case .ARS: "$"
        case .USD: "US$"
        case .EUR: "€"
        case .UYU: "$U"
        case .CLP: "$"
        case .MXN: "$"
        case .COP: "$"
        case .PEN: "S/"
        case .BRL: "R$"
        }
    }

    var nombre: String {
        switch self {
        case .ARS: "Peso argentino"
        case .USD: "Dólar estadounidense"
        case .EUR: "Euro"
        case .UYU: "Peso uruguayo"
        case .CLP: "Peso chileno"
        case .MXN: "Peso mexicano"
        case .COP: "Peso colombiano"
        case .PEN: "Sol peruano"
        case .BRL: "Real brasileño"
        }
    }

    var bandera: String {
        switch self {
        case .ARS: "🇦🇷"
        case .USD: "🇺🇸"
        case .EUR: "🇪🇺"
        case .UYU: "🇺🇾"
        case .CLP: "🇨🇱"
        case .MXN: "🇲🇽"
        case .COP: "🇨🇴"
        case .PEN: "🇵🇪"
        case .BRL: "🇧🇷"
        }
    }

    /// Formatea con el estilo es_AR: "$ 12.500" o "$ 12.500,50".
    func formatear(_ valor: Double, conSigno: Bool = false) -> String {
        Formato.dinero(valor, moneda: self, conSigno: conSigno)
    }
}
