"""
══════════════════════════════════════════════════════════════════════════════
 Widget Sidebar - Navegación lateral
══════════════════════════════════════════════════════════════════════════════
"""

import flet as ft
from config import THEME, get_color


class Sidebar(ft.Container):
    def __init__(self, onNavigate, onApagar):
        self.onNavigate = onNavigate
        self.onApagar = onApagar
        self.active_page = "dashboard"

        # Elementos de navegación
        self.nav_items = [
            {"icon": "home", "label": "Dashboard", "page": "dashboard"},
            {"icon": "receipt_long", "label": "Libro Diario", "page": "diario"},
            {"icon": "inventory_2", "label": "Kardex", "page": "kardex"},
            {"icon": "account_balance", "label": "Mayor", "page": "mayor"},
            {"icon": "balance", "label": "Balanza", "page": "balanza"},
            {"icon": "assessment", "label": "Reportes", "page": "reportes"},
            {"icon": "settings", "label": "Configuración", "page": "settings"},
        ]

    super().__init__(
        width=240,
        bgcolor=THEME["bg2"],
        border=ft.border.only(right=ft.BorderSide(1, THEME["card_border"])),
        padding=10,
        content=self.build_content(),
    )

    def build_content(self):
        return ft.Column(
            controls=[
                # Logo
                self.build_logo(),
                # Navegación
                self.build_nav(),
                # Espacio flexible
                ft.Container(expand=True),
                # Botón apagar
                self.build_bottom(),
            ],
            spacing=10,
            expand=True,
        )

    def build_logo(self):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        width=60,
                        height=60,
                        border_radius=30,
                        bgcolor=THEME["accent"],
                        content=ft.Text(
                            "F&G", size=20, weight=ft.FontWeight.BOLD, color="white"
                        ),
                        alignment=ft.alignment.center,
                    ),
                    ft.Text(
                        "Colectivo FG",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=THEME["text_bright"],
                    ),
                    ft.Text("Joyería y Más", size=10, color=THEME["text_dim"]),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5,
            ),
            padding=10,
            margin=ft.margin.only(bottom=20),
        )

    def build_nav(self):
        items = []
        for item in self.nav_items:
            items.append(
                self.create_nav_item(
                    icon=item["icon"], label=item["label"], page=item["page"]
                )
            )
        return ft.Column(controls=items, spacing=2)

    def create_nav_item(self, icon: str, label: str, page: str):
        is_active = self.active_page == page

        return ft.Container(
            on_click=lambda _: self.onNavigate(page),
            border_radius=8,
            padding=10,
            content=ft.Row(
                controls=[
                    ft.Icon(
                        icon,
                        size=20,
                        color=THEME["accent"] if is_active else THEME["text_dim"],
                    ),
                    ft.Text(
                        label,
                        size=13,
                        color=THEME["text_bright"] if is_active else THEME["text_dim"],
                    ),
                ],
                spacing=12,
            ),
            bgcolor=THEME["accent"] + "20" if is_active else "transparent",
            border=ft.border(
                right=ft.BorderSide(3, THEME["accent"])
                if is_active
                else ft.BorderSide(0, "transparent")
            ),
        )

    def build_bottom(self):
        return ft.Container(
            content=ft.ElevatedButton(
                "🔴 Apagar Sistema",
                on_click=lambda _: self.onApagar(),
                bgcolor=THEME["red"] + "20",
                color=THEME["red"],
                width="100%",
            )
        )

    def set_active(self, page: str):
        self.active_page = page
        self.content = self.build_content()
