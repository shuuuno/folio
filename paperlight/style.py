from .theme import COLORS
from pathlib import Path

STYLE = """
* { font-family: 'Pretendard Variable', 'Malgun Gothic'; font-size: 13px; color: @ink; }
QMainWindow, QDialog { background: @surface; }
QWidget#windowBar { background: #F1F3F8; }
QToolButton#windowControl, QToolButton#windowClose { border: 0; border-radius: 0; padding: 0; }
QToolButton#windowClose:hover { background: #FBDDE0; }
QTabBar#documentTabs { background: transparent; }
QTabBar#documentTabs::tab { background: transparent; border: 0; border-top-left-radius: 7px; border-top-right-radius: 7px; margin-top: 5px; margin-right: 3px; padding: 8px 14px; min-width: 130px; max-width: 220px; }
QTabBar#documentTabs::tab:selected { background: white; }
QTabBar#documentTabs::tab:hover:!selected { background: #E6EAF2; }
QWidget#welcome { background: @chrome; }
QWidget#appHeader, QWidget#header { background: @surface; border-bottom: 1px solid @border; }
QWidget#tools { background: @surface; border-bottom: 1px solid @border; }
QWidget#toolRail { background: @surface; border-right: 1px solid @border; }
QWidget#sidebar { background: @chrome; border-right: 1px solid @border; }
QWidget#inspector { background: @surface; border-left: 1px solid @border; }
QLabel#brand { font-size: 17px; font-weight: 650; color: #222E44; }
QLabel#muted { color: @muted; font-size: 12px; }
QLabel#sectionTitle { font-size: 17px; font-weight: 650; }
QLabel#welcomeTitle { font-size: 30px; font-weight: 650; color: #253249; }
QLabel#welcomeBody { font-size: 14px; color: @muted; }
QLabel#panelCaption { font-size: 12px; color: @muted; font-weight: 550; }
QPushButton, QToolButton { background: transparent; border: 1px solid transparent; border-radius: 7px; padding: 7px 11px; }
QPushButton:hover, QToolButton:hover { background: #F0F3F9; }
QPushButton:pressed, QToolButton:pressed { background: #E5EAF4; }
QPushButton:focus, QToolButton:focus { border-color: #8D9FEE; }
QPushButton:disabled, QToolButton:disabled { color: #9CA6B6; }
QPushButton#primary { background: @accent; color: white; font-weight: 600; padding: 9px 18px; }
QPushButton#primary:hover { background: @accent_hover; }
QPushButton#primary:pressed { background: #2B44AE; }
QPushButton#primary:disabled { background: #DDE3F6; color: #7C89AE; }
QPushButton#secondary { background: @surface; border: 1px solid @border; }
QPushButton#secondary:hover { background: #F3F5FA; }
QPushButton#danger { color: #A6434A; }
QPushButton#danger:hover { background: #FFF0F1; }
QToolButton#iconButton { padding: 6px; }
QToolButton::menu-indicator { image: none; }
QToolButton#railButton { padding: 8px 4px; font-size: 11px; color: #58657C; }
QToolButton#railButton:checked { background: @selected; color: @accent; font-weight: 600; }
QToolButton#tabClose { padding: 3px; border-radius: 4px; }
QToolButton#tabClose:hover { background: #DFE5F0; }
QTabWidget::pane { border: 0; }
QTabWidget { background: @chrome; }
QTabBar::tab { background: #F1F3F8; border: 0; border-right: 1px solid @border; padding: 10px 15px; min-width: 130px; max-width: 230px; color: #606D83; }
QTabBar::tab:selected { background: white; color: #24314C; }
QTabBar::tab:hover:!selected { background: #E9EDF5; }
QTabBar::close-button { image: none; width: 0; }
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: white; border: 1px solid @border; border-radius: 7px; padding: 8px; selection-background-color: #DCE5FF; selection-color: #24314C; }
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover { border-color: #B8C2D4; }
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: #8095E8; }
QLineEdit#search { background: @chrome; border-color: transparent; padding: 7px 8px; }
QLineEdit#search:focus { border-color: #8095E8; background: white; }
QAbstractSpinBox QLineEdit { border: 0; padding: 0; background: transparent; }
QAbstractSpinBox { padding-right: 22px; }
QAbstractSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 20px; height: 16px; border: 0; background: transparent; }
QAbstractSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 20px; height: 16px; border: 0; background: transparent; }
QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover { background: #EBEFFE; }
QAbstractSpinBox::up-button:pressed, QAbstractSpinBox::down-button:pressed { background: #DCE5FF; }
QAbstractSpinBox::up-arrow { image: url('@ui/chevron-up.svg'); width: 10px; height: 10px; }
QAbstractSpinBox::down-arrow { image: url('@ui/chevron-down.svg'); width: 10px; height: 10px; }
QAbstractSpinBox:disabled { color: #9CA6B6; background: #F7F8FB; }
QComboBox::drop-down { border: 0; width: 26px; }
QComboBox QAbstractItemView { background: white; color: @ink; selection-background-color: @selected; outline: 0; border: 1px solid @border; padding: 4px; }
QListWidget { background: @chrome; border: 1px solid @border; border-radius: 8px; padding: 6px; outline: 0; }
QListWidget::item { padding: 9px; border-radius: 5px; }
QListWidget::item:selected { background: @selected; color: #3451C8; }
QListWidget#thumbnails { border: 0; border-radius: 0; padding: 10px 4px; }
QListWidget#thumbnails::item { padding: 6px; margin: 5px; border: 1px solid transparent; color: @muted; }
QListWidget#thumbnails::item:selected { background: #E7EDFD; border: 1px solid #A4B5F0; color: #3451C8; }
QGraphicsView { border: 0; background: @canvas; }
QStatusBar { background: white; border-top: 1px solid @border; color: @muted; font-size: 11px; }
QStatusBar::item { border: 0; }
QStatusBar QLabel { font-size: 11px; color: @muted; }
QStatusBar QSpinBox { border: 0; padding: 3px 20px 3px 6px; min-height: 22px; background: #F3F5FA; border-radius: 4px; }
QStatusBar QSpinBox::up-button, QStatusBar QSpinBox::down-button { height: 13px; }
QStatusBar QToolButton { padding: 3px; }
QMenu { background: white; border: 1px solid @border; padding: 6px; }
QMenu::item { padding: 9px 26px 9px 14px; border-radius: 5px; }
QMenu::item:selected { background: @selected; color: #3451C8; }
QMenu::item:disabled { color: #9CA6B6; }
QMenu::separator { height: 1px; background: @border; margin: 5px 8px; }
QToolTip { background: #253249; color: white; border: 0; padding: 6px 9px; }
QScrollBar:vertical { background: transparent; width: 9px; }
QScrollBar::handle:vertical { background: #C5CDD9; border-radius: 4px; min-height: 36px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 9px; }
QScrollBar::handle:horizontal { background: #C5CDD9; border-radius: 4px; min-width: 36px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
QSplitter::handle { background: @border; width: 1px; }
QProgressBar { background: #EBEFF6; border: 0; border-radius: 4px; min-height: 6px; max-height: 6px; color: transparent; }
QProgressBar::chunk { background: @accent; border-radius: 4px; }
"""
for _name in sorted(COLORS, key=len, reverse=True):
    STYLE = STYLE.replace("@" + _name, COLORS[_name])
STYLE = STYLE.replace("@ui", (Path(__file__).resolve().parents[1] / "assets/ui").as_posix())
