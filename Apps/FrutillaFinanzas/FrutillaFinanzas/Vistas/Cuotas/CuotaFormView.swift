import SwiftUI
import SwiftData

struct CuotaFormView: View {
    enum ModoMonto: String, CaseIterable, Identifiable {
        case porCuota = "Valor de cada cuota"
        case total = "Total"
        var id: String { rawValue }
    }

    static let atajos = [1, 3, 6, 9, 12, 18, 24, 36]

    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var context
    @Environment(\.moneda) private var moneda
    @Query(sort: \Cuenta.orden) private var cuentas: [Cuenta]

    private let cuota: Cuota?

    @State private var nombre: String
    @State private var tipo: TipoCuota
    @State private var modo: ModoMonto = .porCuota
    @State private var montoTexto: String
    @State private var cantidad: Int
    @State private var pagadas: Int
    @State private var primerVencimiento: Date
    @State private var cuenta: Cuenta?
    @State private var avisar: Bool

    init(cuota: Cuota? = nil) {
        self.cuota = cuota
        _nombre = State(initialValue: cuota?.nombre ?? "")
        _tipo = State(initialValue: cuota?.tipo ?? .compraEnCuotas)
        _montoTexto = State(initialValue: cuota.map { Formato.numero($0.valorCuota) } ?? "")
        _cantidad = State(initialValue: cuota?.cantidad ?? 12)
        _pagadas = State(initialValue: cuota?.pagadas ?? 0)
        _primerVencimiento = State(initialValue: cuota?.primerVencimiento ?? Fechas.sumarMeses(1, a: .now))
        _cuenta = State(initialValue: cuota?.cuenta)
        _avisar = State(initialValue: cuota?.avisar ?? true)
    }

    private var montoIngresado: Double { Formato.parsear(montoTexto) ?? 0 }

    private var valorCuota: Double {
        switch modo {
        case .porCuota: montoIngresado
        case .total: cantidad > 0 ? (montoIngresado / Double(cantidad) * 100).rounded() / 100 : 0
        }
    }

    private var esValido: Bool {
        !nombre.recortado.isEmpty && valorCuota > 0 && cantidad >= 1 && pagadas <= cantidad
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Nombre (ej. Heladera, Préstamo auto)", text: $nombre)
                    Picker("Tipo", selection: $tipo) {
                        ForEach(TipoCuota.allCases) { t in
                            Text("\(t.emoji) \(t.nombre)").tag(t)
                        }
                    }
                }

                Section {
                    Picker("Cargar", selection: $modo) {
                        ForEach(ModoMonto.allCases) { m in
                            Text(m.rawValue).tag(m)
                        }
                    }
                    .pickerStyle(.segmented)
                    .onChange(of: modo) { anterior, nuevo in
                        // Convierte lo que ya estaba cargado al otro modo.
                        guard montoIngresado > 0 else { return }
                        let convertido = nuevo == .total
                            ? montoIngresado * Double(cantidad)
                            : montoIngresado / Double(max(cantidad, 1))
                        montoTexto = Formato.numero(convertido)
                    }
                    CampoMonto(titulo: modo == .total ? "Total" : "Cada cuota", texto: $montoTexto)
                } footer: {
                    if valorCuota > 0 {
                        Text("\(cantidad) \(cantidad == 1 ? "cuota" : "cuotas") de \(moneda.formatear(valorCuota)) · Total \(moneda.formatear(valorCuota * Double(cantidad)))")
                            .font(.footnote.weight(.semibold))
                    }
                }

                Section("Cantidad de cuotas") {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 8) {
                            ForEach(Self.atajos, id: \.self) { n in
                                Chip(titulo: "\(n)", activo: cantidad == n) {
                                    cantidad = n
                                    pagadas = min(pagadas, n)
                                }
                            }
                        }
                        .padding(.vertical, 4)
                    }
                    Stepper(value: $cantidad, in: 1...480) {
                        Text("\(cantidad) \(cantidad == 1 ? "cuota" : "cuotas")")
                            .monospacedDigit()
                    }
                    .onChange(of: cantidad) { _, nueva in
                        pagadas = min(pagadas, nueva)
                    }
                    Stepper(value: $pagadas, in: 0...cantidad) {
                        Text(pagadas == 0 ? "Todavía no pagaste ninguna" : "Ya pagaste \(pagadas)")
                            .monospacedDigit()
                    }
                }

                Section {
                    DatePicker("Primer vencimiento", selection: $primerVencimiento, displayedComponents: .date)
                    Picker("Cuenta de pago", selection: $cuenta) {
                        Text("Cuenta principal").tag(Cuenta?.none)
                        ForEach(cuentas) { c in
                            Text(c.nombre).tag(Cuenta?.some(c))
                        }
                    }
                    Toggle("Avisarme antes de cada vencimiento", isOn: $avisar)
                } footer: {
                    Text("Las cuotas vencen todos los meses el mismo día que la primera. Te avisamos el día anterior.")
                }
            }
            .navigationTitle(cuota == nil ? "Nueva cuota" : "Editar cuota")
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
            }
        }
    }

    private func guardar() {
        guard esValido else { return }
        let destino: Cuota
        if let cuota {
            destino = cuota
        } else {
            destino = Cuota(nombre: "", valorCuota: 0, cantidad: 1, primerVencimiento: primerVencimiento)
            context.insert(destino)
        }
        destino.nombre = nombre.recortado
        destino.tipo = tipo
        destino.valorCuota = valorCuota
        destino.cantidad = cantidad
        destino.pagadas = pagadas
        destino.primerVencimiento = primerVencimiento
        destino.cuenta = cuenta
        destino.avisar = avisar
        Acciones.guardar(context)
        dismiss()
    }
}
