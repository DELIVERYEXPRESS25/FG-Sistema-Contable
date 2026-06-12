"""
══════════════════════════════════════════════════════════════════════════════
 Página Dashboard - Panel principal
══════════════════════════════════════════════════════════════════════════════
"""

import flet as ft
from datetime import datetime
from config import THEME
from utils.helpers import format_money, calcular_utilidad, calcular_totales


class DashboardPage(ft.Container):
    def __init__(self, page, data, navigate):
        self.page = page
        self.data = data
        self.navigate = navigate

        super().__init__(expand=True, content=self.build_content())

    def build_content(self):
        # Calcular métricas
        utilidad = calcular_utilidad(self.data)
        totales = calcular_totales(self.data)

        return ft.SingleChildScrollView(
            content=ft.Column(
                controls=[
                    # Header
                    self.build_header(),
                    # Stats Cards
                    self.build_stats_row(utilidad, totales),
                    # Diario Reciente
                    self.build_diario_reciente(),
                ],
                spacing=20,
                expand=True,
            )
        )

    def build_header(self):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "📊 Dashboard",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=THEME["text_bright"],
                    ),
                    ft.Text(
                        f"Fecha: {datetime.now().strftime('%d de %B del %Y')}",
                        size=12,
                        color=THEME["text_dim"],
                    ),
                ]
            ),
            margin=ft.margin.only(bottom=20),
        )

    def build_stats_row(self, utilidad, totales):
        return ft.Row(
            controls=[
                self.create_stat_card(
                    "📈 Ingresos",
                    format_money(totales.get("ingresos", 0)),
                    "+12%",
                    THEME["green"],
                ),
                self.create_stat_card(
                    "📉 Gastos",
                    format_money(totales.get("gastos", 0)),
                    "+5%",
                    THEME["red"],
                ),
                self.create_stat_card(
                    "💰 Utilidad", format_money(utilidad), "Neta", THEME["accent"]
                ),
                self.create_stat_card(
                    "🏦 Activos",
                    format_money(totales.get("activos", 0)),
                    "Total",
                    THEME["yellow"],
                ),
            ],
            spacing=20,
        )

    def create_stat_card(self, label, value, trend, color):
        return ft.Container(
            width=200,
            padding=20,
            border_radius=14,
            bgcolor=THEME["card"],
            border=ft.border(all=1, color=THEME["card_border"]),
            content=ft.Column(
                controls=[
                    ft.Text(label, size=11, color=THEME["text_dim"]),
                    ft.Text(
                        value,
                        size=22,
                        weight=ft.FontWeight.BOLD,
                        color=THEME["text_bright"],
                    ),
                    ft.Text(trend, size=11, color=color),
                ],
                spacing=5,
            ),
        )

    def build_diario_reciente(self):
        diario = self.data.get("diario", [])
        # Últimos 5 asientos
        recent = sorted(diario, key=lambda x: x.get("fecha", ""), reverse=True)[:5]

        return ft.Container(
            padding=20,
            border_radius=14,
            bgcolor=THEME["card"],
            border=ft.border(all=1, color=THEME["card_border"]),
            content=ft.Column(
                controls=[
                    ft.Text(
                        "🧾 Últimos Asientos del Diario",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=THEME["text_bright"],
                    ),
                    ft.Divider(color=THEME["card_border"]),
                    *self.build_diario_items(recent),
                ],
                spacing=10,
            ),
        )

    def build_diario_items(self, asientos):
        if not asientos:
            return [ft.Text("No hay asientos registrados", color=THEME["text_dim"])]

        items = []
        for a in asientos:
            total = sum(m.get("monto", 0) for m in a.get("movimientos", []))
            items.append(
                ft.Container(
                    padding=10,
                    border_radius=8,
                    bgcolor=THEME["bg3"],
                    content=ft.Row(
                        controls=[
                            ft.Text(
                                str(a.get("id", "")),
                                size=12,
                                color=THEME["text_dim"],
                                width=30,
                            ),
                            ft.Text(
                                a.get("fecha", ""),
                                size=12,
                                color=THEME["text_dim"],
                                width=100,
                            ),
                            ft.Text(
                                a.get("descripcion", "")[:40],
                                size=12,
                                color=THEME["text"],
                                expand=True,
                            ),
                            ft.Text(
                                format_money(total),
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                color=THEME["accent"],
                            ),
                        ]
                    ),
                )
            )
        return items
