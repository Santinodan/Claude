import SwiftUI
import SwiftData

enum FiltroMovimientos: String, CaseIterable, Identifiable {
    case todos = "Todos"
    case gastos = "Gastos"
    case ingresos = "Ingresos"
    case transferencias = "Transferencias"

    var id: String { rawValue }

    func incluye(_ m: Movimiento) -> Bool {
        switch self {
        case .todos: true
        case .gastos: m.tipo == .gasto
        case .ingresos: m.tipo == .ingreso
        case .transferencias: m.tipo == .transferencia
        }
    }
}

struct MovimientosView: View {
    @Environment(\.modelContext) private var context
    @Environment(\.moneda) private var moneda
    @Query(sort: \Movimiento.fecha, order: .reverse) private var movimientos: [Movimiento]

    @State private var filtro: FiltroMovimientos = .todos
    @State private var busqueda = ""
    @State private var editando: Movimiento?

    private struct Dia: Identifiable {
        let id: Date
        var items: [Movimiento]
        var neto: Double { items.reduce(0) { $0 + $1.impactoNeto } }
    }

    private var filtrados: [Movimiento] {
        let texto = busqueda.recortado.lowercased()
        return movimientos.filter { m in
            guard filtro.incluye(m) else { return false }
            guard !texto.isEmpty else { return true }
            let campos = [
                m.nota,
                m.categoria?.nombre ?? "",
                m.cuenta?.nombre ?? "",
                m.cuentaDestino?.nombre ?? "",
                m.tipo.nombre,
                Formato.numero(m.monto),
            ]
            return campos.contains { $0.lowercased().contains(texto) }
        }
    }

    private var dias: [Dia] {
        var resultado: [Dia] = []
        for m in filtrados {
            let dia = Fechas.inicioDeDia(m.fecha)
            if let ultimo = resultado.indices.last, resultado[ultimo].id == dia {
                resultado[ultimo].items.append(m)
            } else {
                resultado.append(Dia(id: dia, items: [m]))
            }
        }
        return resultado
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 8) {
                            ForEach(FiltroMovimientos.allCases) { opcion in
                                Chip(titulo: opcion.rawValue, activo: filtro == opcion) {
                                    withAnimation(.snappy) { filtro = opcion }
                                }
                            }
                        }
                        .padding(.horizontal, 16)
                    }
                    .listRowInsets(EdgeInsets())
                    .listRowBackground(Color.clear)
                }

                ForEach(dias) { dia in
                    Section {
                        ForEach(dia.items) { movimiento in
                            Button {
                                editando = movimiento
                            } label: {
                                MovimientoFila(movimiento: movimiento)
                            }
                            .buttonStyle(.plain)
                            .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                                Button(role: .destructive) {
                                    withAnimation { Acciones.borrar(movimiento, en: context) }
                                } label: {
                                    Label("Borrar", systemImage: "trash")
                                }
                            }
                        }
                    } header: {
                        HStack {
                            Text(Fechas.tituloDia(dia.id))
                            Spacer()
                            if dia.neto != 0 {
                                Text(moneda.formatear(dia.neto, conSigno: true))
                                    .foregroundStyle(dia.neto > 0 ? Marca.hoja : Marca.frutilla)
                                    .monospacedDigit()
                            }
                        }
                        .font(.footnote.weight(.semibold))
                        .textCase(nil)
                    }
                }
            }
            .listStyle(.insetGrouped)
            .contentMargins(.bottom, 90, for: .scrollContent)
            .overlay {
                if filtrados.isEmpty {
                    if movimientos.isEmpty {
                        ContentUnavailableView(
                            "Todavía no hay movimientos",
                            systemImage: "tray",
                            description: Text("Tocá el botón + para cargar tu primer gasto o ingreso.")
                        )
                    } else if !busqueda.recortado.isEmpty {
                        ContentUnavailableView.search(text: busqueda)
                    } else {
                        ContentUnavailableView(
                            "No hay \(filtro.rawValue.lowercased())",
                            systemImage: "line.3.horizontal.decrease.circle",
                            description: Text("Probá con otro filtro.")
                        )
                    }
                }
            }
            .searchable(text: $busqueda, prompt: "Buscá por nota, categoría o cuenta")
            .navigationTitle("Movimientos")
            .sheet(item: $editando) { movimiento in
                MovimientoFormView(movimiento: movimiento)
            }
        }
        .botonAgregar()
    }
}
