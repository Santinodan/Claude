import SwiftUI
import SwiftData

struct PlantillaSuscripcion: Identifiable, Hashable {
    let nombre: String
    let emoji: String
    var frecuencia: Frecuencia = .mensual
    var id: String { nombre }

    static let sugerencias: [PlantillaSuscripcion] = [
        .init(nombre: "Netflix", emoji: "🎬"),
        .init(nombre: "Spotify", emoji: "🎧"),
        .init(nombre: "YouTube Premium", emoji: "▶️"),
        .init(nombre: "Disney+", emoji: "🏰"),
        .init(nombre: "iCloud", emoji: "☁️"),
        .init(nombre: "Gimnasio", emoji: "🏋️"),
        .init(nombre: "Internet", emoji: "🌐"),
        .init(nombre: "Celular", emoji: "📱"),
    ]
}

enum FormularioSuscripcion: Identifiable {
    case nueva(PlantillaSuscripcion?)
    case editar(Suscripcion)

    var id: String {
        switch self {
        case .nueva(let plantilla): "nueva-\(plantilla?.nombre ?? "")"
        case .editar(let s): "editar-\(s.persistentModelID.hashValue)"
        }
    }
}

struct ListaSuscripciones: View {
    let suscripciones: [Suscripcion]
    @Binding var formulario: FormularioSuscripcion?

    private var activas: [Suscripcion] { suscripciones.filter(\.activa) }
    private var pausadas: [Suscripcion] { suscripciones.filter { !$0.activa } }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Agregá rápido")
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.secondary)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(PlantillaSuscripcion.sugerencias) { plantilla in
                        Button {
                            formulario = .nueva(plantilla)
                        } label: {
                            Text("\(plantilla.emoji) \(plantilla.nombre)")
                                .font(.subheadline.weight(.medium))
                                .padding(.horizontal, 12)
                                .padding(.vertical, 8)
                                .background(Marca.superficie, in: Capsule())
                        }
                        .buttonStyle(.plain)
                    }
                    Button {
                        formulario = .nueva(nil)
                    } label: {
                        Label("Otra", systemImage: "plus")
                            .font(.subheadline.weight(.semibold))
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                            .foregroundStyle(.white)
                            .background(Marca.frutilla, in: Capsule())
                    }
                    .buttonStyle(.plain)
                }
            }
            .scrollClipDisabled()
        }

        if suscripciones.isEmpty {
            VStack(spacing: 10) {
                Text("📺").font(.system(size: 44))
                Text("Sin suscripciones")
                    .font(.headline)
                Text("Tocá una sugerencia de arriba o cargá la tuya. Te avisamos antes de cada cobro.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
            .padding(.vertical, 12)
            .tarjeta()
        } else {
            if !activas.isEmpty {
                VStack(spacing: 0) {
                    ForEach(activas) { sub in
                        SuscripcionFila(suscripcion: sub) { formulario = .editar(sub) }
                        if sub.id != activas.last?.id { Divider().padding(.leading, 54) }
                    }
                }
                .tarjeta(relleno: 14)
            }
            if !pausadas.isEmpty {
                Text("Pausadas")
                    .font(.headline)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.top, 8)
                VStack(spacing: 0) {
                    ForEach(pausadas) { sub in
                        SuscripcionFila(suscripcion: sub) { formulario = .editar(sub) }
                        if sub.id != pausadas.last?.id { Divider().padding(.leading, 54) }
                    }
                }
                .tarjeta(relleno: 14)
                .opacity(0.7)
            }
        }
    }
}

struct SuscripcionFila: View {
    @Environment(\.modelContext) private var context
    let suscripcion: Suscripcion
    var editar: () -> Void
    @State private var cobros = 0

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Button(action: editar) {
                HStack(spacing: 12) {
                    CirculoEmoji(emoji: suscripcion.emoji, color: suscripcion.categoria?.color ?? Marca.rosa, tamano: 42)
                    VStack(alignment: .leading, spacing: 3) {
                        HStack(spacing: 6) {
                            Text(suscripcion.nombre)
                                .font(.subheadline.weight(.semibold))
                                .lineLimit(1)
                            if suscripcion.vencida {
                                Text("Vencida")
                                    .font(.caption2.weight(.bold))
                                    .foregroundStyle(.white)
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(Marca.frutilla, in: Capsule())
                            }
                        }
                        Text(detalle)
                            .font(.caption)
                            .foregroundStyle(suscripcion.vencida ? Marca.frutilla : Color.secondary)
                    }
                    Spacer()
                    VStack(alignment: .trailing, spacing: 2) {
                        MontoTexto(valor: suscripcion.monto)
                            .font(.monto(16, peso: .semibold))
                        Text(suscripcion.frecuencia.sufijo)
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)

            if suscripcion.activa {
                Button {
                    withAnimation {
                        Acciones.registrarCobro(suscripcion, en: context)
                        cobros += 1
                    }
                } label: {
                    Label("Registrar cobro", systemImage: "checkmark.circle")
                        .font(.footnote.weight(.semibold))
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .tint(suscripcion.vencida ? Marca.frutilla : Color.secondary)
                .padding(.leading, 54)
            }
        }
        .padding(.vertical, 8)
        .sensoryFeedback(.success, trigger: cobros)
    }

    private var detalle: String {
        guard suscripcion.activa else { return "Pausada · \(suscripcion.frecuencia.nombre)" }
        let fecha = Fechas.corta(suscripcion.proximoCobro)
        if suscripcion.vencida { return "Se cobraba el \(fecha)" }
        return "Próximo cobro: \(fecha) · \(Fechas.relativa(suscripcion.proximoCobro))"
    }
}

// MARK: Formulario

struct SuscripcionFormView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var context
    @Query(sort: \Cuenta.orden) private var cuentas: [Cuenta]
    @Query(filter: #Predicate<Categoria> { $0.esIngreso == false }, sort: \Categoria.orden) private var categorias: [Categoria]

    private let suscripcion: Suscripcion?

    @State private var nombre: String
    @State private var emoji: String
    @State private var montoTexto: String
    @State private var frecuencia: Frecuencia
    @State private var proximoCobro: Date
    @State private var diasAviso: Int
    @State private var activa: Bool
    @State private var cuenta: Cuenta?
    @State private var categoria: Categoria?
    @State private var confirmarBorrado = false

    init(suscripcion: Suscripcion? = nil, plantilla: PlantillaSuscripcion? = nil) {
        self.suscripcion = suscripcion
        _nombre = State(initialValue: suscripcion?.nombre ?? plantilla?.nombre ?? "")
        _emoji = State(initialValue: suscripcion?.emoji ?? plantilla?.emoji ?? "📺")
        _montoTexto = State(initialValue: suscripcion.map { Formato.numero($0.monto) } ?? "")
        _frecuencia = State(initialValue: suscripcion?.frecuencia ?? plantilla?.frecuencia ?? .mensual)
        _proximoCobro = State(initialValue: suscripcion?.proximoCobro ?? .now)
        _diasAviso = State(initialValue: suscripcion?.diasAviso ?? 1)
        _activa = State(initialValue: suscripcion?.activa ?? true)
        _cuenta = State(initialValue: suscripcion?.cuenta)
        _categoria = State(initialValue: suscripcion?.categoria)
    }

    private var monto: Double { Formato.parsear(montoTexto) ?? 0 }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    HStack(spacing: 12) {
                        TextField("📺", text: $emoji)
                            .font(.system(size: 30))
                            .multilineTextAlignment(.center)
                            .frame(width: 56, height: 56)
                            .background(Marca.rosa.opacity(0.2), in: Circle())
                            .onChange(of: emoji) { _, nuevo in
                                if nuevo.count > 1, let ultimo = nuevo.last { emoji = String(ultimo) }
                            }
                        TextField("Nombre (ej. Netflix)", text: $nombre)
                            .font(.headline)
                    }
                }

                Section {
                    CampoMonto(titulo: "Monto", texto: $montoTexto)
                    Picker("Frecuencia", selection: $frecuencia) {
                        ForEach(Frecuencia.allCases) { f in
                            Text(f.nombre).tag(f)
                        }
                    }
                    DatePicker("Próximo cobro", selection: $proximoCobro, displayedComponents: .date)
                    Stepper(value: $diasAviso, in: 0...15) {
                        Text(diasAviso == 0 ? "Avisarme el mismo día" : "Avisarme \(diasAviso) \(diasAviso == 1 ? "día" : "días") antes")
                    }
                    Toggle("Activa", isOn: $activa)
                }

                Section {
                    Picker("Cuenta", selection: $cuenta) {
                        Text("Cuenta principal").tag(Cuenta?.none)
                        ForEach(cuentas) { c in
                            Text(c.nombre).tag(Cuenta?.some(c))
                        }
                    }
                    Picker("Categoría", selection: $categoria) {
                        Text("Sin categoría").tag(Categoria?.none)
                        ForEach(categorias) { c in
                            Text("\(c.emoji) \(c.nombre)").tag(Categoria?.some(c))
                        }
                    }
                } footer: {
                    Text("Con \"Registrar cobro\" se carga el gasto en esta cuenta y la fecha pasa al próximo cobro.")
                }

                if suscripcion != nil {
                    Section {
                        Button("Eliminar suscripción", role: .destructive) { confirmarBorrado = true }
                            .frame(maxWidth: .infinity)
                    } footer: {
                        Text("Los cobros que ya registraste quedan en tus movimientos.")
                    }
                }
            }
            .navigationTitle(suscripcion == nil ? "Nueva suscripción" : "Editar suscripción")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancelar") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Guardar") { guardar() }
                        .fontWeight(.semibold)
                        .disabled(nombre.recortado.isEmpty || monto <= 0)
                }
            }
            .onAppear {
                if suscripcion == nil, categoria == nil {
                    categoria = categorias.first { $0.nombre == "Suscripciones" }
                }
            }
            .confirmationDialog("¿Eliminar esta suscripción?", isPresented: $confirmarBorrado, titleVisibility: .visible) {
                Button("Eliminar", role: .destructive) {
                    if let suscripcion {
                        context.delete(suscripcion)
                        Acciones.guardar(context)
                    }
                    dismiss()
                }
            }
        }
    }

    private func guardar() {
        let destino: Suscripcion
        if let suscripcion {
            destino = suscripcion
        } else {
            destino = Suscripcion(nombre: "", emoji: "📺", monto: 0, proximoCobro: .now)
            context.insert(destino)
        }
        destino.nombre = nombre.recortado
        destino.emoji = emoji.isEmpty ? "📺" : emoji
        destino.monto = monto
        destino.frecuencia = frecuencia
        destino.proximoCobro = proximoCobro
        destino.diasAviso = diasAviso
        destino.activa = activa
        destino.cuenta = cuenta
        destino.categoria = categoria
        Acciones.guardar(context)
        dismiss()
    }
}
