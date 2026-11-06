import SwiftUI
import SwiftData

enum FormularioCategoria: Identifiable {
    case nueva(esIngreso: Bool)
    case editar(Categoria)

    var id: String {
        switch self {
        case .nueva(let esIngreso): "nueva-\(esIngreso)"
        case .editar(let c): "editar-\(c.persistentModelID.hashValue)"
        }
    }
}

struct CategoriasView: View {
    @Environment(\.modelContext) private var context
    @Query(sort: \Categoria.orden) private var categorias: [Categoria]
    @State private var formulario: FormularioCategoria?

    private var gastos: [Categoria] { categorias.filter { !$0.esIngreso } }
    private var ingresos: [Categoria] { categorias.filter(\.esIngreso) }

    var body: some View {
        List {
            Section {
                ForEach(gastos) { fila($0) }
                    .onMove { mover(gastos, desde: $0, hacia: $1) }
                    .onDelete { borrar(gastos, en: $0) }
                Button {
                    formulario = .nueva(esIngreso: false)
                } label: {
                    Label("Nueva categoría de gasto", systemImage: "plus")
                }
            } header: {
                Text("Gastos")
            }

            Section {
                ForEach(ingresos) { fila($0) }
                    .onMove { mover(ingresos, desde: $0, hacia: $1) }
                    .onDelete { borrar(ingresos, en: $0) }
                Button {
                    formulario = .nueva(esIngreso: true)
                } label: {
                    Label("Nueva categoría de ingreso", systemImage: "plus")
                }
            } header: {
                Text("Ingresos")
            } footer: {
                Text("Tocá una categoría para editarla. Usá Editar para reordenar. Si borrás una categoría, sus movimientos quedan sin categoría.")
            }
        }
        .navigationTitle("Categorías")
        .toolbar { EditButton() }
        .sheet(item: $formulario) { f in
            switch f {
            case .nueva(let esIngreso): CategoriaFormView(esIngreso: esIngreso)
            case .editar(let c): CategoriaFormView(categoria: c)
            }
        }
    }

    private func fila(_ categoria: Categoria) -> some View {
        Button {
            formulario = .editar(categoria)
        } label: {
            HStack(spacing: 12) {
                CirculoEmoji(emoji: categoria.emoji, color: categoria.color, tamano: 36)
                Text(categoria.nombre)
                    .foregroundStyle(.primary)
                Spacer()
                Circle().fill(categoria.color).frame(width: 12, height: 12)
            }
        }
    }

    private func mover(_ lista: [Categoria], desde: IndexSet, hacia: Int) {
        var ordenadas = lista
        ordenadas.move(fromOffsets: desde, toOffset: hacia)
        for (i, c) in ordenadas.enumerated() { c.orden = i }
        try? context.save()
    }

    private func borrar(_ lista: [Categoria], en indices: IndexSet) {
        for i in indices { context.delete(lista[i]) }
        try? context.save()
    }
}

struct CategoriaFormView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var context
    @Query private var categorias: [Categoria]

    private let categoria: Categoria?

    @State private var nombre: String
    @State private var emoji: String
    @State private var colorHex: String
    @State private var esIngreso: Bool

    init(categoria: Categoria? = nil, esIngreso: Bool = false) {
        self.categoria = categoria
        _nombre = State(initialValue: categoria?.nombre ?? "")
        _emoji = State(initialValue: categoria?.emoji ?? "🏷️")
        _colorHex = State(initialValue: categoria?.colorHex ?? (esIngreso ? "#2FA85A" : "#E32B4A"))
        _esIngreso = State(initialValue: categoria?.esIngreso ?? esIngreso)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    HStack {
                        Spacer()
                        VStack(spacing: 8) {
                            TextField("🏷️", text: $emoji)
                                .font(.system(size: 40))
                                .multilineTextAlignment(.center)
                                .frame(width: 80, height: 80)
                                .background(Color(hex: colorHex).opacity(0.2), in: Circle())
                                .onChange(of: emoji) { _, nuevo in
                                    if nuevo.count > 1, let ultimo = nuevo.last { emoji = String(ultimo) }
                                }
                            Text("Tocá el círculo y elegí un emoji")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                    }
                    .listRowBackground(Color.clear)
                }

                Section {
                    TextField("Nombre", text: $nombre)
                    Picker("Tipo", selection: $esIngreso) {
                        Text("Gasto").tag(false)
                        Text("Ingreso").tag(true)
                    }
                    .pickerStyle(.segmented)
                }

                Section("Color") {
                    SelectorColor(colorHex: $colorHex)
                }
            }
            .navigationTitle(categoria == nil ? "Nueva categoría" : "Editar categoría")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancelar") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Guardar") { guardar() }
                        .fontWeight(.semibold)
                        .disabled(nombre.recortado.isEmpty)
                }
            }
        }
    }

    private func guardar() {
        let destino: Categoria
        if let categoria {
            destino = categoria
        } else {
            let orden = (categorias.filter { $0.esIngreso == esIngreso }.map(\.orden).max() ?? -1) + 1
            destino = Categoria(nombre: "", emoji: "🏷️", colorHex: colorHex, esIngreso: esIngreso, orden: orden)
            context.insert(destino)
        }
        destino.nombre = nombre.recortado
        destino.emoji = emoji.isEmpty ? "🏷️" : emoji
        destino.colorHex = colorHex
        destino.esIngreso = esIngreso
        try? context.save()
        dismiss()
    }
}
