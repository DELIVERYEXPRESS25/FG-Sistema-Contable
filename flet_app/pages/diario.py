"""
══════════════════════════════════════════════════════════════════════════════
 Página Libro Diario
══════════════════════════════════════════════════════════════════════════════
"""

import flet as ft
from datetime import datetime
from config import THEME
from utils.helpers import format_money, get_next_id
from db import save_data


class DiarioPage(ft.Container):
    def __init__(self, page, data, refresh_callback):
        self.page = page
        self.data = data
        self.refresh = refresh_callback

        super().__init__(expand=True, content=self.build_content())

    def build_content(self):
        return ft.Column(
            controls=[
                # Header
                self.build_header(),
                # Botón agregar
                ft.ElevatedButton(
                    "➕ Nuevo Asiento",
                    on_click=self.show_nuevo_asiento,
                    bgcolor=THEME["accent"],
                    color="white",
                ),
                ft.Container(height=20),
                # Lista de asientos
                self.build_asientos_list(),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def build_header(self):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "🧾 Libro Diario",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=THEME["text_bright"],
                    ),
                    ft.Text(
                        f"Total de asientos: {len(self.data.get('diario', []))}",
                        size=12,
                        color=THEME["text_dim"],
                    ),
                ]
            ),
            margin=ft.margin.only(bottom=20),
        )

    def build_asientos_list(self):
        diario = self.data.get("diario", [])

        if not diario:
            return ft.Container(
                content=ft.Text("No hay asientos registrados", color=THEME["text_dim"]),
                padding=20,
            )

        # Ordenar por fecha
        diario = sorted(diario, key=lambda x: x.get("fecha", ""), reverse=True)

        controls = []
        for entry in diario:
            controls.append(self.create_asiento_card(entry))

        return ft.Column(controls=controls, spacing=10)

    def create_asiento_card(self, entry):
        total = sum(m.get("monto", 0) for m in entry.get("movimientos", []))

        return ft.Container(
            padding=15,
            border_radius=12,
            bgcolor=THEME["card"],
            border=ft.border(all=1, color=THEME["card_border"]),
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                f"#{entry.get('id', '')}",
                                size=14,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                entry.get("fecha", ""), size=12, color=THEME["text_dim"]
                            ),
                            ft.Text(
                                entry.get("ref", ""), size=12, color=THEME["text_dim"]
                            ),
                            ft.Container(expand=True),
                            ft.Text(
                                format_money(total),
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=THEME["accent"],
                            ),
                        ]
                    ),
                    ft.Text(entry.get("descripcion", ""), size=13, color=THEME["text"]),
                    ft.Divider(color=THEME["card_border"]),
                    # Movimientos
                    *self.build_movimientos(entry.get("movimientos", [])),
                ],
                spacing=8,
            ),
        )

    def build_movimientos(self, movimientos):
        items = []
        for m in movimientos:
            cuenta = m.get("cuenta", "")
            nombre_cuenta = (
                self.data.get("cuentas", {}).get(cuenta, {}).get("nombre", cuenta)
            )
            items.append(
                ft.Row(
                    controls=[
                        ft.Text(cuenta, size=11, color=THEME["text_dim"], width=50),
                        ft.Text(
                            nombre_cuenta, size=11, color=THEME["text"], expand=True
                        ),
                        ft.Text(
                            m.get("tipo", ""),
                            size=11,
                            color=THEME["text_dim"],
                            width=50,
                        ),
                        ft.Text(
                            format_money(m.get("monto", 0)),
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color=THEME["green"]
                            if m.get("tipo") == "Debe"
                            else THEME["red"],
                            width=100,
                            text_align=ft.TextAlign.RIGHT,
                        ),
                    ]
                )
            )
        return items

    def show_nuevo_asiento(self, e):
        # Dialog para nuevo asiento
        self.dialog = ft.AlertDialog(
            title=ft.Text("Nuevo Asiento"),
            content=ft.Container(
                width=500,
                content=ft.Column(
                    controls=[
                        ft.TextField(
                            label="Fecha", value=datetime.now().strftime("%Y-%m-%d")
                        ),
                        ft.TextField(label="Descripción"),
                        ft.TextField(label="Referencia"),
                        ft.Text("Cuentas:", size=12, color=THEME["text_dim"]),
                        # Aquí irían las cuentas...
                        ft.ElevatedButton("Agregar", on_click=self.guardar_asiento),
                    ]
                ),
            ),
        )
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()

    def guardar_asiento(self, e):
        # Implementar guardado
        pass
