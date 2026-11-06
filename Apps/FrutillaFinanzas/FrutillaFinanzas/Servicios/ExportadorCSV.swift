import Foundation
import CoreTransferable
import UniformTypeIdentifiers

/// Arma el CSV de movimientos. Usa ";" como separador y coma decimal,
/// que es lo que espera Excel / Numbers configurado en español.
enum ExportadorCSV {

    enum Periodo: String, CaseIterable, Identifiable {
        case todo = "Todo"
        case esteMes = "Este mes"
        case mesAnterior = "Mes anterior"
        case esteAnio = "Este año"

        var id: String { rawValue }

        func incluye(_ fecha: Date, hoy: Date = .now) -> Bool {
            let cal = Fechas.calendario
            switch self {
            case .todo: return true
            case .esteMes: return cal.isDate(fecha, equalTo: hoy, toGranularity: .month)
            case .mesAnterior: return cal.isDate(fecha, equalTo: Fechas.sumarMeses(-1, a: hoy), toGranularity: .month)
            case .esteAnio: return cal.isDate(fecha, equalTo: hoy, toGranularity: .year)
            }
        }
    }

    static func generar(_ movimientos: [Movimiento], moneda: Moneda) -> String {
        var lineas = ["Fecha;Tipo;Monto;Moneda;Categoría;Cuenta;Cuenta destino;Nota"]
        for m in movimientos.sorted(by: { $0.fecha < $1.fecha }) {
            let monto = m.tipo == .gasto ? -m.monto : m.monto
            let campos = [
                Fechas.numerica(m.fecha),
                m.tipo.nombre,
                Formato.numeroPlano(monto),
                moneda.rawValue,
                m.categoria?.nombre ?? "",
                m.cuenta?.nombre ?? "",
                m.cuentaDestino?.nombre ?? "",
                m.nota,
            ]
            lineas.append(campos.map(escapar).joined(separator: ";"))
        }
        return lineas.joined(separator: "\r\n") + "\r\n"
    }

    private static func escapar(_ campo: String) -> String {
        guard campo.contains(where: { $0 == ";" || $0 == "\"" || $0 == "\n" || $0 == "\r" }) else { return campo }
        return "\"" + campo.replacingOccurrences(of: "\"", with: "\"\"") + "\""
    }
}

/// Archivo para compartir con ShareLink.
struct ArchivoCSV: Transferable {
    let nombre: String
    let contenido: String

    static var transferRepresentation: some TransferRepresentation {
        FileRepresentation(exportedContentType: .commaSeparatedText) { archivo in
            let url = FileManager.default.temporaryDirectory.appendingPathComponent(archivo.nombre)
            // BOM para que Excel lea bien las tildes.
            try ("\u{FEFF}" + archivo.contenido).write(to: url, atomically: true, encoding: .utf8)
            return SentTransferredFile(url)
        }
    }
}
