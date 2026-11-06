import SwiftUI
import SwiftData

enum SeccionCuotas: String, CaseIterable, Identifiable {
    case cuotas = "Cuotas y créditos"
    case suscripciones = "Suscripciones"
    var id: String { rawValue }
}

struct CuotasView: View {
    @Query(sort: \Cuota.creada, order: .reverse) private var cuotas: [Cuota]
    @Query(sort: \Suscripcion.proximoCobro) private var suscripciones: [Suscripcion]

    @State private var seccion: SeccionCuotas = .cuotas
    @State private var nuevaCuota = false
    @State private var formularioSuscripcion: FormularioSuscripcion?

    private var compromisos: Finanzas.Compromisos {
        Finanzas.compromisos(cuotas: cuotas, suscripciones: suscripciones)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    Picker("Sección", selection: $seccion) {
                        ForEach(SeccionCuotas.allCases) { s in
                            Text(s.rawValue).tag(s)
                        }
                    }
                    .pickerStyle(.segmented)

                    resumen

                    switch seccion {
                    case .cuotas:
                        ListaCuotas(cuotas: cuotas, nuevaCuota: $nuevaCuota)
                    case .suscripciones:
                        ListaSuscripciones(suscripciones: suscripciones, formulario: $formularioSuscripcion)
                    }
                }
                .padding(.horizontal, 16)
                .padding(.top, 4)
                .padding(.bottom, 96)
            }
            .background(Marca.fondo)
            .navigationTitle("Cuotas")
            .navigationDestination(for: Cuota.self) { cuota in
                CuotaDetalleView(cuota: cuota)
            }
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        Button {
                            nuevaCuota = true
                        } label: {
                            Label("Nueva cuota o crédito", systemImage: "creditcard")
                        }
                        Button {
                            formularioSuscripcion = .nueva(nil)
                        } label: {
                            Label("Nueva suscripción", systemImage: "repeat")
                        }
                    } label: {
                        Image(systemName: "plus.circle.fill")
                    }
                    .accessibilityLabel("Agregar")
                }
            }
            .sheet(isPresented: $nuevaCuota) {
                CuotaFormView()
            }
            .sheet(item: $formularioSuscripcion) { formulario in
                switch formulario {
                case .nueva(let plantilla):
                    SuscripcionFormView(plantilla: plantilla)
                case .editar(let suscripcion):
                    SuscripcionFormView(suscripcion: suscripcion)
                }
            }
        }
        .botonAgregar()
    }

    private var resumen: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Compromisos mensuales")
                .font(.subheadline.weight(.semibold))
                .opacity(0.9)
            MontoTexto(valor: compromisos.total)
                .font(.monto(34))
                .minimumScaleFactor(0.5)
                .lineLimit(1)
            HStack(spacing: 12) {
                datoResumen("Cuotas", compromisos.cuotas, cantidad: cuotas.filter { !$0.terminada }.count)
                datoResumen("Suscripciones", compromisos.suscripciones, cantidad: suscripciones.filter(\.activa).count)
            }
        }
        .foregroundStyle(.white)
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Marca.degradado, in: RoundedRectangle(cornerRadius: Marca.radio, style: .continuous))
    }

    private func datoResumen(_ titulo: String, _ valor: Double, cantidad: Int) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text("\(titulo) (\(cantidad))")
                .font(.caption.weight(.semibold))
                .opacity(0.9)
            MontoTexto(valor: valor)
                .font(.monto(17, peso: .semibold))
                .minimumScaleFactor(0.6)
                .lineLimit(1)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.white.opacity(0.18), in: RoundedRectangle(cornerRadius: 16, style: .continuous))
    }
}

// MARK: Lista de cuotas

struct ListaCuotas: View {
    let cuotas: [Cuota]
    @Binding var nuevaCuota: Bool

    private var activas: [Cuota] { cuotas.filter { !$0.terminada } }
    private var terminadas: [Cuota] { cuotas.filter(\.terminada) }

    var body: some View {
        if cuotas.isEmpty {
            VStack(spacing: 12) {
                Text("💳").font(.system(size: 44))
                Text("Sin cuotas ni créditos")
                    .font(.headline)
                Text("Cargá tus compras en cuotas o préstamos y te avisamos antes de cada vencimiento.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                Button("Cargar una cuota") { nuevaCuota = true }
                    .buttonStyle(.borderedProminent)
                    .tint(Marca.frutilla)
            }
            .padding(.vertical, 12)
            .tarjeta()
        } else {
            ForEach(activas) { cuota in
                CuotaTarjeta(cuota: cuota)
            }
            if !terminadas.isEmpty {
                Text("Terminadas")
                    .font(.headline)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.top, 8)
                ForEach(terminadas) { cuota in
                    CuotaTarjeta(cuota: cuota)
                        .opacity(0.7)
                }
            }
        }
    }
}

struct CuotaTarjeta: View {
    @Environment(\.modelContext) private var context
    @Environment(\.moneda) private var moneda
    let cuota: Cuota
    @State private var confirmarPago = false
    @State private var pagos = 0

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            NavigationLink(value: cuota) {
                VStack(alignment: .leading, spacing: 12) {
                    HStack(spacing: 12) {
                        CirculoEmoji(emoji: cuota.tipo.emoji, color: Marca.frutilla, tamano: 42)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(cuota.nombre)
                                .font(.headline)
                                .foregroundStyle(.primary)
                                .lineLimit(1)
                            Text(cuota.tipo.nombre)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        VStack(alignment: .trailing, spacing: 2) {
                            MontoTexto(valor: cuota.valorCuota)
                                .font(.monto(17))
                                .foregroundStyle(.primary)
                            Text("por cuota")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                        Image(systemName: "chevron.right")
                            .font(.caption.weight(.bold))
                            .foregroundStyle(.tertiary)
                    }

                    BarraProgreso(valor: cuota.progreso, color: cuota.terminada ? Marca.hoja : Marca.frutilla)

                    HStack {
                        Text("\(cuota.pagadas) de \(cuota.cantidad)")
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(.primary)
                        Spacer()
                        if cuota.terminada {
                            Text("¡Terminaste de pagar! 🎉")
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(Marca.hoja)
                        } else {
                            Text("Faltan \(moneda.formatear(cuota.pendiente))")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                    }

                    if let vence = cuota.proximoVencimiento {
                        Label {
                            Text("Próximo vencimiento: \(Fechas.corta(vence)) · \(cuota.vencida ? "Vencida" : Fechas.relativa(vence))")
                        } icon: {
                            Image(systemName: cuota.vencida ? "exclamationmark.circle.fill" : "calendar")
                        }
                        .font(.caption.weight(.medium))
                        .foregroundStyle(cuota.vencida ? Marca.frutilla : Color.secondary)
                    }
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)

            if !cuota.terminada {
                Button {
                    confirmarPago = true
                } label: {
                    Label("Pagar cuota", systemImage: "checkmark.circle.fill")
                        .font(.subheadline.weight(.semibold))
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(Marca.frutilla)
                .controlSize(.large)
            }
        }
        .tarjeta()
        .sensoryFeedback(.success, trigger: pagos)
        .confirmationDialog(
            "Pagar cuota \(cuota.pagadas + 1) de \(cuota.cantidad)",
            isPresented: $confirmarPago,
            titleVisibility: .visible
        ) {
            Button("Pagar \(moneda.formatear(cuota.valorCuota))") {
                withAnimation {
                    Acciones.pagarCuota(cuota, en: context)
                    pagos += 1
                }
            }
        } message: {
            Text("Se registra el gasto en \(cuota.cuenta?.nombre ?? "tu cuenta principal") con la categoría Cuotas.")
        }
    }
}
