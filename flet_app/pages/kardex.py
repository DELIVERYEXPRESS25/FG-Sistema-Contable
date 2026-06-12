"""
══════════════════════════════════════════════════════════════════════════════
 Página Kardex - Inventario
══════════════════════════════════════════════════════════════════════════════
"""

import flet as ft
from datetime import datetime
from config import THEME
from utils.helpers import format_money
from db import save_data


class KardexPage(ft.Container):
    def __init__(self, page, data, refresh_callback):
        self.page = page
        self.data = data
        self.refresh = refresh_callback

        super().__init__(expand=True, content=self.build_content())

    def build_content(self):
        return ft.Column(
            controls=[
                self.build_header(),
                # Productos
                self.build_productos_list(),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def build_header(self):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "📦 Tarjetas Kardex",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=THEME["text_bright"],
                    ),
                    ft.Text(
                        f"Productos registrados: {len(self.data.get('kardex', {}))}",
                        size=12,
                        color=THEME["text_dim"],
                    ),
                ]
            ),
            margin=ft.margin.only(bottom=20),
        )

    def build_productos_list(self):
        kardex = self.data.get("kardex", {})

        if not kardex:
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "No hay productos registrados", color=THEME["text_dim"]
                        ),
                        ft.ElevatedButton(
                            "➕ Agregar Producto", on_click=self.show_agregar_producto
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=40,
            )

        controls = []
        for nombre, movimientos in kardex.items():
            # Calcular saldo actual
            saldo = 0
            if movimientos:
                saldo = (
                    movimientos[-1].get("saldo", 0)
                    if isinstance(movimientos[-1], dict)
                    else 0
                )

            controls.append(self.create_producto_card(nombre, saldo, len(movimientos)))

        return ft.Column(controls=controls, spacing=15)

    def create_producto_card(self, nombre, saldo, total_mov):
        return ft.Container(
            padding=20,
            border_radius=14,
            bgcolor=THEME["card"],
            border=ft.border(all=1, color=THEME["card_border"]),
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                nombre,
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=THEME["text_bright"],
                                expand=True,
                            ),
                            ft.Container(
                                padding=ft.padding.only(
                                    left=10, right=10, top=5, bottom=5
                                ),
                                border_radius=20,
                                bgcolor=THEME["green"] + "20",
                                content=ft.Text(
                                    f"Stock: {saldo}", size=12, color=THEME["green"]
                                ),
                            ),
                        ]
                    ),
                    ft.Text(
                        f"Movimientos: {total_mov}", size=11, color=THEME["text_dim"]
                    ),
                ]
            ),
        )

    def show_agregar_producto(self, e):
        self.dialog = ft.AlertDialog(
            title=ft.Text("Nuevo Producto"),
            content=ft.TextField(label="Nombre del Producto"),
            actions=[
                ft.TextButton("Cancelar", on_click=self.close_dialog),
                ft.TextButton("Agregar", on_click=self.guardar_producto),
            ],
        )
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()

    def close_dialog(self, e):
        self.dialog.open = False
        self.page.update()

    def guardar_producto(self, e):
        # Implementar guardado
        pass
