import SwiftUI
import SwiftData

struct AjustesView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var context
    @AppStorage("moneda") private var monedaRaw = Moneda.ARS.rawValue
    @AppStorage(Recordatorios.claveActivos) private var recordatoriosActivos = true
    @AppStorage(Recordatorios.claveHora) private var horaAviso = 600
    @Query(sort: \Movimiento.fecha) private var movimientos: [Movimiento]

    @State private var periodo: ExportadorCSV.Periodo = .todo
    @State private var confirmarBorrado = false

    private var moneda: Moneda { Moneda(rawValue: monedaRaw) ?? .ARS }

    private var movimientosAExportar: [Movimiento] {
        movimientos.filter { periodo.incluye($0.fecha) }
    }

    private var archivo: ArchivoCSV {
        let sufijo = periodo == .todo ? "todo" : Fechas.numerica(.now).replacingOccurrences(of: "/", with: "-")
        return ArchivoCSV(
            nombre: "frutilla-movimientos-\(sufijo).csv",
            contenido: ExportadorCSV.generar(movimientosAExportar, moneda: moneda)
        )
    }

    private var horaBinding: Binding<Date> {
        Binding {
            Fechas.calendario.date(byAdding: .minute, value: horaAviso, to: Fechas.inicioDeDia(.now)) ?? .now
        } set: { nueva in
            let comps = Fechas.calendario.dateComponents([.hour, .minute], from: nueva)
            horaAviso = (comps.hour ?? 10) * 60 + (comps.minute ?? 0)
        }
    }

    private var version: String {
        let v = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0"
        let b = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "1"
        return "\(v) (\(b))"
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("General") {
                    Picker("Moneda", selection: $monedaRaw) {
                        ForEach(Moneda.allCases) { m in
                            Text("\(m.bandera) \(m.nombre) (\(m.rawValue))").tag(m.rawValue)
                        }
                    }
                    .pickerStyle(.navigationLink)

                    NavigationLink {
                        CategoriasView()
                    } label: {
                        Label("Categorías", systemImage: "square.grid.2x2")
                    }
                }

                Section {
                    Toggle("Avisos de vencimientos", isOn: $recordatoriosActivos)
                    if recordatoriosActivos {
                        DatePicker("Hora del aviso", selection: horaBinding, displayedComponents: .hourAndMinute)
                    }
                } header: {
                    Text("Recordatorios")
                } footer: {
                    Text("Te avisamos el día antes de cada cuota y los días que elijas antes de cada suscripción.")
                }

                Section {
                    Picker("Período", selection: $periodo) {
                        ForEach(ExportadorCSV.Periodo.allCases) { p in
                            Text(p.rawValue).tag(p)
                        }
                    }
                    ShareLink(item: archivo, preview: SharePreview(archivo.nombre)) {
                        Label("Exportar movimientos a CSV", systemImage: "square.and.arrow.up")
                    }
                    .disabled(movimientosAExportar.isEmpty)
                } header: {
                    Text("Exportar")
                } footer: {
                    Text(movimientosAExportar.isEmpty
                         ? "No hay movimientos en este período."
                         : "\(movimientosAExportar.count) movimientos. Se abre directo en Excel, Numbers o Google Sheets.")
                }

                Section {
                    Button("Borrar todos los datos", role: .destructive) {
                        confirmarBorrado = true
                    }
                } footer: {
                    Text("Tus datos quedan solo en este teléfono: no hay servidor ni cuenta.")
                }

                Section {
                    HStack {
                        Text("🍓 Frutilla Finanzas")
                        Spacer()
                        Text(version).foregroundStyle(.secondary)
                    }
                }
            }
            .navigationTitle("Ajustes")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Listo") { dismiss() }
                }
            }
            .onChange(of: recordatoriosActivos) { _, _ in Recordatorios.reprogramar(context) }
            .onChange(of: horaAviso) { _, _ in Recordatorios.reprogramar(context) }
            .confirmationDialog("¿Borrar todos los datos?", isPresented: $confirmarBorrado, titleVisibility: .visible) {
                Button("Borrar todo", role: .destructive) {
                    Acciones.borrarTodo(en: context)
                }
            } message: {
                Text("Se borran movimientos, cuentas, cuotas, suscripciones y categorías. Vuelven las categorías y la cuenta Efectivo de fábrica. No se puede deshacer.")
            }
        }
    }
}
