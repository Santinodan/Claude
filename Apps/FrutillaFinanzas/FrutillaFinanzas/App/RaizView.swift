import SwiftUI
import SwiftData

enum Pestana: Hashable {
    case inicio, movimientos, cuentas, cuotas
}

struct RaizView: View {
    @Environment(\.modelContext) private var context
    @Environment(\.scenePhase) private var fase
    @AppStorage("moneda") private var monedaRaw = Moneda.ARS.rawValue
    @State private var pestana: Pestana = .inicio

    var body: some View {
        TabView(selection: $pestana) {
            InicioView()
                .tabItem { Label("Inicio", systemImage: "house.fill") }
                .tag(Pestana.inicio)

            MovimientosView()
                .tabItem { Label("Movimientos", systemImage: "list.bullet.rectangle.portrait") }
                .tag(Pestana.movimientos)

            CuentasView()
                .tabItem { Label("Cuentas", systemImage: "wallet.pass") }
                .tag(Pestana.cuentas)

            CuotasView()
                .tabItem { Label("Cuotas", systemImage: "calendar.badge.clock") }
                .tag(Pestana.cuotas)
        }
        .tint(Marca.frutilla)
        .environment(\.moneda, Moneda(rawValue: monedaRaw) ?? .ARS)
        .environment(\.locale, Fechas.locale)
        .environment(\.calendar, Fechas.calendario)
        .onAppear {
            DatosIniciales.crearSiHaceFalta(context)
        }
        .onChange(of: fase) { _, nueva in
            if nueva == .active { Recordatorios.reprogramar(context) }
        }
    }
}

#Preview {
    RaizView()
        .modelContainer(for: [Cuenta.self, Movimiento.self, Categoria.self, Cuota.self, Suscripcion.self], inMemory: true)
}
