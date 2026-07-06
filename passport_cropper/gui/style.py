"""Gowri Studio theme — light & dark, built around the gold brand accent."""

GOLD = "#F0B90B"
GOLD_HOVER = "#FFC526"
GOLD_TEXT = "#141414"   # text on gold buttons


def _palette(dark: bool) -> dict:
    if dark:
        return dict(
            bg="#1b1c21", panel="#24262e", header="#202128",
            text="#e6e8ec", subtext="#9aa0ab", border="#34363f",
            input_bg="#2b2d36", input_border="#3a3d47", th_bg="#2b2d36",
            dz_bg="#2b2718", dz_border="#6b5a1e", row_sel="#2f3546",
            accent=GOLD, link=GOLD,
        )
    return dict(
        bg="#f3f4f6", panel="#ffffff", header="#ffffff",
        text="#1f2937", subtext="#6b7280", border="#e5e7eb",
        input_bg="#ffffff", input_border="#d1d5db", th_bg="#f9fafb",
        dz_bg="#fbf6e6", dz_border="#e6c65c", row_sel="#fff6da",
        accent="#B8860B", link="#B8860B",
    )


def build_qss(dark: bool) -> str:
    p = _palette(dark)
    return f"""
* {{
    font-family: -apple-system, "SF Pro Text", "Segoe UI", "Helvetica Neue", Arial;
    font-size: 13px; color: {p['text']};
}}
QMainWindow, QWidget#page, QScrollArea, QScrollArea > QWidget > QWidget {{ background: {p['bg']}; }}

QWidget#header {{ background: {p['header']}; border-bottom: 1px solid {p['border']}; }}
QLabel#brand {{ font-size: 19px; font-weight: 800; color: {p['text']}; letter-spacing: 0.3px; }}
QLabel#brandsub {{ color: {p['subtext']}; font-size: 11px; }}
QPushButton#themeToggle {{
    background: transparent; border: 1px solid {p['border']}; border-radius: 16px;
    padding: 6px 14px; color: {p['subtext']};
}}
QPushButton#themeToggle:hover {{ border-color: {GOLD}; color: {p['text']}; }}

QTabWidget::pane {{ border: none; background: {p['bg']}; }}
QTabBar::tab {{
    background: transparent; padding: 10px 22px; margin-right: 2px;
    color: {p['subtext']}; font-weight: 600; border: none;
}}
QTabBar::tab:selected {{ color: {p['accent']}; border-bottom: 3px solid {GOLD}; }}
QTabBar::tab:hover {{ color: {p['text']}; }}

QLabel#title {{ font-size: 20px; font-weight: 700; color: {p['text']}; }}
QLabel#subtitle {{ color: {p['subtext']}; font-size: 13px; }}

QPushButton {{
    background: {p['panel']}; border: 1px solid {p['input_border']}; border-radius: 8px;
    padding: 8px 14px; color: {p['text']};
}}
QPushButton:hover {{ border-color: {GOLD}; }}
QPushButton:disabled {{ color: {p['subtext']}; border-color: {p['border']}; }}
QPushButton#primary {{
    background: {GOLD}; color: {GOLD_TEXT}; border: none; font-weight: 700; padding: 9px 22px;
}}
QPushButton#primary:hover {{ background: {GOLD_HOVER}; }}
QPushButton#primary:disabled {{ background: {p['border']}; color: {p['subtext']}; }}

QGroupBox {{
    background: {p['panel']}; border: 1px solid {p['border']}; border-radius: 12px;
    margin-top: 16px; padding: 16px 14px 10px 14px; font-weight: 700;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 14px; padding: 0 6px; color: {p['text']}; }}

QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{
    background: {p['input_bg']}; border: 1px solid {p['input_border']}; border-radius: 8px;
    padding: 6px 10px; min-height: 20px; color: {p['text']}; selection-background-color: {GOLD};
}}
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {{ border-color: {GOLD}; }}
QComboBox QAbstractItemView {{ background: {p['panel']}; color: {p['text']};
    selection-background-color: {GOLD}; selection-color: {GOLD_TEXT}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QCheckBox {{ spacing: 8px; }}

QProgressBar {{ border: none; background: {p['border']}; border-radius: 7px; height: 12px; }}
QProgressBar::chunk {{ background: {GOLD}; border-radius: 7px; }}

QTableWidget {{
    background: {p['panel']}; border: 1px solid {p['border']}; border-radius: 12px;
    gridline-color: {p['border']};
}}
QTableWidget::item {{ padding: 6px; }}
QTableWidget::item:selected {{ background: {p['row_sel']}; color: {p['text']}; }}
QHeaderView::section {{
    background: {p['th_bg']}; padding: 10px; border: none;
    border-bottom: 1px solid {p['border']}; font-weight: 700; color: {p['subtext']};
}}

QFrame#dropzone {{ background: {p['dz_bg']}; border: 2px dashed {p['dz_border']}; border-radius: 14px; }}
QFrame#dropzone[hovering="true"] {{ border-color: {GOLD}; }}
QLabel#drophint {{ color: {p['accent']}; font-size: 15px; font-weight: 700; }}
QLabel#dropsub {{ color: {p['subtext']}; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {p['input_border']}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {GOLD}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

QDialog {{ background: {p['bg']}; }}
QMenu {{ background: {p['panel']}; color: {p['text']}; border: 1px solid {p['border']}; }}
QMenu::item:selected {{ background: {GOLD}; color: {GOLD_TEXT}; }}
"""


# Back-compat: a default stylesheet constant.
APP_QSS = build_qss(dark=True)
