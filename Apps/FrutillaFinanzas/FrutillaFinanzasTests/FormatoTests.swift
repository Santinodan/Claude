import XCTest
@testable import FrutillaFinanzas

final class FormatoTests: XCTestCase {

    func testParsearFormatosAceptados() {
        XCTAssertEqual(Formato.parsear("12500"), 12500)
        XCTAssertEqual(Formato.parsear("12.500"), 12500)
        XCTAssertEqual(Formato.parsear("12.500,50"), 12500.5)
        XCTAssertEqual(Formato.parsear("$ 1.234.567,89"), 1234567.89)
        XCTAssertEqual(Formato.parsear("12,5"), 12.5)
        XCTAssertNil(Formato.parsear(""))
        XCTAssertNil(Formato.parsear("abc"))
    }

    func testMostrarMontos() {
        XCTAssertEqual(Formato.dinero(12500), "$ 12.500")
        XCTAssertEqual(Formato.dinero(12500.5), "$ 12.500,50")
        XCTAssertEqual(Formato.dinero(-1500), "-$ 1.500")
        XCTAssertEqual(Formato.dinero(300, moneda: .USD, conSigno: true), "+US$ 300")
        XCTAssertEqual(Formato.numeroPlano(12500.5), "12500,50")
    }

    func testFormateoMientrasSeTipea() {
        var texto = ""
        for c in "12500,507" { texto = Formato.formatearEntrada(texto + String(c)) }
        XCTAssertEqual(texto, "12.500,50")
        XCTAssertEqual(Formato.formatearEntrada("12.50"), "1.250")
        XCTAssertEqual(Formato.formatearEntrada("12."), "12,")
        XCTAssertEqual(Formato.formatearEntrada("007"), "7")
    }
}
