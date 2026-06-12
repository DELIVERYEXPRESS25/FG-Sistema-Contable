"""
══════════════════════════════════════════════════════════════════════════════
 Página Configuración
══════════════════════════════════════════════════════════════════════════════
"""

import flet as ft
from config import THEME


class SettingsPage(ft.Container):
    def __init__(self, page, data, refresh_callback):
        self.page = page
        self.data = data
        self.refresh = refresh_callback

        super().__init__(expand=True, content=self.build_content())

    def build_content(self):
        return ft.Column(
            controls=[self.build_header(), self.build_settings_form()],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def build_header(self):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "⚙️ Configuración",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=THEME["text_bright"],
                    ),
                    ft.Text(
                        "Configuración del sistema", size=12, color=THEME["text_dim"]
                    ),
                ]
            ),
            margin=ft.margin.only(bottom=20),
        )

    def build_settings_form(self):
        return ft.Container(
            padding=20,
            border_radius=14,
            bgcolor=THEME["card"],
            border=ft.border(all=1, color=THEME["card_border"]),
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Información del Sistema",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=THEME["text_bright"],
                    ),
                    ft.Divider(color=THEME["card_border"]),
                    self.create_setting_row("Versión", "1.0.0"),
                    self.create_setting_row("Base de datos", "SQLite"),
                    self.create_setting_row("Fecha de actualización", "17/04/2026"),
                    ft.Container(height=20),
                    ft.Text(
                        "Acciones",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=THEME["text_bright"],
                    ),
                    ft.Divider(color=THEME["card_border"]),
                    ft.Row(
                        controls=[
                            ft.ElevatedButton(
                                "💾 Exportar Backup",
                                on_click=self.exportar_backup,
                                bgcolor=THEME["green"],
                                color="white",
                            ),
                            ft.ElevatedButton(
                                "🔄 Restaurar desde Backup",
                                on_click=self.restaurar_backup,
                                bgcolor=THEME["accent"],
                                color="white",
                            ),
                            ft.ElevatedButton(
                                "🗑️ Borrar Todos los Datos",
                                on_click=self.borrar_datos,
                                bgcolor=THEME["red"],
                                color="white",
                            ),
                        ],
                        spacing=10,
                    ),
                ],
                spacing=15,
            ),
        )

    def create_setting_row(self, label, value):
        return ft.Row(
            controls=[
                ft.Text(f"{label}:", size=12, color=THEME["text_dim"], width=150),
                ft.Text(value, size=12, color=THEME["text_bright"], expand=True),
            ]
        )

    def exportar_backup(self, e):
        self.page.snack_bar = ft.SnackBar(content=ft.Text("Exportando backup..."))
        self.page.snack_bar.open = True
        self.page.update()

    def restaurar_backup(self, e):
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text("Restaurando desde backup...")
        )
        self.page.snack_bar.open = True
        self.page.update()

    def borrar_datos(self, e):
        # Confirmación
        def borrar_confirmado(e):
            from db import empty_data, save_data

            save_data(empty_data())
            self.refresh()
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("Datos borrados correctamente")
            )
            self.page.snack_bar.open = True
            self.page.update()
            self.dialog.open = False
            self.page.update()

        self.dialog = ft.AlertDialog(
            title=ft.Text("Confirmar eliminación"),
            content=ft.Text(
                "¿Está seguro de que desea borrar TODOS los datos? Esta acción no se puede deshacer."
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.close_dialog(e)),
                ft.TextButton("Borrar Todo", on_click=borrar_confirmado),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()

    def close_dialog(self, e):
        self.dialog.open = False
        self.page.update()
