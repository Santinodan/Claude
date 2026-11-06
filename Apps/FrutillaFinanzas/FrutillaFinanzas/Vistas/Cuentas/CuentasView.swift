import SwiftUI
import SwiftData

struct CuentasView: View {
    @Environment(\.modelContext) private var context
    @Query(sort: \Cuenta.orden) private var cuentas: [Cuenta]
    @Query private var cuotas: [Cuota]
    @State private var nuevaCuenta = false

    private var saldoTotal: Double { cuentas.reduce(0) { $0 + $1.saldo } }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    tarjetaTotal
                        .listRowInsets(EdgeInsets())
                        .listRowBackground(Color.clear)
                }

                Section("Mis cuentas") {
                    if cuentas.isEmpty {
                        Text("No tenés cuentas. Tocá + arriba para crear una.")
                            .foregroundStyle(.secondary)
                    }
                    ForEach(cuentas) { cuenta in
                        NavigationLink(value: cuenta) {
                            CuentaFila(cuenta: cuenta)
                        }
                    }
                    .onMove(perform: mover)
                }
            }
            .listStyle(.insetGrouped)
            .contentMargins(.bottom, 90, for: .scrollContent)
            .navigationTitle("Cuentas")
            .navigationDestination(for: Cuenta.self) { cuenta in
                CuentaDetalleView(cuenta: cuenta)
            }
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    if cuentas.count > 1 { EditButton() }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        nuevaCuenta = true
                    } label: {
                        Image(systemName: "plus.circle.fill")
                    }
                    .accessibilityLabel("Nueva cuenta")
                }
            }
            .sheet(isPresented: $nuevaCuenta) {
                CuentaFormView()
            }
        }
        .botonAgregar()
    }

    private var tarjetaTotal: some View {
        let resumen = Finanzas.patrimonio(cuentas: cuentas, cuotas: [])
        return VStack(alignment: .leading, spacing: 10) {
            Text("Saldo total")
                .font(.subheadline.weight(.semibold))
                .opacity(0.9)
            MontoTexto(valor: saldoTotal)
                .font(.monto(36))
                .minimumScaleFactor(0.5)
                .lineLimit(1)
            HStack(spacing: 16) {
                Label {
                    MontoTexto(valor: resumen.tenes)
                } icon: {
                    Image(systemName: "arrow.up.right")
                }
                Label {
                    MontoTexto(valor: resumen.debes)
                } icon: {
                    Image(systemName: "creditcard")
                }
            }
            .font(.footnote.weight(.semibold))
            .opacity(0.95)
            Text("\(cuentas.count) \(cuentas.count == 1 ? "cuenta" : "cuentas")")
                .font(.caption)
                .opacity(0.8)
        }
        .foregroundStyle(.white)
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Marca.degradado, in: RoundedRectangle(cornerRadius: Marca.radio, style: .continuous))
    }

    private func mover(desde: IndexSet, hacia: Int) {
        var ordenadas = cuentas
        ordenadas.move(fromOffsets: desde, toOffset: hacia)
        for (i, cuenta) in ordenadas.enumerated() { cuenta.orden = i }
        try? context.save()
    }
}

struct CuentaFila: View {
    let cuenta: Cuenta

    var body: some View {
        HStack(spacing: 12) {
            IconoCuenta(tipo: cuenta.tipo, color: cuenta.color)
            VStack(alignment: .leading, spacing: 2) {
                Text(cuenta.nombre)
                    .font(.body.weight(.semibold))
                    .lineLimit(1)
                Text(cuenta.tipo.nombre)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 2) {
                if cuenta.esTarjeta {
                    Text("Deuda")
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(.secondary)
                    MontoTexto(valor: cuenta.deuda)
                        .font(.monto(16, peso: .semibold))
                        .foregroundStyle(cuenta.deuda > 0 ? Marca.frutilla : Color.primary)
                } else {
                    MontoTexto(valor: cuenta.saldo)
                        .font(.monto(16, peso: .semibold))
                        .foregroundStyle(cuenta.saldo < 0 ? Marca.frutilla : Color.primary)
                }
            }
        }
        .padding(.vertical, 2)
    }
}
