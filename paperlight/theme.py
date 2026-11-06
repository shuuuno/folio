"""Windows 테마와 관계없이 같은 명도/글꼴을 쓰는 네이티브 UI 토큰."""
from pathlib import Path
import os
import sys
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

COLORS = dict(ink="#202A3B", muted="#465772", accent="#3451C8", accent_hover="#2B44AE",
              accent_pressed="#243A96", selected="#E8EDFC", border="#D7DFEA",
              canvas="#CCD6E4", surface="#FFFFFF", chrome="#F3F6FA", rail="#E3EBFB",
              window_bar="#E8EDF5", tab_hover="#DCE4F0", hover="#E9EEF6", pressed="#DCE4F0",
              focus="#3451C8", disabled="#929DAF", disabled_primary_bg="#E0E6F2",
              disabled_primary_ink="#7785A2", danger="#A13644", danger_hover="#FCECEF",
              selection_text="#DCE5FF", selection_ink="#24314C", control_border="#7C8BA1", border_hover="#63758F",
              scrollbar="#B7C3D3", tooltip="#253249", close_hover="#FBDDE0")
TYPE = dict(body=14, compact=12, label=13, editor=16, introduction=18,
            title=26, group=17, page_heading=20, dialog=28, headline=44, wordmark=21)
_loaded = False


def create_application(arguments):
    """앱 안의 Windows 글자 렌더러만 고른다. 시스템 글꼴 설정은 바꾸지 않는다."""
    args = list(arguments) or ["Folio"]
    platform = os.environ.get("QT_QPA_PLATFORM", "")
    if sys.platform == "win32" and platform in ("", "windows"):
        args += ["-platform", "windows:fontengine=freetype"]
    return QApplication(args)


def install_theme():
    global _loaded
    app = QApplication.instance()
    if not _loaded:
        QFontDatabase.addApplicationFont(str(Path(__file__).resolve().parents[1] / "assets/fonts/PretendardVariable.ttf"))
        _loaded = True
    font = QFont("Pretendard Variable")
    font.setPixelSize(TYPE["body"])
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    font.setHintingPreference(QFont.HintingPreference.PreferVerticalHinting)
    app.setFont(font)
    palette = QPalette()
    for role, name in ((QPalette.ColorRole.Window, "surface"), (QPalette.ColorRole.Base, "surface"),
                       (QPalette.ColorRole.AlternateBase, "chrome"), (QPalette.ColorRole.Button, "surface"),
                       (QPalette.ColorRole.WindowText, "ink"), (QPalette.ColorRole.Text, "ink"),
                       (QPalette.ColorRole.ButtonText, "ink"), (QPalette.ColorRole.Highlight, "selected"),
                       (QPalette.ColorRole.HighlightedText, "accent"), (QPalette.ColorRole.PlaceholderText, "muted")):
        palette.setColor(role, QColor(COLORS[name]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(COLORS["disabled"]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(COLORS["disabled"]))
    app.setPalette(palette)
