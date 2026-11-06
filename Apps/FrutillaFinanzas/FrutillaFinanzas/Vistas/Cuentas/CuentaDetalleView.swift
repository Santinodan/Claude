import SwiftUI
import SwiftData

struct CuentaDetalleView: View {
    @Environment(\.modelContext) private var context
    @Environment(\.dismiss) private var dismiss
    let cuenta: Cuenta

    @State private var formulario: TipoMovimiento?
    @State private var editandoMovimiento: Movimiento?
    @State private var editandoCuenta = false
    @State private var confirmarBorrado = false
    @State private var borrando = false

    var body: some View {
        List {
            if !borrando {
                Section {
                    encabezado
                        .listRowInsets(EdgeInsets())
                        .listRowBackground(Color.clear)
                }

                Section {
                    HStack(spacing: 10) {
                        botonRapido("Ingreso", simbolo: "arrow.down.circle.fill", color: Marca.hoja, tipo: .ingreso)
                        botonRapido("Gasto", simbolo: "arrow.up.circle.fill", color: Marca.frutilla, tipo: .gasto)
                        botonRapido("Transferir", simbolo: "arrow.left.arrow.right.circle.fill", color: .blue, tipo: .transferencia)
                    }
                    .listRowInsets(EdgeInsets())
                    .listRowBackground(Color.clear)
                }

                Section("Historial") {
                    let historial = cuenta.historial
                    if historial.isEmpty {
                        Text("Todavía no hay movimientos en esta cuenta.")
                            .foregroundStyle(.secondary)
                    }
                    ForEach(historial) { movimiento in
                        Button {
                            editandoMovimiento = movimiento
                        } label: {
                            MovimientoFila(movimiento: movimiento, cuentaContexto: cuenta, mostrarFecha: true)
                        }
                        .buttonStyle(.plain)
                        .swipeActions {
                            Button(role: .destructive) {
                                withAnimation { Acciones.borrar(movimiento, en: context) }
                            } label: {
                                Label("Borrar", systemImage: "trash")
                            }
                        }
                    }
                }
            }
        }
        .listStyle(.insetGrouped)
        .contentMargins(.bottom, 90, for: .scrollContent)
        .navigationTitle(borrando ? "" : cuenta.nombre)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Menu {
                    Button {
                        editandoCuenta = true
                    } label: {
                        Label("Editar cuenta", systemImage: "pencil")
                    }
                    Button(role: .destructive) {
                        confirmarBorrado = true
                    } label: {
                        Label("Eliminar cuenta", systemImage: "trash")
                    }
                } label: {
                    Image(systemName: "ellipsis.circle")
                }
            }
        }
        .sheet(item: $formulario) { tipo in
            MovimientoFormView(tipo: tipo, cuenta: cuenta)
        }
        .sheet(item: $editandoMovimiento) { movimiento in
            MovimientoFormView(movimiento: movimiento)
        }
        .sheet(isPresented: $editandoCuenta) {
            CuentaFormView(cuenta: cuenta)
        }
        .confirmationDialog(
            "¿Eliminar esta cuenta?",
            isPresented: $confirmarBorrado,
            titleVisibility: .visible
        ) {
            Button("Eliminar cuenta y movimientos", role: .destructive) { eliminar() }
        } message: {
            let cantidad = cuenta.movimientos.count + cuenta.transferenciasEntrantes.count
            Text(cantidad == 0
                 ? "La cuenta no tiene movimientos."
                 : "También se van a borrar sus \(cantidad) movimientos. No se puede deshacer.")
        }
    }

    private var encabezado: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Label(cuenta.tipo.nombre, systemImage: cuenta.tipo.simbolo)
                    .font(.subheadline.weight(.semibold))
                Spacer()
            }
            .opacity(0.9)
            Text(cuenta.esTarjeta ? "Deuda" : "Saldo")
                .font(.caption.weight(.semibold))
                .opacity(0.85)
            MontoTexto(valor: cuenta.esTarjeta ? cuenta.deuda : cuenta.saldo)
                .font(.monto(38))
                .minimumScaleFactor(0.5)
                .lineLimit(1)
        }
        .foregroundStyle(.white)
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            LinearGradient(colors: [cuenta.color, cuenta.color.opacity(0.7)], startPoint: .topLeading, endPoint: .bottomTrailing),
            in: RoundedRectangle(cornerRadius: Marca.radio, style: .continuous)
        )
    }

    private func botonRapido(_ titulo: String, simbolo: String, color: Color, tipo: TipoMovimiento) -> some View {
        Button {
            formulario = tipo
        } label: {
            VStack(spacing: 6) {
                Image(systemName: simbolo)
                    .font(.title2)
                    .foregroundStyle(color)
                Text(titulo)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.primary)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .background(Marca.superficie, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        }
        .buttonStyle(.plain)
    }

    private func eliminar() {
        // Primero se oculta el contenido y se vuelve atrás; después se borra,
        // así ninguna vista lee la cuenta ya eliminada.
        borrando = true
        dismiss()
        let cuenta = self.cuenta
        let context = self.context
        Task { @MainActor in
            try? await Task.sleep(for: .milliseconds(450))
            context.delete(cuenta)
            Acciones.guardar(context)
        }
    }
}
