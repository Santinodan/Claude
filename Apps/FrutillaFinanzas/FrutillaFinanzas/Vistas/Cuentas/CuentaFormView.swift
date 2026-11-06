import SwiftUI
import SwiftData

struct CuentaFormView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var context
    @Query(sort: \Cuenta.orden) private var cuentas: [Cuenta]

    private let cuenta: Cuenta?

    @State private var nombre: String
    @State private var tipo: TipoCuenta
    @State private var saldoTexto: String
    @State private var saldoNegativo: Bool
    @State private var colorHex: String

    init(cuenta: Cuenta? = nil) {
        self.cuenta = cuenta
        _nombre = State(initialValue: cuenta?.nombre ?? "")
        _tipo = State(initialValue: cuenta?.tipo ?? .banco)
        let inicial = cuenta?.saldoInicial ?? 0
        _saldoTexto = State(initialValue: inicial == 0 ? "" : Formato.numero(inicial))
        // En tarjetas el saldo inicial negativo es deuda; en el resto, cuenta en rojo.
        _saldoNegativo = State(initialValue: cuenta.map { !$0.esTarjeta && $0.saldoInicial < 0 } ?? false)
        _colorHex = State(initialValue: cuenta?.colorHex ?? Marca.paleta[6])
    }

    private var valor: Double { Formato.parsear(saldoTexto) ?? 0 }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    HStack {
                        Spacer()
                        VStack(spacing: 8) {
                            IconoCuenta(tipo: tipo, color: Color(hex: colorHex), tamano: 64)
                            Text(nombre.isEmpty ? "Nueva cuenta" : nombre)
                                .font(.headline)
                        }
                        Spacer()
                    }
                    .listRowBackground(Color.clear)
                }

                Section {
                    TextField("Nombre (ej. Banco Nación, Mercado Pago)", text: $nombre)
                    Picker("Tipo", selection: $tipo) {
                        ForEach(TipoCuenta.allCases) { t in
                            Label(t.nombre, systemImage: t.simbolo).tag(t)
                        }
                    }
                }

                Section {
                    CampoMonto(titulo: tipo == .tarjetaCredito ? "Deuda actual" : "Saldo inicial", texto: $saldoTexto)
                    if tipo != .tarjetaCredito {
                        Toggle("Está en negativo", isOn: $saldoNegativo)
                    }
                } footer: {
                    Text(tipo == .tarjetaCredito
                         ? "Cargá lo que debés hoy en la tarjeta. Los gastos con tarjeta suman a la deuda y los pagos la bajan."
                         : "El saldo actual se calcula sumando los ingresos y restando los gastos a este saldo inicial.")
                }

                Section("Color") {
                    SelectorColor(colorHex: $colorHex)
                }
            }
            .navigationTitle(cuenta == nil ? "Nueva cuenta" : "Editar cuenta")
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
        let destino: Cuenta
        if let cuenta {
            destino = cuenta
        } else {
            destino = Cuenta(nombre: "", orden: (cuentas.map(\.orden).max() ?? -1) + 1)
            context.insert(destino)
        }
        destino.nombre = nombre.recortado
        destino.tipo = tipo
        let negativo = tipo == .tarjetaCredito || saldoNegativo
        destino.saldoInicial = negativo ? -abs(valor) : abs(valor)
        destino.colorHex = colorHex
        try? context.save()
        dismiss()
    }
}

/// Grilla de colores de la marca más un selector libre.
struct SelectorColor: View {
    @Binding var colorHex: String

    private let columnas = [GridItem(.adaptive(minimum: 36), spacing: 12)]

    var body: some View {
        LazyVGrid(columns: columnas, spacing: 12) {
            ForEach(Marca.paleta, id: \.self) { hex in
                let elegido = hex.uppercased() == colorHex.uppercased()
                Button {
                    colorHex = hex
                } label: {
                    Circle()
                        .fill(Color(hex: hex))
                        .frame(width: 34, height: 34)
                        .overlay {
                            if elegido {
                                Image(systemName: "checkmark")
                                    .font(.caption.weight(.bold))
                                    .foregroundStyle(.white)
                            }
                        }
                        .overlay {
                            Circle().strokeBorder(Color.primary.opacity(elegido ? 0.5 : 0), lineWidth: 2)
                                .padding(-4)
                        }
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Color \(hex)")
            }
        }
        .padding(.vertical, 6)

        ColorPicker("Otro color", selection: Binding(
            get: { Color(hex: colorHex) },
            set: { colorHex = $0.hex }
        ), supportsOpacity: false)
    }
}
