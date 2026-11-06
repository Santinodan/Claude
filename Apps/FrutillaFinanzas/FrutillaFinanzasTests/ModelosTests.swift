import XCTest
import SwiftData
@testable import FrutillaFinanzas

@MainActor
final class ModelosTests: XCTestCase {
    var contenedor: ModelContainer!
    var context: ModelContext { contenedor.mainContext }

    override func setUp() async throws {
        contenedor = try ModelContainer(
            for: Cuenta.self, Movimiento.self, Categoria.self, Cuota.self, Suscripcion.self,
            configurations: ModelConfiguration(isStoredInMemoryOnly: true)
        )
    }

    private func movimiento(_ monto: Double, _ tipo: TipoMovimiento, cuenta: Cuenta, destino: Cuenta? = nil) -> Movimiento {
        let m = Movimiento(monto: monto, tipo: tipo)
        context.insert(m)
        m.cuenta = cuenta
        m.cuentaDestino = destino
        return m
    }

    func testSaldoConTransferencias() throws {
        let banco = Cuenta(nombre: "Banco", tipo: .banco, saldoInicial: 1000)
        let efectivo = Cuenta(nombre: "Efectivo")
        context.insert(banco)
        context.insert(efectivo)
        _ = movimiento(500, .ingreso, cuenta: banco)
        _ = movimiento(200, .gasto, cuenta: banco)
        _ = movimiento(300, .transferencia, cuenta: banco, destino: efectivo)
        try context.save()

        XCTAssertEqual(banco.saldo, 1000)
        XCTAssertEqual(efectivo.saldo, 300)
        XCTAssertEqual(efectivo.historial.count, 1)
    }

    func testTarjetaSeMuestraComoDeuda() throws {
        let visa = Cuenta(nombre: "Visa", tipo: .tarjetaCredito, saldoInicial: -1000)
        context.insert(visa)
        _ = movimiento(500, .gasto, cuenta: visa)
        try context.save()
        XCTAssertEqual(visa.deuda, 1500)

        let patrimonio = Finanzas.patrimonio(cuentas: [visa], cuotas: [])
        XCTAssertEqual(patrimonio.debes, 1500)
        XCTAssertEqual(patrimonio.neto, -1500)
    }

    func testBorrarCuentaBorraSusMovimientos() throws {
        let banco = Cuenta(nombre: "Banco")
        let otra = Cuenta(nombre: "Otra")
        context.insert(banco)
        context.insert(otra)
        _ = movimiento(100, .gasto, cuenta: banco)
        _ = movimiento(50, .transferencia, cuenta: otra, destino: banco)
        _ = movimiento(70, .gasto, cuenta: otra)
        try context.save()

        context.delete(banco)
        try context.save()

        let restantes = try context.fetch(FetchDescriptor<Movimiento>())
        XCTAssertEqual(restantes.count, 1)
        XCTAssertEqual(restantes.first?.monto, 70)
    }

    func testBorrarCategoriaDejaLosMovimientos() throws {
        let cuenta = Cuenta(nombre: "Efectivo")
        let comida = Categoria(nombre: "Comida", emoji: "🍔", colorHex: "#FF9800")
        context.insert(cuenta)
        context.insert(comida)
        let m = movimiento(100, .gasto, cuenta: cuenta)
        m.categoria = comida
        try context.save()

        context.delete(comida)
        try context.save()

        let restantes = try context.fetch(FetchDescriptor<Movimiento>())
        XCTAssertEqual(restantes.count, 1)
        XCTAssertNil(restantes.first?.categoria)
    }

    func testPagarCuotaYBorrarCuota() throws {
        DatosIniciales.crear(context)
        let cuenta = try XCTUnwrap(context.fetch(FetchDescriptor<Cuenta>()).first)
        let cuota = Cuota(nombre: "Heladera", valorCuota: 10000, cantidad: 12, primerVencimiento: .now)
        context.insert(cuota)
        cuota.cuenta = cuenta

        let pago = try XCTUnwrap(Acciones.pagarCuota(cuota, en: context))
        XCTAssertEqual(cuota.pagadas, 1)
        XCTAssertEqual(pago.categoria?.nombre, "Cuotas")
        XCTAssertEqual(cuenta.saldo, -10000)
        XCTAssertEqual(cuota.pendiente, 110000)

        context.delete(cuota)
        try context.save()
        XCTAssertEqual(try context.fetch(FetchDescriptor<Movimiento>()).count, 1)

        Acciones.borrar(pago, en: context)
        XCTAssertEqual(try context.fetchCount(FetchDescriptor<Movimiento>()), 0)
    }

    func testRegistrarCobroAvanzaLaFecha() throws {
        DatosIniciales.crear(context)
        let inicio = Fechas.calendario.date(from: DateComponents(year: 2026, month: 1, day: 31))!
        let sub = Suscripcion(nombre: "Netflix", emoji: "🎬", monto: 8000, frecuencia: .mensual, proximoCobro: inicio)
        context.insert(sub)

        let cobro = Acciones.registrarCobro(sub, en: context)
        XCTAssertEqual(cobro.categoria?.nombre, "Suscripciones")
        XCTAssertEqual(Fechas.calendario.component(.month, from: sub.proximoCobro), 2)
        XCTAssertTrue(sub.vencida == false || Fechas.diasDesdeHoy(sub.proximoCobro) < 0)
    }

    func testDatosInicialesCreaCategoriasYEfectivo() throws {
        DatosIniciales.crear(context)
        let categorias = try context.fetch(FetchDescriptor<Categoria>())
        XCTAssertEqual(categorias.filter { !$0.esIngreso }.count, 14)
        XCTAssertEqual(categorias.filter(\.esIngreso).count, 6)
        XCTAssertEqual(try context.fetch(FetchDescriptor<Cuenta>()).map(\.nombre), ["Efectivo"])
    }
}
