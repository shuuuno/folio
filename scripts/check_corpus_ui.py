"""Public corpus in the actual Qt Windows app; no external OS input automation."""
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["QT_QPA_PLATFORM"] = "windows"
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEventLoop, QTimer
from paperlight.window import MainWindow

app = QApplication([])
app.setStyle("Fusion")
app.setApplicationName("PaperlightCompatibility")
window = MainWindow()
out = ROOT / "evidence/compatibility/ui"
out.mkdir(exist_ok=True)
errors = []
sys.excepthook = lambda *exc: errors.append("".join(traceback.format_exception(*exc)))
window.error = lambda exc: errors.append(str(exc))
results = []


def settle():
    loop = QEventLoop()
    QTimer.singleShot(250, loop.quit)
    loop.exec()


try:
    window.show()
    settle()
    for name, page, query in [("korean-curriculum.pdf", 4, "한국어"),
                              ("korean-curriculum.pdf", 33, "듣기"),
                              ("hog-manual-bilingual.pdf", 96, "Employment"),
                              ("archives-declaration.pdf", 0, "")]:
        assert window.open_file(ROOT / "research/corpus" / name)
        if query:
            window.search_box.setText(query)
            window.search()
            assert window._search_hits
        hits = len(window._search_hits)
        window.search_box.clear()
        assert window.go_page(page)
        window.fit_width()
        settle()
        assert window.page_input.value() == page + 1
        assert not window.view.page_item.pixmap().isNull()
        assert not window.thumbnails.item(page).icon().isNull()
        assert window.isVisible() and window.winId()
        window.grab().save(str(out / f"{Path(name).stem}-{page+1}.png"))
        assert not errors, errors
        results.append(dict(file=name, page=page+1, search_hits=hits,
                            visible=True, page_rendered=True, thumbnail_rendered=True))
    (out / "results.json").write_text(json.dumps(dict(passed=True, qt_platform=app.platformName(),
        scope="app-internal calls on real Windows window, no OS mouse/keyboard automation", cases=results),
        indent=2), encoding="utf-8")
finally:
    window.confirm_discard = lambda: True
    window.close()
    if window.model.doc:
        window.model.doc.close()
