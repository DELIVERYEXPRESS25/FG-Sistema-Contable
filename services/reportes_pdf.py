from io import BytesIO
from datetime import date
from fpdf import FPDF


class ReportePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(79, 140, 255)
        self.cell(0, 6, "F & G - Sistema Contable", align="L")
        self.set_font("Helvetica", "", 7)
        self.set_text_color(122, 127, 153)
        self.cell(0, 6, date.today().isoformat(), align="R", new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(122, 127, 153)
        self.cell(0, 10, f"P\xe1gina {self.page_no()}/{{nb}}", align="C")

    def titulo(self, text):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(15, 17, 23)
        self.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def subtitulo(self, text):
        if not text:
            return
        self.set_font("Helvetica", "", 9)
        self.set_text_color(122, 127, 153)
        self.cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    @staticmethod
    def celda_monto(monto):
        return f"C${'{:,.2f}'.format(monto)}"

    def encabezado_tabla(self, headers, widths):
        self.set_fill_color(26, 29, 46)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 8)
        for i, h in enumerate(headers):
            self.cell(widths[i], 7, h, border=1, fill=True, align="C")
        self.ln()

    def fila_tabla(self, data, widths, align=None, bold=False):
        self.set_text_color(45, 45, 63)
        self.set_font("Helvetica", "B" if bold else "", 8)
        if align is None:
            align = ["L"] * len(data)
        for i, d in enumerate(data):
            self.cell(widths[i], 6, str(d), border=1, align=align[i])
        self.ln()

    def portada(self, titulo_reporte, periodo=""):
        self.add_page()
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(79, 140, 255)
        self.ln(40)
        self.cell(0, 12, "F & G - Sistema Contable", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(8)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(15, 17, 23)
        self.cell(0, 10, titulo_reporte, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(6)
        self.set_font("Helvetica", "", 11)
        self.set_text_color(122, 127, 153)
        if periodo:
            self.cell(0, 8, periodo, align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 8, f"Generado: {date.today().isoformat()}", align="C", new_x="LMARGIN", new_y="NEXT")


def _filtrar_por_periodo(data, desde, hasta):
    import copy
    d = copy.deepcopy(data)
    if desde and hasta:
        d["diario"] = [e for e in d.get("diario", []) if desde <= e.get("fecha", "") <= hasta]
        d["ajustes"] = [a for a in d.get("ajustes", []) if desde <= a.get("fecha", "") <= hasta]
    return d


def _cargar_data(data, desde=None, hasta=None):
    from services.calculos import (
        calcular_mayor, calcular_balanza, calcular_estado_resultados,
        calcular_balance_general,
    )
    filtrada = _filtrar_por_periodo(data, desde, hasta) if desde or hasta else data
    mayor = calcular_mayor(filtrada)
    cuentas = data["cuentas"]
    balanza, td, th, tsd, tsh = calcular_balanza(filtrada)
    er_detalle_ing, er_total_ing, er_detalle_gas, er_total_gas, er_util = calcular_estado_resultados(filtrada)
    bg_activos, bg_ta, bg_pasivos, bg_tp, bg_capital, bg_tc = calcular_balance_general(filtrada)
    return {
        "mayor": mayor, "cuentas": cuentas,
        "balanza": balanza,
        "balanza_td": td, "balanza_th": th, "balanza_tsd": tsd, "balanza_tsh": tsh,
        "er_detalle_ing": er_detalle_ing, "er_total_ing": er_total_ing,
        "er_detalle_gas": er_detalle_gas, "er_total_gas": er_total_gas, "er_util": er_util,
        "bg_activos": bg_activos, "bg_ta": bg_ta,
        "bg_pasivos": bg_pasivos, "bg_tp": bg_tp,
        "bg_capital": bg_capital, "bg_tc": bg_tc,
    }


def _periodo_str(desde, hasta):
    if desde and hasta:
        return f"Periodo: {desde} al {hasta}"
    return ""


def _init_pdf(pdf=None):
    if pdf is None:
        p = ReportePDF()
        p.alias_nb_pages()
        p.add_page()
        return p
    return pdf


# ── Reportes principales ──────────────────────────────

def pdf_balanza(data, desde=None, hasta=None, pdf=None):
    c = _cargar_data(data, desde, hasta)
    p = _init_pdf(pdf)
    p.titulo("Balanza de Comprobacion")
    p.subtitulo("Verificacion de debitos y creditos")
    p.subtitulo(_periodo_str(desde, hasta))
    headers = ["Codigo", "Cuenta", "Debe", "Haber", "Saldo Debe", "Saldo Haber"]
    widths = [18, 60, 28, 28, 28, 28]
    p.encabezado_tabla(headers, widths)
    for item in c["balanza"]:
        p.fila_tabla([
            item["codigo"], item["nombre"][:35],
            p.celda_monto(item["debe"]), p.celda_monto(item["haber"]),
            p.celda_monto(item["saldo_debe"]), p.celda_monto(item["saldo_haber"]),
        ], widths, align=["L", "L", "R", "R", "R", "R"])
        if p.get_y() > 260:
            p.add_page()
            p.encabezado_tabla(headers, widths)
    p.fila_tabla(["", "TOTALES",
        p.celda_monto(c["balanza_td"]), p.celda_monto(c["balanza_th"]),
        p.celda_monto(c["balanza_tsd"]), p.celda_monto(c["balanza_tsh"])],
        widths, align=["L", "L", "R", "R", "R", "R"], bold=True)
    if pdf is None:
        return p


def pdf_estado_resultados(data, desde=None, hasta=None, pdf=None):
    c = _cargar_data(data, desde, hasta)
    p = _init_pdf(pdf)
    p.titulo("Estado de Resultados")
    p.subtitulo("Ingresos, Gastos y Utilidad Neta")
    p.subtitulo(_periodo_str(desde, hasta))
    w = [80, 40]
    p.set_font("Helvetica", "B", 9)
    p.set_text_color(46, 204, 113)
    p.cell(0, 7, "INGRESOS", new_x="LMARGIN", new_y="NEXT")
    for item in c["er_detalle_ing"]:
        p.set_text_color(45, 45, 63)
        p.set_font("Helvetica", "", 8)
        p.cell(w[0], 6, item["nombre"][:40])
        p.cell(w[1], 6, p.celda_monto(item["monto"]), align="R", new_x="LMARGIN", new_y="NEXT")
    p.set_font("Helvetica", "B", 8)
    p.set_text_color(46, 204, 113)
    p.cell(w[0], 6, "Total Ingresos")
    p.cell(w[1], 6, p.celda_monto(c["er_total_ing"]), align="R", new_x="LMARGIN", new_y="NEXT")
    p.ln(4)
    p.set_font("Helvetica", "B", 9)
    p.set_text_color(231, 76, 60)
    p.cell(0, 7, "GASTOS", new_x="LMARGIN", new_y="NEXT")
    for item in c["er_detalle_gas"]:
        p.set_text_color(45, 45, 63)
        p.set_font("Helvetica", "", 8)
        p.cell(w[0], 6, item["nombre"][:40])
        p.cell(w[1], 6, p.celda_monto(item["monto"]), align="R", new_x="LMARGIN", new_y="NEXT")
    p.set_font("Helvetica", "B", 8)
    p.set_text_color(231, 76, 60)
    p.cell(w[0], 6, "Total Gastos")
    p.cell(w[1], 6, p.celda_monto(c["er_total_gas"]), align="R", new_x="LMARGIN", new_y="NEXT")
    p.ln(6)
    p.set_font("Helvetica", "B", 11)
    color = (46, 204, 113) if c["er_util"] >= 0 else (231, 76, 60)
    p.set_text_color(*color)
    p.cell(0, 8, f"UTILIDAD NETA: {p.celda_monto(c['er_util'])}", new_x="LMARGIN", new_y="NEXT")
    if pdf is None:
        return p


def pdf_balance_general(data, desde=None, hasta=None, pdf=None):
    c = _cargar_data(data, desde, hasta)
    p = _init_pdf(pdf)
    p.titulo("Balance General")
    p.subtitulo("Activos = Pasivos + Capital")
    p.subtitulo(_periodo_str(desde, hasta))
    w = [80, 40]
    def seccion(nombre, items, total, color_sel):
        p.set_font("Helvetica", "B", 9)
        p.set_text_color(*color_sel)
        p.cell(0, 7, nombre, new_x="LMARGIN", new_y="NEXT")
        for item in items:
            p.set_text_color(45, 45, 63)
            p.set_font("Helvetica", "", 8)
            p.cell(w[0], 6, item["nombre"][:40])
            p.cell(w[1], 6, p.celda_monto(item["saldo"]), align="R", new_x="LMARGIN", new_y="NEXT")
        p.set_font("Helvetica", "B", 8)
        p.set_text_color(*color_sel)
        p.cell(w[0], 6, f"Total {nombre}")
        p.cell(w[1], 6, p.celda_monto(total), align="R", new_x="LMARGIN", new_y="NEXT")
        p.ln(4)
    seccion("ACTIVOS", c["bg_activos"], c["bg_ta"], (79, 140, 255))
    seccion("PASIVOS", c["bg_pasivos"], c["bg_tp"], (231, 76, 60))
    seccion("CAPITAL", c["bg_capital"], c["bg_tc"], (46, 204, 113))
    p.set_font("Helvetica", "B", 9)
    p.set_text_color(79, 140, 255)
    p.cell(0, 7, f"VERIFICACION: Pasivos + Capital = {p.celda_monto(c['bg_tp'] + c['bg_tc'])}",
             new_x="LMARGIN", new_y="NEXT")
    if pdf is None:
        return p


def pdf_diario(data, desde=None, hasta=None, pdf=None):
    filtrada = _filtrar_por_periodo(data, desde, hasta) if desde or hasta else data
    c = _cargar_data(data, desde, hasta)
    p = _init_pdf(pdf)
    p.titulo("Libro Diario")
    p.subtitulo("Registro cronologico de asientos")
    p.subtitulo(_periodo_str(desde, hasta))
    headers = ["#", "Fecha", "Descripcion", "Cuenta", "Debe", "Haber"]
    widths = [8, 18, 50, 36, 28, 28]
    p.encabezado_tabla(headers, widths)
    for entry in filtrada.get("diario", []):
        if p.get_y() > 250:
            p.add_page()
            p.encabezado_tabla(headers, widths)
        first = True
        for mov in entry["movimientos"]:
            if first:
                p.set_font("Helvetica", "B", 7)
                p.set_text_color(15, 17, 23)
                p.cell(widths[0], 5, str(entry.get("id", "")))
                p.set_font("Helvetica", "", 7)
                p.cell(widths[1], 5, entry.get("fecha", ""))
                p.cell(widths[2], 5, entry.get("descripcion", "")[:35])
                first = False
            else:
                p.cell(widths[0] + widths[1] + widths[2], 5, "")
            p.set_text_color(45, 45, 63)
            p.cell(widths[3], 5, f"{mov['cuenta']} {c['cuentas'].get(mov['cuenta'], {}).get('nombre', '')[:20]}")
            debe = p.celda_monto(mov["monto"]) if mov["tipo"] == "Debe" else ""
            haber = p.celda_monto(mov["monto"]) if mov["tipo"] == "Haber" else ""
            p.cell(widths[4], 5, debe, align="R")
            p.cell(widths[5], 5, haber, align="R", new_x="LMARGIN", new_y="NEXT")
    if pdf is None:
        return p


def pdf_mayor(data, desde=None, hasta=None, pdf=None):
    c = _cargar_data(data, desde, hasta)
    p = _init_pdf(pdf)
    p.titulo("Libro Mayor")
    p.subtitulo("Cuentas T - Movimientos por cuenta")
    p.subtitulo(_periodo_str(desde, hasta))
    w = [18, 50, 16, 28, 28, 28]
    for codigo in sorted(c["cuentas"].keys()):
        info = c["cuentas"][codigo]
        debe = c["mayor"][codigo]["debe"] if codigo in c["mayor"] else 0
        haber = c["mayor"][codigo]["haber"] if codigo in c["mayor"] else 0
        from services.helpers import tipo_saldo
        ts = tipo_saldo(info["tipo"])
        saldo = (debe - haber) if ts == "Debe" else (haber - debe)
        if p.get_y() > 260:
            p.add_page()
        p.set_font("Helvetica", "B", 8)
        p.set_text_color(15, 17, 23)
        p.cell(w[0] + w[1] + w[2], 6,
                 f"{codigo} - {info['nombre'][:35]} ({info['tipo']})",
                 new_x="LMARGIN", new_y="NEXT")
        p.encabezado_tabla(["Cuenta", "Nombre", "Tipo", "Debe", "Haber", "Saldo"], w)
        p.fila_tabla([
            codigo, info["nombre"][:35], info["tipo"],
            p.celda_monto(debe), p.celda_monto(haber), p.celda_monto(saldo),
        ], w, align=["L", "L", "C", "R", "R", "R"])
        p.ln(3)
    if pdf is None:
        return p


# ── Reportes adicionales ──────────────────────────────

def pdf_cobrar(data, desde=None, hasta=None, pdf=None):
    p = _init_pdf(pdf)
    p.titulo("Cuentas por Cobrar")
    p.subtitulo("Pendientes de pago")
    p.subtitulo(_periodo_str(desde, hasta))
    cobros = data.get("cuentas_cobrar", [])
    if desde and hasta:
        cobros = [c for c in cobros if desde <= c.get("fecha", "") <= hasta]
    if not cobros:
        p.set_font("Helvetica", "", 10)
        p.set_text_color(122, 127, 153)
        p.cell(0, 10, "No hay cuentas por cobrar en este periodo.", new_x="LMARGIN", new_y="NEXT")
        if pdf is None:
            return p
        return
    headers = ["#", "Fecha", "Descripcion", "Monto C$", "Pagado C$", "Saldo C$", "Estado"]
    widths = [8, 18, 50, 28, 28, 28, 20]
    p.encabezado_tabla(headers, widths)
    for c in cobros:
        saldo = c["monto"] - sum(pg.get("monto", 0) for pg in c.get("pagos", []))
        p.fila_tabla([
            str(c.get("id", "")), c.get("fecha", ""), c.get("descripcion", "")[:35],
            p.celda_monto(c["monto"]), p.celda_monto(c["monto"] - saldo),
            p.celda_monto(saldo), c.get("estado", "pendiente"),
        ], widths, align=["C", "C", "L", "R", "R", "R", "C"])
        if p.get_y() > 260:
            p.add_page()
            p.encabezado_tabla(headers, widths)
    if pdf is None:
        return p


def pdf_caja(data, desde=None, hasta=None, pdf=None):
    p = _init_pdf(pdf)
    p.titulo("Movimientos de Caja")
    p.subtitulo("Registro de ingresos y egresos")
    p.subtitulo(_periodo_str(desde, hasta))
    movs = data.get("caja_movimientos", [])
    if desde and hasta:
        movs = [m for m in movs if desde <= m.get("fecha", "") <= hasta]
    if not movs:
        p.set_font("Helvetica", "", 10)
        p.set_text_color(122, 127, 153)
        p.cell(0, 10, "No hay movimientos de caja en este periodo.", new_x="LMARGIN", new_y="NEXT")
        if pdf is None:
            return p
        return
    headers = ["Fecha", "Descripcion", "Tipo", "Monto C$"]
    widths = [22, 70, 30, 40]
    p.encabezado_tabla(headers, widths)
    for m in movs:
        p.fila_tabla([
            m.get("fecha", ""), m.get("descripcion", "")[:50],
            m.get("tipo", ""), p.celda_monto(m.get("monto", 0)),
        ], widths, align=["C", "L", "C", "R"])
        if p.get_y() > 260:
            p.add_page()
            p.encabezado_tabla(headers, widths)
    if pdf is None:
        return p


def pdf_antiguedad_cobros(data, desde=None, hasta=None, pdf=None):
    p = _init_pdf(pdf)
    p.titulo("Antiguedad de Cuentas por Cobrar")
    p.subtitulo("Saldos pendientes por rango de vencimiento")
    from datetime import date, timedelta
    hoy = date.today()
    cobros = data.get("cuentas_cobrar", [])
    activos = [c for c in cobros if c.get("estado", "pendiente") != "pagado"]
    if not activos:
        p.set_font("Helvetica", "", 10)
        p.set_text_color(122, 127, 153)
        p.cell(0, 10, "No hay cuentas por cobrar pendientes.", new_x="LMARGIN", new_y="NEXT")
        if pdf is None:
            return p
        return
    rangos = [
        ("0-30 dias",      lambda d, h: 0 <= (hoy - _parse_fecha(d)).days <= 30),
        ("31-60 dias",     lambda d, h: 31 <= (hoy - _parse_fecha(d)).days <= 60),
        ("61-90 dias",     lambda d, h: 61 <= (hoy - _parse_fecha(d)).days <= 90),
        ("91+ dias",       lambda d, h: (hoy - _parse_fecha(d)).days > 90),
    ]
    headers = ["Rango", "Cantidad", "Total C$"]
    widths = [60, 40, 60]
    p.encabezado_tabla(headers, widths)
    gran_total = 0
    for label, cond in rangos:
        items = [c for c in activos if cond(c.get("fecha", ""), hoy)]
        if not items:
            continue
        total_rango = sum(c["monto"] - sum(pg.get("monto", 0) for pg in c.get("pagos", [])) for c in items)
        gran_total += total_rango
        p.fila_tabla([label, str(len(items)), p.celda_monto(total_rango)], widths, align=["L", "C", "R"])
    p.fila_tabla(["TOTAL", str(len(activos)), p.celda_monto(gran_total)], widths, align=["L", "C", "R"], bold=True)
    p.ln(6)
    p.subtitulo("Detalle de cuentas pendientes")
    dh = ["#", "Fecha", "Descripcion", "Monto C$", "Saldo C$", "Dias"]
    dw = [10, 18, 50, 30, 30, 18]
    p.encabezado_tabla(dh, dw)
    for c in activos:
        saldo = c["monto"] - sum(pg.get("monto", 0) for pg in c.get("pagos", []))
        dias = (hoy - _parse_fecha(c.get("fecha", ""))).days
        p.fila_tabla([
            str(c.get("id", "")), c.get("fecha", ""), c.get("descripcion", "")[:35],
            p.celda_monto(c["monto"]), p.celda_monto(saldo), str(dias),
        ], dw, align=["C", "C", "L", "R", "R", "C"])
        if p.get_y() > 260:
            p.add_page()
            p.encabezado_tabla(dh, dw)
    if pdf is None:
        return p


def _parse_fecha(f):
    from datetime import date
    try:
        return date.fromisoformat(f)
    except (ValueError, TypeError):
        return date.today()


# ── Reporte completo (todos en un PDF) ──────────────

def pdf_completo(data, desde=None, hasta=None):
    p = ReportePDF()
    p.alias_nb_pages()
    periodo = _periodo_str(desde, hasta) or "Todos los periodos"
    p.portada("Reporte Completo", periodo)
    for fn in [pdf_balanza, pdf_estado_resultados, pdf_balance_general,
               pdf_diario, pdf_mayor, pdf_cobrar, pdf_caja, pdf_antiguedad_cobros]:
        fn(data, desde, hasta, pdf=p)
    return p


# ── Reporte IVA (genera su propio periodo) ──────────

def pdf_reporte_iva(data, desde, hasta):
    p = ReportePDF()
    p.alias_nb_pages()
    p.add_page()
    p.titulo("Reporte de IVA")
    p.subtitulo(f"Periodo: {desde} al {hasta}")
    from services.calculos import procesar_movimientos_periodo
    saldos = procesar_movimientos_periodo(data, desde, hasta, excluir_cierre=True)
    cuentas = data["cuentas"]
    total_ingresos = 0
    total_gastos = 0
    for cod, info in cuentas.items():
        sd = saldos.get(cod, {"debe": 0, "haber": 0})
        if info.get("tipo") == "Ingreso":
            total_ingresos += sd["haber"] - sd["debe"]
        elif info.get("tipo") == "Gasto":
            total_gastos += sd["debe"] - sd["haber"]
    iva_tasa = 0.15
    iva_debitado = total_ingresos * iva_tasa
    iva_creditado = total_gastos * iva_tasa
    iva_pagar = iva_debitado - iva_creditado
    headers = ["Concepto", "Base C$", "IVA C$"]
    w = [80, 40, 40]
    p.encabezado_tabla(headers, w)
    p.fila_tabla(["Ingresos Gravados", p.celda_monto(total_ingresos), p.celda_monto(iva_debitado)], w, align=["L", "R", "R"])
    p.fila_tabla(["Gastos con IVA", p.celda_monto(total_gastos), p.celda_monto(iva_creditado)], w, align=["L", "R", "R"])
    p.fila_tabla(["IVA a Pagar", "", p.celda_monto(iva_pagar)], w, align=["L", "R", "R"], bold=True)
    return p


# ── Generación de bytes ─────────────────────────────

def generar_pdf_bytes(func_pdf, data, desde=None, hasta=None):
    pdf = func_pdf(data, desde, hasta)
    return pdf.output()


def generar_pdf_bytes_con_periodo(func_pdf, data, desde, hasta):
    pdf = func_pdf(data, desde, hasta)
    return pdf.output()
