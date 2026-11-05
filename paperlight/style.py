STYLE = """
* { font-family: 'Malgun Gothic'; font-size: 13px; color: #233647; }
QMainWindow, QDialog { background: #ffffff; }
QToolTip { background: #233647; color: #ffffff; border: 0; padding: 7px; }
QWidget#header { background: #ffffff; border-bottom: 1px solid #e4e9ee; }
QWidget#tools { background: #fbfcfd; border-bottom: 1px solid #e4e9ee; }
QWidget#sidebar, QWidget#inspector { background: #ffffff; }
QLabel#brand { color: #153e43; font-size: 22px; font-weight: 700; }
QLabel#muted { color: #7a8996; font-size: 11px; }
QLabel#sectionTitle { color: #223b49; font-size: 17px; font-weight: 700; }
QLabel#welcomeTitle { color: #183c43; font-size: 36px; font-weight: 700; }
QLabel#welcomeBody { color: #72818c; font-size: 15px; }
QPushButton, QToolButton { border: 1px solid transparent; border-radius: 7px; padding: 8px 12px; background: transparent; }
QPushButton:hover, QToolButton:hover { background: #edf3f4; }
QPushButton:checked, QToolButton:checked { color: #146b66; background: #e1f1ed; border-color: #c4e4dc; }
QPushButton:disabled, QToolButton:disabled { color: #adb7bf; }
QPushButton#primary { color: #ffffff; background: #237b70; font-weight: 700; padding: 10px 19px; }
QPushButton#primary:hover { background: #1c685f; }
QPushButton#primary:disabled { background: #bdcdc9; }
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: #f8fafb; border: 1px solid #dde5e9; border-radius: 6px; padding: 6px; selection-background-color: #a5d6cc; }
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border-color: #399489; }
QAbstractSpinBox QLineEdit { border: 0; padding: 0; background: transparent; }
QListWidget { background: #f8fafb; border: 0; outline: 0; padding: 12px; }
QListWidget::item { border: 2px solid transparent; border-radius: 8px; padding: 8px; margin-bottom: 9px; color: #71818d; }
QListWidget::item:selected { background: #e8f3ef; border-color: #3c9387; color: #176b62; }
QGraphicsView { border: 0; background: #e9eef1; }
QStatusBar { background: #ffffff; border-top: 1px solid #e4e9ee; color: #7a8996; font-size: 11px; }
QScrollBar:vertical { background: transparent; width: 10px; }
QScrollBar::handle:vertical { background: #c0cbd2; border-radius: 5px; min-height: 36px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; }
QScrollBar::handle:horizontal { background: #c0cbd2; border-radius: 5px; min-width: 36px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QSplitter::handle { background: #e4e9ee; width: 1px; }
"""
