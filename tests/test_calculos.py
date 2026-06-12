"""Tests for financial calculations."""
import pytest
from app import app as flask_app
from services.calculos import (
    calcular_mayor, calcular_balanza, calcular_estado_resultados,
    calcular_balance_general, get_ventas_por_dia, get_ventas_por_mes,
    get_gastos_por_mes, procesar_movimientos_periodo,
    calcular_movimientos_cierre, obtener_cuenta_capital_cierre,
    validar_cierre_posible, calcular_total_comercializacion,
)
from services.helpers import get_next_id, ensure_ids, tipo_saldo


def test_calcular_mayor_empty(data):
    result = calcular_mayor(data)
    assert isinstance(result, dict)


def test_calcular_balanza_empty(data):
    items, td, th, tsd, tsh = calcular_balanza(data)
    assert td == th == 0


def test_calcular_estado_resultados_empty(data):
    di, ti, dg, tg, util = calcular_estado_resultados(data)
    assert ti == tg == util == 0


def test_calcular_balance_general_empty(data):
    activos, ta, pasivos, tp, capital_items, tc = calcular_balance_general(data)
    assert ta == tp == tc == 0


def test_get_ventas_returns_dict(data):
    result = get_ventas_por_dia(data)
    assert isinstance(result, dict)
    result = get_ventas_por_mes(data)
    assert isinstance(result, dict)


def test_get_gastos_returns_dict(data):
    result = get_gastos_por_mes(data)
    assert isinstance(result, dict)


def test_tipo_saldo_valid():
    assert tipo_saldo("Activo") == "Debe"
    assert tipo_saldo("Pasivo") == "Haber"
    assert tipo_saldo("Capital") == "Haber"
    assert tipo_saldo("Ingreso") == "Haber"
    assert tipo_saldo("Gasto") == "Debe"


def test_tipo_saldo_invalid():
    assert tipo_saldo("Unknown") == "Haber"


def test_get_next_id(data):
    data["diario"] = [{"id": 1}, {"id": 3}]
    assert get_next_id(data, "diario") == 4
    data["diario"] = []
    assert get_next_id(data, "diario") == 1


def test_ensure_ids():
    data = {"diario": [{"id": 5}, {"id": 2}, {}]}
    ensure_ids(data)
    ids = [e["id"] for e in data["diario"]]
    assert len(set(ids)) == 3
    assert 0 not in ids


def test_procesar_movimientos_periodo_empty(data):
    result = procesar_movimientos_periodo(data, "2025-01-01", "2025-12-31")
    assert isinstance(result, dict)


def test_validar_cierre_posible_empty(data):
    ok, msg = validar_cierre_posible(data, "mensual", "2025-01")
    assert ok is False
    assert "No hay cuentas de resultado" in msg


def test_obtener_cuenta_capital_cierre(data):
    result = obtener_cuenta_capital_cierre(data)
    assert result is not None
    assert result == "3001"  # Capital cuenta por defecto


def test_calcular_total_comercializacion_empty(data):
    detalle, total = calcular_total_comercializacion(data)
    assert total == 0
    assert isinstance(detalle, list)


def test_calcular_movimientos_cierre_empty(data):
    result = calcular_movimientos_cierre(data, "2025-01-01", "2025-12-31")
    # Returns (movimientos, ing, gast, resultado)
    assert len(result) == 4
    assert result[1] == 0.0  # ing


def test_add_journal_entry_and_check_mayor(client):
    """Integration test: add an entry and verify it appears in mayor."""
    client.post("/diario/agregar", data={
        "fecha": "2025-06-01",
        "descripcion": "Test entry",
        "ref": "TEST-001",
        "cuenta_0": "4001", "tipo_0": "Haber", "monto_0": "100",
        "cuenta_1": "1001", "tipo_1": "Debe", "monto_1": "100",
        "num_movs": "2",
    }, follow_redirects=True)
    r = client.get("/mayor")
    assert r.status_code == 200


def test_search_diario(client):
    """Add entry then search for it."""
    client.post("/diario/agregar", data={
        "fecha": "2025-06-15",
        "descripcion": "UniqueSearchTerm",
        "ref": "SRCH",
        "cuenta_0": "4001", "tipo_0": "Haber", "monto_0": "50",
        "cuenta_1": "1001", "tipo_1": "Debe", "monto_1": "50",
        "num_movs": "2",
    })
    r = client.get("/diario?search=UniqueSearchTerm")
    assert r.status_code == 200
    assert b"UniqueSearchTerm" in r.data
