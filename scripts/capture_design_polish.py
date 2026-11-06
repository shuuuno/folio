"""격리된 예제 문서로 실제 Qt 화면의 전후 비교와 배치 검증을 기록한다."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("before", "after"))
    parser.add_argument("--scale", default="1")
    parser.add_argument("--variant", choices=("bolder2", "font-picker"))
    parser.add_argument("--evidence-only", action="store_true")
    args = parser.parse_args()
    os.environ["QT_QPA_PLATFORM"] = "windows"
    os.environ["QT_SCALE_FACTOR"] = args.scale
    from PySide6.QtCore import QSettings, QPointF
    from paperlight.theme import create_application
    from paperlight.workspace import Workspace
    from paperlight.signature import SignatureDialog, png_bytes
    import pymupdf as fitz

    output = ROOT / "docs/design-polish"
    evidence_root = ROOT / "evidence/design-polish"
    if args.variant:
        output /= args.variant
        evidence_root /= args.variant
    evidence = evidence_root / f"{args.phase}-{args.scale}"
    if args.evidence_only:
        output = evidence
    output.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    source = evidence / "시작하기.pdf"
    shutil.copy2(ROOT / "assets/시작하기.pdf", source)
    app = create_application([])
    app.setStyle("Fusion")
    app.setApplicationName("FolioDesignPolishCheck")
    settings = QSettings(str(evidence / "settings.ini"), QSettings.Format.IniFormat)
    window = Workspace(data_dir=evidence / "data", settings=settings, tray_enabled=False)
    window.resize(1400, 960)
    window.show()
    records = []

    def settle():
        until = time.monotonic() + .65
        while time.monotonic() < until:
            app.processEvents()
            time.sleep(.01)

    def capture(name, widget=window):
        settle()
        path = output / f"{name}-{args.phase}.png" if args.scale == "1" else evidence / f"{name}.png"
        assert widget.grab().save(str(path))
        editor = window.current
        records.append(dict(
            name=name, path=str(path.relative_to(ROOT)),
            size=[widget.width(), widget.height()], dpr=widget.devicePixelRatioF(),
            inspector_width=editor.inspector.width(),
            inspector_horizontal_overflow=getattr(editor, "inspector_scroll", editor.inspector).horizontalScrollBar().maximum(),
            document_horizontal_overflow=editor.view.horizontalScrollBar().maximum(),
            apply_visible=editor.apply_button.isVisible(),
        ))

    try:
        capture("01-empty")
        window.open_files([source])
        editor = window.current
        capture("02-reading")
        editor.set_mode("edit")
        span = next(s for s in editor.model.page_spans(0) if 4 < len(s.text) < 50)
        editor.select_text(span)
        capture("03-edit")
        editor._clear_selection()
        editor.set_mode("text")
        editor.select_area(fitz.Rect(64, 470, 440, 540))
        editor.editor.setPlainText("검토를 마쳤습니다.\n확인 후 보관해 주세요.")
        capture("04-text")
        window.resize(960, 640)
        capture("05-compact")
        if args.phase == "after":
            assert window.size().width() == 960 and window.size().height() == 640
            assert editor.inspector_scroll.horizontalScrollBar().maximum() == 0
            assert editor.inspector.rect().contains(
                editor.apply_button.mapTo(editor.inspector, editor.apply_button.rect().center()))
            assert editor.view.horizontalScrollBar().maximum() == 0
            if hasattr(editor, "ribbon"):
                for control in list(editor.mode_buttons.values()) + [editor.search_box, editor.sidebar_button,
                                                                     editor.undo_button, editor.redo_button]:
                    assert editor.ribbon.rect().contains(control.mapTo(editor.ribbon, control.rect().topLeft()))
                    assert editor.ribbon.rect().contains(control.mapTo(editor.ribbon, control.rect().bottomRight()))
        editor._clear_selection()
        window.resize(1400, 960)
        editor.set_mode("view")
        window.show_conversion()
        dialog = window.conversion_dialog
        dialog.use_current()
        dialog.destination.setText(str(evidence))
        capture("06-conversion", dialog)
        dialog.hide()
        signature = SignatureDialog(editor, evidence / "data/signature.png")
        signature.show()
        settle()
        pad = signature.pad
        pad.last = QPointF(190, 280)
        for x, y in [(230, 150), (250, 300), (330, 180), (300, 290), (390, 240), (450, 260), (520, 160), (480, 300), (640, 260), (820, 210)]:
            pad.stroke(QPointF(x, y))
        capture("07-signature", signature)
        editor.signature_data = png_bytes(pad.result())
        signature.close()
        editor.model.add_text(0, (64, 470, 440, 540), "검토를 마쳤습니다.")
        editor.after_edit()
        editor.set_mode("object")
        obj = editor.model.page_objects(0)[0]
        editor.select_object(obj["id"])
        capture("08-placement")
    finally:
        for i in range(window.tabs.count()):
            current = window.tabs.widget(i)
            current._clear_selection()
            current.model.saved_revision = current.model.revision
        window.exiting = True
        window.close()
        app.processEvents()
    (evidence / "captures.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(dict(phase=args.phase, scale=args.scale, screenshots=len(records), evidence=str(evidence)), ensure_ascii=False))


if __name__ == "__main__":
    main()
