"""
══════════════════════════════════════════════════════════════════════════════
 Página Reportes - Exportación de datos
══════════════════════════════════════════════════════════════════════════════
"""

import flet as ft
from config import THEME


class ReportesPage(ft.Container):
    def __init__(self, page, data):
        self.page = page
        self.data = data

        super().__init__(expand=True, content=self.build_content())

    def build_content(self):
        return ft.Column(
            controls=[
                self.build_header(),
                # Opciones de reportes
                self.build_reportes_grid(),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def build_header(self):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "📤 Reportes",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=THEME["text_bright"],
                    ),
                    ft.Text(
                        "Exporta los datos del sistema",
                        size=12,
                        color=THEME["text_dim"],
                    ),
                ]
            ),
            margin=ft.margin.only(bottom=20),
        )

    def build_reportes_grid(self):
        reportes = [
            {"icon": "description", "title": "Diario", "desc": "Exportar libro diario"},
            {
                "icon": "account_balance",
                "title": "Mayor",
                "desc": "Exportar libro mayor",
            },
            {"icon": "assessment", "title": "Balanza", "desc": "Exportar balanza"},
            {"icon": "inventory_2", "title": "Kardex", "desc": "Exportar inventario"},
            {
                "icon": "download",
                "title": "Backup JSON",
                "desc": "Exportar datos completos",
            },
            {"icon": "table_chart", "title": "Excel", "desc": "Exportar a Excel"},
        ]

        controls = []
        for r in reportes:
            controls.append(self.create_reporte_card(r["icon"], r["title"], r["desc"]))

        return ft.GridView(
            controls=controls, max_extent=200, spacing=15, run_spacing=15
        )

    def create_reporte_card(self, icon, title, desc):
        return ft.Container(
            padding=20,
            border_radius=14,
            bgcolor=THEME["card"],
            border=ft.border(all=1, color=THEME["card_border"]),
            on_click=lambda _: self.exportar(title),
            content=ft.Column(
                controls=[
                    ft.Icon(icon, size=32, color=THEME["accent"]),
                    ft.Text(
                        title,
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=THEME["text_bright"],
                    ),
                    ft.Text(desc, size=11, color=THEME["text_dim"]),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
        )

    def exportar(self, tipo):
        # Implementar exportación
        self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Exportando {tipo}..."))
        self.page.snack_bar.open = True
        self.page.update()
