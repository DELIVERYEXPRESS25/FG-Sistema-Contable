"""
══════════════════════════════════════════════════════════════════════════════
 Página Balanza de Comprobación
══════════════════════════════════════════════════════════════════════════════
"""

import flet as ft
from config import THEME
from utils.helpers import format_money, calcular_balanza


class BalanzaPage(ft.Container):
    def __init__(self, page, data):
        self.page = page
        self.data = data

        super().__init__(expand=True, content=self.build_content())

    def build_content(self):
        balanza, total_debe, total_haber = calcular_balanza(self.data)

        return ft.Column(
            controls=[
                self.build_header(balanza, total_debe, total_haber),
                # Tabla de balanza
                self.build_balanza_table(balanza, total_debe, total_haber),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def build_header(self, balanza, total_debe, total_haber):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "⚖️ Balanza de Comprobación",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=THEME["text_bright"],
                    ),
                    ft.Text(
                        f"Cuentas: {len(balanza)} | Total Débitos: {format_money(total_debe)} | Total Créditos: {format_money(total_haber)}",
                        size=12,
                        color=THEME["text_dim"],
                    ),
                ]
            ),
            margin=ft.margin.only(bottom=20),
        )

    def build_balanza_table(self, balanza, total_debe, total_haber):
        return ft.Container(
            padding=20,
            border_radius=14,
            bgcolor=THEME["card"],
            border=ft.border(all=1, color=THEME["card_border"]),
            content=ft.Column(
                controls=[
                    # Headers
                    ft.Container(
                        padding=10,
                        bgcolor=THEME["bg3"],
                        border_radius=8,
                        content=ft.Row(
                            controls=[
                                ft.Text(
                                    "Código",
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    width=80,
                                ),
                                ft.Text(
                                    "Cuenta",
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    expand=True,
                                ),
                                ft.Text(
                                    "Débitos",
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    width=100,
                                    text_align=ft.TextAlign.RIGHT,
                                ),
                                ft.Text(
                                    "Créditos",
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    width=100,
                                    text_align=ft.TextAlign.RIGHT,
                                ),
                            ]
                        ),
                    ),
                    # Datos
                    *self.build_balanza_rows(balanza),
                    # Totales
                    ft.Divider(color=THEME["card_border"]),
                    ft.Container(
                        padding=10,
                        bgcolor=THEME["accent"] + "20",
                        border_radius=8,
                        content=ft.Row(
                            controls=[
                                ft.Text(
                                    "TOTALES",
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    expand=True,
                                ),
                                ft.Text(
                                    format_money(total_debe),
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    width=100,
                                    text_align=ft.TextAlign.RIGHT,
                                    color=THEME["green"],
                                ),
                                ft.Text(
                                    format_money(total_haber),
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    width=100,
                                    text_align=ft.TextAlign.RIGHT,
                                    color=THEME["red"],
                                ),
                            ]
                        ),
                    ),
                ],
                spacing=5,
            ),
        )

    def build_balanza_rows(self, balanza):
        rows = []
        for item in balanza:
            if item.get("debe", 0) > 0 or item.get("haber", 0) > 0:
                rows.append(
                    ft.Container(
                        padding=10,
                        content=ft.Row(
                            controls=[
                                ft.Text(
                                    item.get("codigo", ""),
                                    size=11,
                                    color=THEME["text_dim"],
                                    width=80,
                                ),
                                ft.Text(
                                    item.get("nombre", "")[:30],
                                    size=11,
                                    color=THEME["text"],
                                    expand=True,
                                ),
                                ft.Text(
                                    format_money(item.get("debe", 0)),
                                    size=11,
                                    width=100,
                                    text_align=ft.TextAlign.RIGHT,
                                ),
                                ft.Text(
                                    format_money(item.get("haber", 0)),
                                    size=11,
                                    width=100,
                                    text_align=ft.TextAlign.RIGHT,
                                ),
                            ]
                        ),
                    )
                )
        return rows
