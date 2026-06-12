"""
══════════════════════════════════════════════════════════════════════════════
 Configuración del Tema de la App
══════════════════════════════════════════════════════════════════════════════
"""

import flet as ft

THEME = {
    "bg": "#0f1117",
    "bg2": "#161822",
    "bg3": "#1e2030",
    "card": "#1a1d2e",
    "card_border": "#2a2d42",
    "accent": "#4f8cff",
    "accent2": "#7c5cfc",
    "green": "#2ecc71",
    "red": "#e74c3c",
    "yellow": "#f39c12",
    "text": "#e2e4eb",
    "text_dim": "#7a7f99",
    "text_bright": "#ffffff",
}


def get_theme() -> ft.ThemeMode:
    """Retorna el tema oscuro para la aplicación."""
    return ft.ThemeMode.DARK


def get_color(name: str) -> str:
    """Obtiene un color del tema."""
    return THEME.get(name, "#ffffff")


# Estilos CSS para Flet
CSS = f"""
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@300;400;500;600&display=swap');
    
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    
    body {{
        font-family: 'Inter', sans-serif;
        background: {THEME["bg"]};
        color: {THEME["text"]};
    }}
    
    .title {{
        font-family: 'Playfair Display', serif;
        font-weight: 700;
        color: {THEME["text_bright"]};
    }}
    
    .card {{
        background: {THEME["card"]};
        border: 1px solid {THEME["card_border"]};
        border-radius: 14px;
        padding: 20px;
    }}
    
    .btn-primary {{
        background: linear-gradient(135deg, {THEME["accent"]}, {THEME["accent2"]});
        color: #fff;
        border-radius: 8px;
        padding: 10px 20px;
    }}
"""
