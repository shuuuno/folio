"""Windows 테마와 관계없이 같은 명도/글꼴을 쓰는 네이티브 UI 토큰."""
from pathlib import Path
import os
import sys
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

COLORS = dict(ink="#202A3B", muted="#667187", accent="#4361DE", accent_hover="#3451C8",
              selected="#EBEFFE", border="#E1E5ED", canvas="#EDF0F5", surface="#FFFFFF", chrome="#F7F8FB")
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
    font.setPixelSize(13)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    font.setHintingPreference(QFont.HintingPreference.PreferVerticalHinting)
    app.setFont(font)
    palette = QPalette()
    for role, value in ((QPalette.ColorRole.Window,"#FFFFFF"),(QPalette.ColorRole.Base,"#FFFFFF"),
                        (QPalette.ColorRole.AlternateBase,"#F7F8FB"),(QPalette.ColorRole.Button,"#FFFFFF"),
                        (QPalette.ColorRole.WindowText,"#202A3B"),(QPalette.ColorRole.Text,"#202A3B"),
                        (QPalette.ColorRole.ButtonText,"#202A3B"),(QPalette.ColorRole.Highlight,"#EBEFFE"),
                        (QPalette.ColorRole.HighlightedText,"#3451C8"),(QPalette.ColorRole.PlaceholderText,"#667187")):
        palette.setColor(role, QColor(value))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#9CA6B6"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#9CA6B6"))
    app.setPalette(palette)
