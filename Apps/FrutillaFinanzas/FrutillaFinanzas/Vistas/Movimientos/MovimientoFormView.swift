import SwiftUI
import SwiftData

/// Alta y edición de gastos, ingresos y transferencias.
struct MovimientoFormView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var context
    @Query(sort: \Cuenta.orden) private var cuentas: [Cuenta]
    @Query(sort: \Categoria.orden) private var categorias: [Categoria]

    private let movimiento: Movimiento?

    @State private var tipo: TipoMovimiento
    @State private var montoTexto: String
    @State private var categoria: Categoria?
    @State private var cuenta: Cuenta?
    @State private var cuentaDestino: Cuenta?
    @State private var fecha: Date
    @State private var nota: String
    @State private var confirmarBorrado = false
    @FocusState private var montoEnfocado: Bool

    init(movimiento: Movimiento? = nil, tipo: TipoMovimiento = .gasto, cuenta: Cuenta? = nil) {
        self.movimiento = movimiento
        _tipo = State(initialValue: movimiento?.tipo ?? tipo)
        _montoTexto = State(initialValue: movimiento.map { Formato.numero($0.monto) } ?? "")
        _categoria = State(initialValue: movimiento?.categoria)
        _cuenta = State(initialValue: movimiento?.cuenta ?? cuenta)
        _cuentaDestino = State(initialValue: movimiento?.cuentaDestino)
        _fecha = State(initialValue: movimiento?.fecha ?? .now)
        _nota = State(initialValue: movimiento?.nota ?? "")
    }

    private var monto: Double { Formato.parsear(montoTexto) ?? 0 }

    private var categoriasDelTipo: [Categoria] {
        categorias.filter { $0.esIngreso == (tipo == .ingreso) }
    }

    private var esValido: Bool {
        guard monto > 0, let cuenta else { return false }
        if tipo == .transferencia {
            guard let cuentaDestino, cuentaDestino != cuenta else { return false }
        }
        return true
    }

    private var colorMonto: Color {
        switch tipo {
        case .gasto: Marca.frutilla
        case .ingreso: Marca.hoja
        case .transferencia: .blue
        }
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Picker("Tipo", selection: $tipo) {
                        ForEach(TipoMovimiento.allCases) { t in
                            Text(t.nombre).tag(t)
                        }
                    }
                    .pickerStyle(.segmented)
                    .listRowBackground(Color.clear)
                    .listRowInsets(EdgeInsets(top: 0, leading: 0, bottom: 8, trailing: 0))

                    CampoMontoGrande(texto: $montoTexto, foco: $montoEnfocado, color: colorMonto)
                }

                if tipo != .transferencia {
                    Section("Categoría") {
                        GrillaCategorias(categorias: categoriasDelTipo, seleccion: $categoria)
                    }
                }

                Section {
                    Picker(tipo == .transferencia ? "Desde" : "Cuenta", selection: $cuenta) {
                        Text("Elegí una cuenta").tag(Cuenta?.none)
                        ForEach(cuentas) { c in
                            Text(c.nombre).tag(Cuenta?.some(c))
                        }
                    }
                    if tipo == .transferencia {
                        Picker("Hacia", selection: $cuentaDestino) {
                            Text("Elegí una cuenta").tag(Cuenta?.none)
                            ForEach(cuentas.filter { $0 != cuenta }) { c in
                                Text(c.nombre).tag(Cuenta?.some(c))
                            }
                        }
                    }
                    DatePicker("Fecha", selection: $fecha, displayedComponents: .date)
                    TextField("Nota (opcional)", text: $nota, axis: .vertical)
                        .lineLimit(1...3)
                } footer: {
                    if tipo == .transferencia && cuentas.count < 2 {
                        Text("Para transferir necesitás al menos dos cuentas. Creá otra en la pestaña Cuentas.")
                    }
                }

                if movimiento != nil {
                    Section {
                        Button("Eliminar movimiento", role: .destructive) {
                            confirmarBorrado = true
                        }
                        .frame(maxWidth: .infinity)
                    }
                }
            }
            .navigationTitle(movimiento == nil ? "Nuevo movimiento" : "Editar movimiento")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancelar") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Guardar") { guardar() }
                        .fontWeight(.semibold)
                        .disabled(!esValido)
                }
                ToolbarItemGroup(placement: .keyboard) {
                    Spacer()
                    Button("Listo") { montoEnfocado = false }
                }
            }
            .confirmationDialog("¿Eliminar este movimiento?", isPresented: $confirmarBorrado, titleVisibility: .visible) {
                Button("Eliminar", role: .destructive) {
                    if let movimiento { Acciones.borrar(movimiento, en: context) }
                    dismiss()
                }
            }
            .onChange(of: tipo) { _, nuevo in
                if let categoria, categoria.esIngreso != (nuevo == .ingreso) {
                    self.categoria = nil
                }
                if nuevo == .transferencia, cuentaDestino == nil {
                    cuentaDestino = cuentas.first { $0 != cuenta }
                }
            }
            .onAppear {
                if cuenta == nil { cuenta = cuentas.first }
            }
            .task {
                // El teclado aparece apenas se abre el formulario.
                guard movimiento == nil else { return }
                try? await Task.sleep(for: .milliseconds(350))
                montoEnfocado = true
            }
        }
        .presentationDragIndicator(.visible)
    }

    private func guardar() {
        guard esValido else { return }
        let destino: Movimiento
        if let movimiento {
            destino = movimiento
        } else {
            destino = Movimiento()
            context.insert(destino)
        }
        destino.monto = monto
        destino.tipo = tipo
        destino.fecha = fecha
        destino.nota = nota.recortado
        destino.cuenta = cuenta
        destino.cuentaDestino = tipo == .transferencia ? cuentaDestino : nil
        destino.categoria = tipo == .transferencia ? nil : categoria
        try? context.save()
        dismiss()
    }
}

/// Grilla de categorías con emoji.
struct GrillaCategorias: View {
    let categorias: [Categoria]
    @Binding var seleccion: Categoria?

    private let columnas = [GridItem(.adaptive(minimum: 72), spacing: 8)]

    var body: some View {
        if categorias.isEmpty {
            Text("No tenés categorías. Creá una en Ajustes.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        } else {
            LazyVGrid(columns: columnas, spacing: 12) {
                ForEach(categorias) { cat in
                    let elegida = seleccion == cat
                    Button {
                        withAnimation(.snappy) { seleccion = elegida ? nil : cat }
                    } label: {
                        VStack(spacing: 6) {
                            Text(cat.emoji)
                                .font(.system(size: 24))
                                .frame(width: 50, height: 50)
                                .background(cat.color.opacity(elegida ? 0.35 : 0.15), in: Circle())
                                .overlay {
                                    Circle().strokeBorder(elegida ? cat.color : .clear, lineWidth: 2.5)
                                }
                            Text(cat.nombre)
                                .font(.caption2.weight(elegida ? .bold : .regular))
                                .foregroundStyle(elegida ? Color.primary : Color.secondary)
                                .lineLimit(1)
                                .minimumScaleFactor(0.8)
                        }
                        .frame(maxWidth: .infinity)
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityAddTraits(elegida ? .isSelected : [])
                }
            }
            .padding(.vertical, 6)
        }
    }
}
