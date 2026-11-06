import SwiftUI
import UIKit

enum Marca {
    static let frutilla = Color(hex: "#E32B4A")
    static let rosa = Color(hex: "#FF7A8A")
    static let hoja = Color(hex: "#2FA85A")

    static let radio: CGFloat = 22

    static let degradado = LinearGradient(
        colors: [Color(hex: "#C81E3F"), frutilla, rosa],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    /// Colores para elegir en cuentas y categorías.
    static let paleta: [String] = [
        "#E32B4A", "#FF7A8A", "#F06292", "#AB47BC", "#7E57C2", "#5C6BC0",
        "#2196F3", "#00ACC1", "#26A69A", "#2FA85A", "#9CCC65", "#FFC107",
        "#FF9800", "#FF7043", "#8D6E63", "#90A4AE",
    ]

    static let fondo = Color(.systemGroupedBackground)
    static let superficie = Color(.secondarySystemGroupedBackground)
}

extension Color {
    init(hex: String) {
        let limpio = hex.trimmingCharacters(in: CharacterSet(charactersIn: "# "))
        var valor: UInt64 = 0
        Scanner(string: limpio).scanHexInt64(&valor)
        let r, g, b: Double
        if limpio.count == 6 {
            r = Double((valor >> 16) & 0xFF) / 255
            g = Double((valor >> 8) & 0xFF) / 255
            b = Double(valor & 0xFF) / 255
        } else {
            r = 0.6; g = 0.6; b = 0.6
        }
        self.init(.sRGB, red: r, green: g, blue: b, opacity: 1)
    }

    /// "#RRGGBB" para guardar en SwiftData.
    var hex: String {
        var r: CGFloat = 0, g: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
        UIColor(self).getRed(&r, green: &g, blue: &b, alpha: &a)
        func canal(_ v: CGFloat) -> Int { Int((min(max(v, 0), 1) * 255).rounded()) }
        return String(format: "#%02X%02X%02X", canal(r), canal(g), canal(b))
    }
}

extension Font {
    /// Tipografía redondeada para los montos grandes.
    static func monto(_ tamano: CGFloat, peso: Font.Weight = .bold) -> Font {
        .system(size: tamano, weight: peso, design: .rounded)
    }
}

extension Cuenta {
    var color: Color { Color(hex: colorHex) }
}

extension Categoria {
    var color: Color { Color(hex: colorHex) }
}

// MARK: Moneda en el entorno

private struct MonedaKey: EnvironmentKey {
    static let defaultValue: Moneda = .ARS
}

extension EnvironmentValues {
    var moneda: Moneda {
        get { self[MonedaKey.self] }
        set { self[MonedaKey.self] = newValue }
    }
}
