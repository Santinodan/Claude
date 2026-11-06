import SwiftUI
import SwiftData

@main
struct FrutillaFinanzasApp: App {
    var body: some Scene {
        WindowGroup {
            RaizView()
        }
        .modelContainer(for: [
            Cuenta.self,
            Movimiento.self,
            Categoria.self,
            Cuota.self,
            Suscripcion.self,
        ])
    }
}
