import Foundation
import SwiftData
import UserNotifications

/// Notificaciones locales para cuotas y suscripciones. Cada vez que algo cambia
/// se borran todas las pendientes y se vuelven a programar.
enum Recordatorios {
    static let claveActivos = "recordatoriosActivos"
    /// Minutos desde la medianoche (600 = 10:00).
    static let claveHora = "horaAviso"

    private struct Pedido: Sendable {
        let id: String
        let titulo: String
        let cuerpo: String
        let fecha: Date
    }

    static var activos: Bool {
        UserDefaults.standard.object(forKey: claveActivos) as? Bool ?? true
    }

    static var minutosAviso: Int {
        UserDefaults.standard.object(forKey: claveHora) as? Int ?? 600
    }

    static func reprogramar(_ context: ModelContext) {
        let pedidos = activos ? armarPedidos(context) : []
        Task {
            let centro = UNUserNotificationCenter.current()
            centro.removeAllPendingNotificationRequests()
            guard !pedidos.isEmpty else { return }

            let ajustes = await centro.notificationSettings()
            if ajustes.authorizationStatus == .notDetermined {
                let permitido = (try? await centro.requestAuthorization(options: [.alert, .sound, .badge])) ?? false
                guard permitido else { return }
            } else if ajustes.authorizationStatus == .denied {
                return
            }

            // iOS permite hasta 64 pendientes por app.
            for pedido in pedidos.prefix(60) {
                let contenido = UNMutableNotificationContent()
                contenido.title = pedido.titulo
                contenido.body = pedido.cuerpo
                contenido.sound = .default
                let comps = Fechas.calendario.dateComponents([.year, .month, .day, .hour, .minute], from: pedido.fecha)
                let disparador = UNCalendarNotificationTrigger(dateMatching: comps, repeats: false)
                try? await centro.add(UNNotificationRequest(identifier: pedido.id, content: contenido, trigger: disparador))
            }
        }
    }

    private static func armarPedidos(_ context: ModelContext) -> [Pedido] {
        let moneda = Moneda(rawValue: UserDefaults.standard.string(forKey: "moneda") ?? "") ?? .ARS
        let cuotas = (try? context.fetch(FetchDescriptor<Cuota>())) ?? []
        let suscripciones = (try? context.fetch(FetchDescriptor<Suscripcion>())) ?? []
        let ahora = Date()
        var pedidos: [Pedido] = []

        for cuota in cuotas where cuota.avisar {
            guard let vence = cuota.proximoVencimiento else { continue }
            let monto = moneda.formatear(cuota.valorCuota)
            let detalle = "\(cuota.nombre) · cuota \(cuota.pagadas + 1) de \(cuota.cantidad) · \(monto)"
            // Un día antes y, si eso ya pasó, el mismo día.
            if let fecha = fechaAviso(vence, diasAntes: 1), fecha > ahora {
                pedidos.append(Pedido(id: "cuota-\(cuota.persistentModelID.hashValue)", titulo: "Mañana vence una cuota 🍓", cuerpo: "\(detalle). Tocá para registrar el pago.", fecha: fecha))
            } else if let fecha = fechaAviso(vence, diasAntes: 0), fecha > ahora {
                pedidos.append(Pedido(id: "cuota-\(cuota.persistentModelID.hashValue)", titulo: "Hoy vence una cuota 🍓", cuerpo: "\(detalle). Acordate de pagarla.", fecha: fecha))
            }
        }

        for sub in suscripciones where sub.activa {
            guard let fecha = fechaAviso(sub.proximoCobro, diasAntes: sub.diasAviso), fecha > ahora else { continue }
            let monto = moneda.formatear(sub.monto)
            let cuando: String
            switch sub.diasAviso {
            case 0: cuando = "hoy"
            case 1: cuando = "mañana"
            default: cuando = "en \(sub.diasAviso) días"
            }
            pedidos.append(Pedido(
                id: "sub-\(sub.persistentModelID.hashValue)",
                titulo: "\(sub.emoji) \(sub.nombre)",
                cuerpo: "Te cobra \(monto) \(cuando). Tenelo en cuenta.",
                fecha: fecha
            ))
        }
        return pedidos.sorted { $0.fecha < $1.fecha }
    }

    private static func fechaAviso(_ vencimiento: Date, diasAntes: Int) -> Date? {
        let dia = Fechas.sumarDias(-diasAntes, a: Fechas.inicioDeDia(vencimiento))
        return Fechas.calendario.date(byAdding: .minute, value: minutosAviso, to: dia)
    }
}
