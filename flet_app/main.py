"""
══════════════════════════════════════════════════════════════════════════════
 FG Sistema Contable - Flet App
══════════════════════════════════════════════════════════════════════════════
© 2024 Colectivo FG - Joyería y Muchas Más
"""

import flet as ft
from config import THEME, get_theme
from db import init_db, load_data, save_data
from pages.dashboard import DashboardPage
from pages.diario import DiarioPage
from pages.kardex import KardexPage
from pages.mayor import MayorPage
from pages.balanza import BalanzaPage
from pages.reportes import ReportesPage
from pages.settings import SettingsPage
from widgets.sidebar import Sidebar


class FGApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.current_page = "dashboard"

        # Configurar página
        self.page.title = "F&G Sistema Contable"
        self.page.theme = get_theme()
        self.page.padding = 0
        self.page.spacing = 0
        self.page.window_min_width = 1024
        self.page.window_min_height = 768

        # Inicializar base de datos
        init_db()

        # Cargar datos
        self.data = load_data()

        # Inicializar UI
        self.init_ui()

    def init_ui(self):
        # Sidebar
        self.sidebar = Sidebar(onNavigate=self.navigate, onApagar=self.apagar_sistema)

        # Contenedor principal
        self.main_content = ft.Container(
            expand=True, padding=20, content=self.get_current_page()
        )

        # Layout
        self.page.add(
            ft.Row(controls=[self.sidebar, self.main_content], expand=True, spacing=0)
        )

        self.page.update()

    def navigate(self, page_name: str):
        self.current_page = page_name
        self.main_content.content = self.get_current_page()
        self.sidebar.set_active(page_name)
        self.page.update()

    def get_current_page(self):
        pages = {
            "dashboard": DashboardPage(self.page, self.data, self.navigate),
            "diario": DiarioPage(self.page, self.data, self.refresh_data),
            "kardex": KardexPage(self.page, self.data, self.refresh_data),
            "mayor": MayorPage(self.page, self.data),
            "balanza": BalanzaPage(self.page, self.data),
            "reportes": ReportesPage(self.page, self.data),
            "settings": SettingsPage(self.page, self.data, self.refresh_data),
        }
        return pages.get(self.current_page, pages["dashboard"])

    def refresh_data(self):
        self.data = load_data()
        self.main_content.content = self.get_current_page()
        self.page.update()

    def apagar_sistema(self):
        self.page.window_destroy()


def main(page: ft.Page):
    FGApp(page)


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER)
