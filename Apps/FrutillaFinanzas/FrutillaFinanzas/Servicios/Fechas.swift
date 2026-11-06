import Foundation

/// Fechas en español rioplatense, con la semana arrancando el lunes.
enum Fechas {
    static let locale = Locale(identifier: "es_AR")

    static let calendario: Calendar = {
        var cal = Calendar(identifier: .gregorian)
        cal.locale = locale
        cal.firstWeekday = 2
        return cal
    }()

    private static func formateador(_ formato: String) -> DateFormatter {
        let f = DateFormatter()
        f.locale = locale
        f.calendar = calendario
        f.dateFormat = formato
        return f
    }

    private static let fMes = formateador("LLLL yyyy")
    private static let fDia = formateador("EEEE d 'de' MMMM")
    private static let fDiaAnio = formateador("EEEE d 'de' MMMM 'de' yyyy")
    private static let fCorta = formateador("d MMM")
    private static let fCortaAnio = formateador("d MMM yyyy")
    private static let fNumerica = formateador("dd/MM/yyyy")

    // MARK: Cálculos

    static func inicioDeDia(_ fecha: Date) -> Date {
        calendario.startOfDay(for: fecha)
    }

    static func inicioDeMes(_ fecha: Date) -> Date {
        let comps = calendario.dateComponents([.year, .month], from: fecha)
        return calendario.date(from: comps) ?? fecha
    }

    static func sumarMeses(_ meses: Int, a fecha: Date) -> Date {
        calendario.date(byAdding: .month, value: meses, to: fecha) ?? fecha
    }

    static func sumarDias(_ dias: Int, a fecha: Date) -> Date {
        calendario.date(byAdding: .day, value: dias, to: fecha) ?? fecha
    }

    /// Días entre hoy y la fecha (negativo si ya pasó).
    static func diasDesdeHoy(_ fecha: Date, hoy: Date = .now) -> Int {
        calendario.dateComponents([.day], from: inicioDeDia(hoy), to: inicioDeDia(fecha)).day ?? 0
    }

    static func esMismoMes(_ a: Date, _ b: Date) -> Bool {
        calendario.isDate(a, equalTo: b, toGranularity: .month)
    }

    // MARK: Textos

    /// "Noviembre 2026"
    static func nombreMes(_ fecha: Date) -> String {
        fMes.string(from: fecha).capitalizandoPrimera
    }

    /// "Hoy", "Ayer" o "Jueves 5 de noviembre".
    static func tituloDia(_ fecha: Date) -> String {
        let dias = diasDesdeHoy(fecha)
        if dias == 0 { return "Hoy" }
        if dias == -1 { return "Ayer" }
        let mismoAnio = calendario.isDate(fecha, equalTo: .now, toGranularity: .year)
        return (mismoAnio ? fDia : fDiaAnio).string(from: fecha).capitalizandoPrimera
    }

    /// "15 nov" (o "15 nov 2027" si es de otro año).
    static func corta(_ fecha: Date) -> String {
        let mismoAnio = calendario.isDate(fecha, equalTo: .now, toGranularity: .year)
        return (mismoAnio ? fCorta : fCortaAnio).string(from: fecha).replacingOccurrences(of: ".", with: "")
    }

    /// "05/11/2026"
    static func numerica(_ fecha: Date) -> String {
        fNumerica.string(from: fecha)
    }

    /// "Hoy", "Mañana", "En 3 días", "Ayer", "Hace 4 días".
    static func relativa(_ fecha: Date) -> String {
        let dias = diasDesdeHoy(fecha)
        switch dias {
        case 0: return "Hoy"
        case 1: return "Mañana"
        case -1: return "Ayer"
        case let d where d > 1: return "En \(d) días"
        default: return "Hace \(-dias) días"
        }
    }
}

extension String {
    var capitalizandoPrimera: String {
        guard let primera = first else { return self }
        return primera.uppercased() + dropFirst()
    }

    var recortado: String {
        trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
