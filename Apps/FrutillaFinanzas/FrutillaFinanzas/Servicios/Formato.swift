import Foundation

/// Formato de montos estilo es_AR, sin depender del idioma del teléfono:
/// miles con punto y decimales con coma ("$ 12.500" o "$ 12.500,50").
enum Formato {

    // MARK: Mostrar montos

    static func dinero(_ valor: Double, moneda: Moneda = .ARS, conSigno: Bool = false) -> String {
        let centavos = Int64((abs(valor) * 100).rounded())
        var signo = ""
        if centavos > 0 {
            if valor < 0 { signo = "-" } else if conSigno { signo = "+" }
        }
        return "\(signo)\(moneda.simbolo) \(numero(centavos: centavos))"
    }

    /// Número sin símbolo: "12.500" o "12.500,50". Se usa para precargar campos de monto.
    static func numero(_ valor: Double) -> String {
        numero(centavos: Int64((abs(valor) * 100).rounded()))
    }

    /// Número sin miles ni símbolo, con coma decimal: "12500,50". Ideal para CSV.
    static func numeroPlano(_ valor: Double) -> String {
        let centavos = Int64((abs(valor) * 100).rounded())
        let signo = valor < 0 && centavos > 0 ? "-" : ""
        let entero = centavos / 100
        let resto = centavos % 100
        return resto == 0 ? "\(signo)\(entero)" : "\(signo)\(entero),\(dosDigitos(resto))"
    }

    private static func numero(centavos: Int64) -> String {
        let entero = centavos / 100
        let resto = centavos % 100
        let base = agrupar(entero)
        return resto == 0 ? base : "\(base),\(dosDigitos(resto))"
    }

    private static func dosDigitos(_ n: Int64) -> String {
        n < 10 ? "0\(n)" : "\(n)"
    }

    static func agrupar(_ n: Int64) -> String {
        let digitos = Array(String(n))
        var resultado = ""
        for (i, c) in digitos.enumerated() {
            if i > 0 && (digitos.count - i) % 3 == 0 { resultado.append(".") }
            resultado.append(c)
        }
        return resultado
    }

    // MARK: Leer montos

    /// Acepta "12500", "12.500", "12.500,50", "$ 12.500,5" y también "12.5" (pegado).
    /// La coma siempre es decimal. Sin coma, un único punto seguido de 1 o 2 dígitos se toma como decimal;
    /// cualquier otro punto es separador de miles.
    static func parsear(_ texto: String) -> Double? {
        let limpio = texto.filter { esDigito($0) || $0 == "." || $0 == "," }
        guard limpio.contains(where: esDigito) else { return nil }

        var entero = ""
        var decimales = ""

        if let coma = limpio.lastIndex(of: ",") {
            entero = String(limpio[..<coma]).filter(esDigito)
            decimales = String(limpio[limpio.index(after: coma)...]).filter(esDigito)
        } else if let punto = limpio.lastIndex(of: "."),
                  limpio.filter({ $0 == "." }).count == 1,
                  limpio.distance(from: punto, to: limpio.endIndex) - 1 <= 2 {
            entero = String(limpio[..<punto]).filter(esDigito)
            decimales = String(limpio[limpio.index(after: punto)...])
        } else {
            entero = limpio.filter(esDigito)
        }

        decimales = String(decimales.prefix(2))
        let texto = (entero.isEmpty ? "0" : entero) + "." + (decimales.isEmpty ? "0" : decimales)
        guard let valor = Double(texto) else { return nil }
        return (valor * 100).rounded() / 100
    }

    /// Reformatea lo que se va tipeando en el campo de monto: agrega los puntos de miles
    /// y deja hasta 2 decimales después de la coma. Un punto tipeado al final se toma como coma decimal
    /// (en teclados con punto decimal). Los puntos de miles se recalculan siempre.
    static func formatearEntrada(_ texto: String) -> String {
        var t = texto.filter { esDigito($0) || $0 == "." || $0 == "," }
        if t.hasSuffix("."), !t.contains(",") {
            t.removeLast()
            t.append(",")
        }
        let tieneComa = t.contains(",")
        let partes = t.split(separator: ",", maxSplits: 1, omittingEmptySubsequences: false)
        var entero = String(partes.first ?? "").filter(esDigito)
        let decimales = partes.count > 1 ? String(String(partes[1]).filter(esDigito).prefix(2)) : ""

        while entero.count > 1 && entero.hasPrefix("0") { entero.removeFirst() }
        entero = String(entero.prefix(12))

        if entero.isEmpty {
            guard tieneComa else { return "" }
            entero = "0"
        }
        var resultado = agrupar(Int64(entero) ?? 0)
        if tieneComa { resultado += "," + decimales }
        return resultado
    }

    private static func esDigito(_ c: Character) -> Bool {
        c >= "0" && c <= "9"
    }
}
