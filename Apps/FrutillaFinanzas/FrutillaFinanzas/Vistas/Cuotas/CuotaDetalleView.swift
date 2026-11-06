import SwiftUI
import SwiftData

struct CuotaDetalleView: View {
    @Environment(\.modelContext) private var context
    @Environment(\.dismiss) private var dismiss
    @Environment(\.moneda) private var moneda
    let cuota: Cuota

    @State private var editando = false
    @State private var confirmarBorrado = false
    @State private var confirmarPago = false
    @State private var borrando = false
    @State private var pagos = 0

    var body: some View {
        List {
            if !borrando {
                Section {
                    encabezado
                        .listRowInsets(EdgeInsets())
                        .listRowBackground(Color.clear)
                }

                if !cuota.terminada {
                    Section {
                        Button {
                            confirmarPago = true
                        } label: {
                            Label("Pagar cuota \(cuota.pagadas + 1) de \(cuota.cantidad)", systemImage: "checkmark.circle.fill")
                                .font(.headline)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 6)
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(Marca.frutilla)
                        .listRowInsets(EdgeInsets())
                        .listRowBackground(Color.clear)
                    }
                }

                Section("Detalle") {
                    fila("Tipo", cuota.tipo.nombre)
                    fila("Valor de cada cuota", moneda.formatear(cuota.valorCuota))
                    fila("Total", moneda.formatear(cuota.total))
                    fila("Pagado", moneda.formatear(cuota.valorCuota * Double(cuota.pagadas)))
                    fila("Falta pagar", moneda.formatear(cuota.pendiente))
                    fila("Primer vencimiento", Fechas.corta(cuota.primerVencimiento))
                    if let vence = cuota.proximoVencimiento {
                        fila("Próximo vencimiento", "\(Fechas.corta(vence)) · \(cuota.vencida ? "Vencida" : Fechas.relativa(vence))")
                    }
                    fila("Cuenta de pago", cuota.cuenta?.nombre ?? "Cuenta principal")
                    fila("Aviso", cuota.avisar ? "Un día antes" : "Desactivado")
                }

                Section {
                    if cuota.pagos.isEmpty {
                        Text("Todavía no registraste pagos desde la app.")
                            .foregroundStyle(.secondary)
                    }
                    ForEach(cuota.pagosOrdenados) { pago in
                        MovimientoFila(movimiento: pago, mostrarFecha: true)
                            .swipeActions {
                                Button(role: .destructive) {
                                    withAnimation { Acciones.borrar(pago, en: context) }
                                } label: {
                                    Label("Anular", systemImage: "arrow.uturn.backward")
                                }
                            }
                    }
                } header: {
                    Text("Pagos")
                } footer: {
                    if !cuota.pagos.isEmpty {
                        Text("Deslizá un pago para anularlo: se borra el gasto y se descuenta la cuota pagada.")
                    }
                }
            }
        }
        .listStyle(.insetGrouped)
        .contentMargins(.bottom, 90, for: .scrollContent)
        .navigationTitle(borrando ? "" : cuota.nombre)
        .navigationBarTitleDisplayMode(.inline)
        .sensoryFeedback(.success, trigger: pagos)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Menu {
                    Button {
                        editando = true
                    } label: {
                        Label("Editar", systemImage: "pencil")
                    }
                    Button(role: .destructive) {
                        confirmarBorrado = true
                    } label: {
                        Label("Eliminar", systemImage: "trash")
                    }
                } label: {
                    Image(systemName: "ellipsis.circle")
                }
            }
        }
        .sheet(isPresented: $editando) {
            CuotaFormView(cuota: cuota)
        }
        .confirmationDialog("Pagar cuota", isPresented: $confirmarPago, titleVisibility: .visible) {
            Button("Pagar \(moneda.formatear(cuota.valorCuota))") {
                withAnimation {
                    Acciones.pagarCuota(cuota, en: context)
                    pagos += 1
                }
            }
        } message: {
            Text("Se registra el gasto en \(cuota.cuenta?.nombre ?? "tu cuenta principal") con la categoría Cuotas.")
        }
        .confirmationDialog("¿Eliminar esta cuota?", isPresented: $confirmarBorrado, titleVisibility: .visible) {
            Button("Eliminar", role: .destructive) { eliminar() }
        } message: {
            Text("Los pagos que ya registraste quedan en tus movimientos.")
        }
    }

    private var encabezado: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text(cuota.tipo.emoji).font(.title)
                Text(cuota.tipo.nombre).font(.subheadline.weight(.semibold))
                Spacer()
            }
            .opacity(0.95)
            Text("\(cuota.pagadas) de \(cuota.cantidad) cuotas")
                .font(.monto(30))
            BarraProgreso(valor: cuota.progreso, color: .white, alto: 12)
            HStack {
                Text("\(Int((cuota.progreso * 100).rounded()))% pagado")
                Spacer()
                Text(cuota.terminada ? "¡Listo! 🎉" : "Faltan \(cuota.restantes)")
            }
            .font(.subheadline.weight(.semibold))
            .opacity(0.9)
        }
        .foregroundStyle(.white)
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(cuota.terminada ? AnyShapeStyle(Marca.hoja.gradient) : AnyShapeStyle(Marca.degradado),
                    in: RoundedRectangle(cornerRadius: Marca.radio, style: .continuous))
    }

    private func fila(_ titulo: String, _ valor: String) -> some View {
        HStack {
            Text(titulo)
            Spacer()
            Text(valor)
                .foregroundStyle(.secondary)
                .monospacedDigit()
                .multilineTextAlignment(.trailing)
        }
    }

    private func eliminar() {
        borrando = true
        dismiss()
        let cuota = self.cuota
        let context = self.context
        Task { @MainActor in
            try? await Task.sleep(for: .milliseconds(450))
            context.delete(cuota)
            Acciones.guardar(context)
        }
    }
}
