from .theme import COLORS, TYPE
from pathlib import Path

STYLE = """
* { font-family: 'Pretendard Variable', 'Malgun Gothic'; font-size: @type-body; color: @ink; }
QMainWindow, QDialog { background: @surface; }
QWidget#windowBar { background: @window_bar; }
QLabel#wordmark { font-size: @type-wordmark; font-weight: 600; color: @ink; }
QToolButton#windowControl, QToolButton#windowClose { border: 0; border-radius: 0; padding: 0; }
QToolButton#windowClose:hover { background: @close_hover; }
QToolButton#windowControl:focus, QToolButton#windowClose:focus { border: 1px dashed @focus; }
QTabBar#documentTabs { background: transparent; }
QTabBar#documentTabs::tab { background: transparent; border: 0; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-top: 5px; margin-right: 3px; padding: 6px 12px; min-width: 110px; max-width: 210px; }
QTabBar#documentTabs::tab:selected { background: @surface; font-weight: 600; }
QTabBar#documentTabs::tab:hover:!selected { background: @tab_hover; }
QWidget#welcome { background: @canvas; }
QWidget#emptyContent { background: @surface; }
QWidget#appHeader, QWidget#header { background: @surface; border-bottom: 1px solid @border; }
QWidget#tools { background: @surface; border-bottom: 1px solid @border_hover; }
QWidget#sidebar { background: @rail; border-right: 1px solid @border; }
QWidget#inspector { background: @surface; border-left: 1px solid @border; }
QScrollArea#inspectorFields { background: @surface; }
QWidget#inspectorFooter { background: @selected; border-top: 1px solid @border; }
QWidget#inspectorBody { background: @surface; }
QLabel#brand { font-size: @type-title; font-weight: 600; color: @ink; }
QLabel#muted { color: @muted; font-size: @type-label; }
QLabel#sectionTitle { font-size: @type-title; font-weight: 600; }
QLabel#groupTitle { font-size: @type-group; font-weight: 600; }
QLabel#dialogTitle { font-size: @type-dialog; font-weight: 600; padding-bottom: 10px; }
QLabel#welcomeTitle { font-size: @type-headline; font-weight: 600; color: @ink; }
QLabel#welcomeBody { font-size: @type-introduction; color: @muted; }
QLabel:disabled { color: @disabled; }
QLabel#panelCaption { font-size: @type-label; color: @muted; font-weight: 600; }
QLabel#pagesTitle { font-size: @type-page_heading; font-weight: 600; color: @accent; padding: 0 20px 16px; }
QFrame#sectionRule { background: @border; border: 0; max-height: 1px; min-height: 1px; }
QFrame#ribbonSeparator { background: @border; border: 0; }
QPushButton, QToolButton { background: transparent; border: 1px solid transparent; border-radius: 4px; padding: 6px 10px; }
QPushButton:hover, QToolButton:hover { background: @hover; }
QPushButton:pressed, QToolButton:pressed { background: @pressed; }
QPushButton:focus, QToolButton:focus { border-color: @focus; border-style: dashed; }
QPushButton:disabled, QToolButton:disabled { color: @disabled; }
QPushButton#primary { background: @accent; color: @surface; font-weight: 600; padding: 9px 18px; }
QPushButton#primary:hover { background: @accent_hover; }
QPushButton#primary:pressed { background: @accent_pressed; }
QPushButton#primary:focus { border-color: @surface; border-style: dashed; }
QPushButton#primary:disabled { background: @disabled_primary_bg; color: @disabled_primary_ink; }
QPushButton#secondary { background: @surface; border: 1px solid @border; }
QPushButton#secondary:hover { background: @hover; }
QPushButton#secondary:focus { border-color: @focus; border-style: dashed; }
QPushButton#danger { color: @danger; }
QPushButton#danger:hover { background: @danger_hover; }
QToolButton#iconButton { padding: 6px; }
QToolButton::menu-indicator { image: none; }
QToolButton#railButton { padding: 6px 2px; font-size: @type-body; color: @ink; }
QToolButton#railButton:checked { background: @accent; color: @surface; font-weight: 600; }
QToolButton#railButton:checked:focus { border-color: @surface; border-style: dashed; }
QToolButton#railButton:disabled { background: transparent; color: @disabled; font-weight: 400; }
QPushButton#danger:disabled { color: @disabled; }
QToolButton#tabClose { padding: 3px; border-radius: 4px; }
QToolButton#tabClose:hover { background: @hover; }
QTabWidget::pane { border: 0; }
QTabWidget { background: @chrome; }
QTabBar::tab { background: @window_bar; border: 0; border-right: 1px solid @border; padding: 10px 15px; min-width: 130px; max-width: 230px; color: @muted; }
QTabBar::tab:selected { background: @surface; color: @selection_ink; }
QTabBar::tab:hover:!selected { background: @hover; }
QTabBar::close-button { image: none; width: 0; }
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: @surface; border: 1px solid @control_border; border-radius: 4px; padding: 7px; selection-background-color: @selection_text; selection-color: @selection_ink; }
QTextEdit#contentEditor { background: @chrome; font-size: @type-editor; padding: 10px; }
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover { border-color: @border_hover; }
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border: 2px solid @focus; padding: 6px; }
QTextEdit#contentEditor:focus { padding: 9px; }
QLineEdit#search { background: @chrome; border-color: @control_border; padding: 7px 8px; }
QLineEdit#search:focus { border: 2px solid @focus; padding: 6px 7px; background: @surface; }
QAbstractSpinBox QLineEdit, QAbstractSpinBox QLineEdit:focus { border: 0; padding: 0; background: transparent; }
QAbstractSpinBox { padding-right: 22px; }
QAbstractSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 20px; height: 16px; border: 0; background: transparent; }
QAbstractSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 20px; height: 16px; border: 0; background: transparent; }
QAbstractSpinBox:focus { padding-right: 21px; }
QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover { background: @selected; }
QAbstractSpinBox::up-button:pressed, QAbstractSpinBox::down-button:pressed { background: @selection_text; }
QAbstractSpinBox::up-arrow { image: url('@ui/chevron-up.svg'); width: 10px; height: 10px; }
QAbstractSpinBox::down-arrow { image: url('@ui/chevron-down.svg'); width: 10px; height: 10px; }
QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled, QAbstractSpinBox:disabled { color: @disabled; background: @chrome; }
QComboBox { padding-right: 28px; }
QComboBox:focus { padding-right: 27px; }
QComboBox::drop-down { border: 0; width: 26px; }
QComboBox::down-arrow { image: url('@ui/chevron-down.svg'); width: 12px; height: 12px; }
QComboBox QAbstractItemView { background: @surface; color: @ink; selection-background-color: @selected; outline: 0; border: 1px solid @border; padding: 4px; }
QListWidget { background: @chrome; border: 1px solid @border; border-radius: 4px; padding: 4px; outline: 0; }
QListWidget::item { padding: 8px; border-radius: 2px; }
QListWidget::item:selected { background: @selected; color: @accent; }
QListWidget:focus { border-color: @focus; }
QListWidget#thumbnails { background: @rail; border: 0; border-radius: 0; padding: 4px 8px; }
QListWidget#thumbnails::item { padding: 10px 12px; margin: 6px; border: 1px solid transparent; color: @muted; }
QListWidget#thumbnails::item:selected { background: @accent; border: 1px solid @accent; color: @surface; font-weight: 600; }
QGraphicsView { border: 0; background: @canvas; }
QStatusBar { background: @surface; border-top: 1px solid @border; color: @muted; font-size: @type-compact; }
QStatusBar::item { border: 0; }
QStatusBar QLabel { font-size: @type-compact; color: @muted; }
QStatusBar QSpinBox { border: 1px solid transparent; padding: 3px 20px 3px 6px; min-height: 22px; background: @chrome; border-radius: 4px; }
QStatusBar QSpinBox:focus { border-color: @focus; }
QStatusBar QSpinBox::up-button, QStatusBar QSpinBox::down-button { height: 13px; }
QStatusBar QToolButton { padding: 3px; }
QMenu { background: @surface; border: 1px solid @border; padding: 6px; }
QMenu::item { padding: 9px 26px 9px 14px; border-radius: 5px; }
QMenu::item:selected { background: @selected; color: @accent; }
QMenu::item:disabled { color: @disabled; }
QMenu::separator { height: 1px; background: @border; margin: 5px 8px; }
QToolTip { background: @tooltip; color: @surface; border: 0; padding: 6px 9px; }
QScrollBar:vertical { background: transparent; width: 9px; }
QScrollBar::handle:vertical { background: @scrollbar; border-radius: 4px; min-height: 36px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 9px; }
QScrollBar::handle:horizontal { background: @scrollbar; border-radius: 4px; min-width: 36px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
QSplitter::handle { background: @border; width: 1px; }
QProgressBar { background: @rail; border: 0; border-radius: 4px; min-height: 6px; max-height: 6px; color: transparent; }
QProgressBar::chunk { background: @accent; border-radius: 4px; }
"""
for _name, _size in TYPE.items():
    STYLE = STYLE.replace("@type-" + _name, f"{_size}px")
for _name in sorted(COLORS, key=len, reverse=True):
    STYLE = STYLE.replace("@" + _name, COLORS[_name])
STYLE = STYLE.replace("@ui", (Path(__file__).resolve().parents[1] / "assets/ui").as_posix())
