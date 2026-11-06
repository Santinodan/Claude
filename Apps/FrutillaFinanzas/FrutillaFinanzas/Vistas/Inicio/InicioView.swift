import SwiftUI
import SwiftData

struct InicioView: View {
    @Query(sort: \Cuenta.orden) private var cuentas: [Cuenta]
    @Query private var cuotas: [Cuota]
    @Query private var suscripciones: [Suscripcion]

    @State private var mes = Fechas.inicioDeMes(.now)
    @State private var mostrarAjustes = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    TarjetaPatrimonio(resumen: Finanzas.patrimonio(cuentas: cuentas, cuotas: cuotas))
                    SelectorMes(mes: $mes)
                    ResumenMesView(
                        mes: mes,
                        compromisos: Finanzas.compromisos(cuotas: cuotas, suscripciones: suscripciones),
                        vencimientos: Finanzas.vencimientos(cuotas: cuotas, suscripciones: suscripciones)
                    )
                }
                .padding(.horizontal, 16)
                .padding(.top, 4)
                .padding(.bottom, 96)
            }
            .background(Marca.fondo)
            .navigationTitle("Inicio")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        mostrarAjustes = true
                    } label: {
                        Image(systemName: "gearshape")
                    }
                    .accessibilityLabel("Ajustes")
                }
            }
            .sheet(isPresented: $mostrarAjustes) {
                AjustesView()
            }
        }
        .botonAgregar()
    }
}

// MARK: Patrimonio

struct TarjetaPatrimonio: View {
    let resumen: Finanzas.Patrimonio

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Text("Patrimonio neto")
                    .font(.subheadline.weight(.semibold))
                    .opacity(0.9)
                Spacer()
                Text("🍓")
            }
            MontoTexto(valor: resumen.neto)
                .font(.monto(38))
                .minimumScaleFactor(0.5)
                .lineLimit(1)

            HStack(spacing: 12) {
                columna(titulo: "Tenés", valor: resumen.tenes, simbolo: "arrow.up.right")
                columna(titulo: "Debés", valor: resumen.debes, simbolo: "arrow.down.right")
            }
        }
        .foregroundStyle(.white)
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Marca.degradado, in: RoundedRectangle(cornerRadius: Marca.radio, style: .continuous))
        .shadow(color: Marca.frutilla.opacity(0.25), radius: 14, y: 8)
    }

    private func columna(titulo: String, valor: Double, simbolo: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Label(titulo, systemImage: simbolo)
                .font(.caption.weight(.semibold))
                .opacity(0.9)
            MontoTexto(valor: valor)
                .font(.monto(18, peso: .semibold))
                .minimumScaleFactor(0.6)
                .lineLimit(1)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.white.opacity(0.18), in: RoundedRectangle(cornerRadius: 16, style: .continuous))
    }
}

// MARK: Selector de mes

struct SelectorMes: View {
    @Binding var mes: Date

    var body: some View {
        HStack {
            Button {
                mes = Fechas.sumarMeses(-1, a: mes)
            } label: {
                Image(systemName: "chevron.left")
                    .frame(width: 36, height: 36)
            }
            .accessibilityLabel("Mes anterior")

            Spacer()

            Button {
                mes = Fechas.inicioDeMes(.now)
            } label: {
                VStack(spacing: 2) {
                    Text(Fechas.nombreMes(mes))
                        .font(.headline)
                        .foregroundStyle(.primary)
                    if !Fechas.esMismoMes(mes, .now) {
                        Text("Tocá para volver a este mes")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            Spacer()

            Button {
                mes = Fechas.sumarMeses(1, a: mes)
            } label: {
                Image(systemName: "chevron.right")
                    .frame(width: 36, height: 36)
            }
            .accessibilityLabel("Mes siguiente")
        }
        .font(.headline)
        .buttonStyle(.plain)
        .foregroundStyle(Marca.frutilla)
        .tarjeta(relleno: 8)
    }
}
