"""Tests for main application routes."""


def test_index_returns_200(client):
    r = client.get("/")
    assert r.status_code == 200


def test_diario_page(client):
    r = client.get("/diario")
    assert r.status_code == 200


def test_diario_with_search(client):
    r = client.get("/diario?search=test")
    assert r.status_code == 200


def test_diario_with_pagination(client):
    r = client.get("/diario?page=1")
    assert r.status_code == 200


def test_mayor_page(client):
    r = client.get("/mayor")
    assert r.status_code == 200


def test_balanza_page(client):
    r = client.get("/balanza")
    assert r.status_code == 200


def test_estado_resultados_page(client):
    r = client.get("/estado_resultados")
    assert r.status_code == 200


def test_balance_general_page(client):
    r = client.get("/balance_general")
    assert r.status_code == 200


def test_catalogar_page(client):
    r = client.get("/catalogar")
    assert r.status_code == 200


def test_cierre_mensual_page(client):
    r = client.get("/cierre-mensual")
    assert r.status_code == 200


def test_cierre_mensual_with_tipo(client):
    for tipo in ["mensual", "semanal", "quincenal"]:
        r = client.get(f"/cierre-mensual?tipo={tipo}")
        assert r.status_code == 200, f"tipo={tipo} returned {r.status_code}"


def test_cierre_vista_previa(client):
    r = client.get("/cierre-mensual/vista-previa/mensual/2025-01")
    assert r.status_code == 200


def test_caja_page(client):
    r = client.get("/caja")
    assert r.status_code == 200


def test_caja_with_pagination(client):
    r = client.get("/caja?page=1")
    assert r.status_code == 200


def test_cobrar_page(client):
    r = client.get("/cobrar")
    assert r.status_code == 200


def test_kardex_page(client):
    r = client.get("/kardex")
    assert r.status_code == 200


def test_ajustes_page(client):
    r = client.get("/ajustes")
    assert r.status_code == 200


def test_auxiliar_diario_page(client):
    r = client.get("/auxiliar-diario")
    assert r.status_code == 200


def test_pos_page(client):
    r = client.get("/pos")
    assert r.status_code == 200


def test_reportes_page(client):
    r = client.get("/reportes")
    assert r.status_code == 200


def test_comercializacion_page(client):
    r = client.get("/comercializacion")
    assert r.status_code == 200


def test_api_endpoints(client):
    apis = ["/api/ventas_dia", "/api/ventas_mes", "/api/gastos_mes"]
    for path in apis:
        r = client.get(path)
        assert r.status_code == 200, f"{path} returned {r.status_code}"
