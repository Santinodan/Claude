import SwiftUI

// MARK: Tarjeta

struct EstiloTarjeta: ViewModifier {
    var relleno: CGFloat = 16

    func body(content: Content) -> some View {
        content
            .padding(relleno)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Marca.superficie, in: RoundedRectangle(cornerRadius: Marca.radio, style: .continuous))
    }
}

extension View {
    func tarjeta(relleno: CGFloat = 16) -> some View {
        modifier(EstiloTarjeta(relleno: relleno))
    }
}

struct TituloTarjeta: View {
    let titulo: String
    var simbolo: String? = nil

    var body: some View {
        HStack(spacing: 6) {
            if let simbolo {
                Image(systemName: simbolo).foregroundStyle(Marca.frutilla)
            }
            Text(titulo)
        }
        .font(.headline)
    }
}

// MARK: Círculos

struct CirculoEmoji: View {
    let emoji: String
    var color: Color = .gray
    var tamano: CGFloat = 40

    var body: some View {
        Text(emoji)
            .font(.system(size: tamano * 0.5))
            .frame(width: tamano, height: tamano)
            .background(color.opacity(0.18), in: Circle())
    }
}

struct IconoCuenta: View {
    let tipo: TipoCuenta
    let color: Color
    var tamano: CGFloat = 40

    var body: some View {
        Image(systemName: tipo.simbolo)
            .font(.system(size: tamano * 0.42, weight: .semibold))
            .foregroundStyle(.white)
            .frame(width: tamano, height: tamano)
            .background(color.gradient, in: RoundedRectangle(cornerRadius: tamano * 0.3, style: .continuous))
    }
}

// MARK: Montos

struct MontoTexto: View {
    @Environment(\.moneda) private var moneda
    let valor: Double
    var conSigno = false

    var body: some View {
        Text(moneda.formatear(valor, conSigno: conSigno))
            .monospacedDigit()
    }
}

/// Campo de monto grande del formulario de movimientos.
struct CampoMontoGrande: View {
    @Environment(\.moneda) private var moneda
    @Binding var texto: String
    var foco: FocusState<Bool>.Binding
    var color: Color = .primary

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 8) {
            Text(moneda.simbolo)
                .font(.monto(32, peso: .semibold))
                .foregroundStyle(.secondary)
            TextField("0", text: $texto)
                .font(.monto(52))
                .foregroundStyle(color)
                .keyboardType(.decimalPad)
                .focused(foco)
                .minimumScaleFactor(0.4)
                .lineLimit(1)
                .onChange(of: texto) { _, nuevo in
                    let formateado = Formato.formatearEntrada(nuevo)
                    if formateado != nuevo { texto = formateado }
                }
        }
        .frame(maxWidth: .infinity, alignment: .center)
        .padding(.vertical, 8)
    }
}

/// Fila de formulario con un monto chico ("Saldo inicial   $ 1.000").
struct CampoMonto: View {
    @Environment(\.moneda) private var moneda
    let titulo: String
    @Binding var texto: String

    var body: some View {
        HStack {
            Text(titulo)
            Spacer()
            Text(moneda.simbolo).foregroundStyle(.secondary)
            TextField("0", text: $texto)
                .keyboardType(.decimalPad)
                .multilineTextAlignment(.trailing)
                .font(.monto(17, peso: .semibold))
                .frame(maxWidth: 160)
                .onChange(of: texto) { _, nuevo in
                    let formateado = Formato.formatearEntrada(nuevo)
                    if formateado != nuevo { texto = formateado }
                }
        }
    }
}

// MARK: Progreso

struct BarraProgreso: View {
    let valor: Double
    var color: Color = Marca.frutilla
    var alto: CGFloat = 10

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                Capsule().fill(color.opacity(0.15))
                Capsule()
                    .fill(color.gradient)
                    .frame(width: max(alto, geo.size.width * min(max(valor, 0), 1)))
                    .opacity(valor > 0 ? 1 : 0)
            }
        }
        .frame(height: alto)
        .animation(.spring(duration: 0.4), value: valor)
    }
}

// MARK: Chips

struct Chip: View {
    let titulo: String
    var activo: Bool
    var accion: () -> Void

    var body: some View {
        Button(action: accion) {
            Text(titulo)
                .font(.subheadline.weight(.semibold))
                .padding(.horizontal, 14)
                .padding(.vertical, 8)
                .foregroundStyle(activo ? Color.white : Color.primary)
                .background(activo ? AnyShapeStyle(Marca.frutilla) : AnyShapeStyle(Marca.superficie), in: Capsule())
        }
        .buttonStyle(.plain)
    }
}

// MARK: Botón flotante "+"

struct BotonAgregar: ViewModifier {
    @State private var mostrarFormulario = false

    func body(content: Content) -> some View {
        content
            .overlay(alignment: .bottomTrailing) {
                Button {
                    mostrarFormulario = true
                } label: {
                    Image(systemName: "plus")
                        .font(.system(size: 26, weight: .bold))
                        .foregroundStyle(.white)
                        .frame(width: 60, height: 60)
                        .background(Marca.degradado, in: Circle())
                        .shadow(color: Marca.frutilla.opacity(0.4), radius: 10, y: 5)
                }
                .padding(.trailing, 20)
                .padding(.bottom, 16)
                .accessibilityLabel("Cargar movimiento")
            }
            .sheet(isPresented: $mostrarFormulario) {
                MovimientoFormView()
            }
    }
}

extension View {
    func botonAgregar() -> some View {
        modifier(BotonAgregar())
    }
}
