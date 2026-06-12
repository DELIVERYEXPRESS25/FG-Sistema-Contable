"""
══════════════════════════════════════════════════════════════════════════════
 Página Mayor - Libro Mayor
══════════════════════════════════════════════════════════════════════════════
"""

import flet as ft
from config import THEME
from utils.helpers import format_money, calcular_mayor


class MayorPage(ft.Container):
    def __init__(self, page, data):
        self.page = page
        self.data = data

        super().__init__(expand=True, content=self.build_content())

    def build_content(self):
        mayor = calcular_mayor(self.data)

        return ft.Column(
            controls=[self.build_header(), self.build_cuentas_list(mayor)],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def build_header(self):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "📗 Libro Mayor",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=THEME["text_bright"],
                    ),
                    ft.Text(
                        f"Cuentas con movimientos: {len(mayor)}",
                        size=12,
                        color=THEME["text_dim"],
                    ),
                ]
            ),
            margin=ft.margin.only(bottom=20),
        )

    def build_cuentas_list(self, mayor):
        if not mayor:
            return ft.Container(
                content=ft.Text(
                    "No hay movimientos registrados", color=THEME["text_dim"]
                ),
                padding=20,
            )

        controls = []
        for cuenta, datos in sorted(mayor.items()):
            nombre = self.data.get("cuentas", {}).get(cuenta, {}).get("nombre", cuenta)

            controls.append(self.create_cuenta_card(cuenta, nombre, datos))

        return ft.Column(controls=controls, spacing=15)

    def create_cuenta_card(self, cuenta, nombre, datos):
        debe = datos.get("debe", 0)
        haber = datos.get("haber", 0)
        saldo = debe - haber

        return ft.Container(
            padding=20,
            border_radius=14,
            bgcolor=THEME["card"],
            border=ft.border(all=1, color=THEME["card_border"]),
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(cuenta, size=12, color=THEME["text_dim"]),
                            ft.Text(
                                nombre,
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=THEME["text_bright"],
                                expand=True,
                            ),
                        ]
                    ),
                    ft.Divider(color=THEME["card_border"]),
                    ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text("Debe", size=10, color=THEME["text_dim"]),
                                    ft.Text(
                                        format_money(debe),
                                        size=14,
                                        weight=ft.FontWeight.BOLD,
                                        color=THEME["green"],
                                    ),
                                ],
                                spacing=2,
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text("Haber", size=10, color=THEME["text_dim"]),
                                    ft.Text(
                                        format_money(haber),
                                        size=14,
                                        weight=ft.FontWeight.BOLD,
                                        color=THEME["red"],
                                    ),
                                ],
                                spacing=2,
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text("Saldo", size=10, color=THEME["text_dim"]),
                                    ft.Text(
                                        format_money(saldo),
                                        size=14,
                                        weight=ft.FontWeight.BOLD,
                                        color=THEME["accent"],
                                    ),
                                ],
                                spacing=2,
                            ),
                        ],
                        spacing=40,
                    ),
                ]
            ),
        )
