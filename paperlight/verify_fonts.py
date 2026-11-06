"""설정·문서·복구 경로를 격리한 글꼴 선택기 실행 검증."""
from io import BytesIO
import json
import os
from pathlib import Path
import shutil
import sys
import time


def verify(output, native=False):
    os.environ["QT_QPA_PLATFORM"] = "windows" if native else "offscreen"
    from PySide6.QtCore import QSettings
    from fontTools.ttLib import TTFont
    import pymupdf as fitz
    from .theme import create_application
    from .workspace import Workspace
    from .fonts import installed_fonts, default_font_id, embedding_allowed

    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    root = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1] / "assets"
    source = output / "글꼴 검증.pdf"
    shutil.copy2(root / "시작하기.pdf", source)
    app = create_application([])
    app.setStyle("Fusion")
    settings = QSettings(str(output / "settings.ini"), QSettings.Format.IniFormat)
    preferences = QSettings(str(output / "data/preferences.ini"), QSettings.Format.IniFormat)
    preferences.remove("lastTextFont")
    preferences.sync()
    window = Workspace(data_dir=output / "data", settings=settings, tray_enabled=False)
    result = dict(passed=False, native=native, frozen=bool(getattr(sys, "frozen", False)))

    def settle():
        until = time.monotonic() + .5
        while time.monotonic() < until:
            app.processEvents()
            time.sleep(.01)

    try:
        window.resize(1400, 960)
        window.show()
        window.open_files([source])
        editor = window.current
        editor.set_mode("text")
        settle()
        assert editor.selected_font_id == default_font_id()
        choices = installed_fonts()
        assert len(choices) > 1
        key = default_font_id(True)
        index = editor.font_combo.findData(key)
        assert index >= 0
        editor.font_combo.setCurrentIndex(index)
        editor.select_area(fitz.Rect(64, 470, 440, 540))
        editor.editor.setPlainText("선택한 글꼴로 한글을 입력합니다.\n저장 후에도 글꼴이 유지됩니다.")
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            app.processEvents()
            if editor.view.preview_rendered and not editor.preview_timer.isActive() and not editor.fit_timer.isActive():
                break
            time.sleep(.01)
        assert editor.view.preview_rendered and not editor.preview_timer.isActive()
        assert editor.preview_note.text().startswith("미리보기 ·")
        assert window.grab().save(str(output / "font-picker.png"))
        window.resize(960, 640)
        settle()
        assert window.width() == 960 and window.height() == 640
        editor.inspector_scroll.ensureWidgetVisible(editor.font_combo)
        settle()
        assert editor.inspector_scroll.viewport().rect().contains(
            editor.font_combo.mapTo(editor.inspector_scroll.viewport(), editor.font_combo.rect().center()))
        assert editor.inspector.rect().contains(
            editor.apply_button.mapTo(editor.inspector, editor.apply_button.rect().center()))
        assert editor.apply_edit()
        target = output / "선택 글꼴 결과.pdf"
        assert editor.save_to(target)
        assert editor.open_file(target)
        item = editor.model.page_objects(0)[0]
        resource = next(f for f in editor.model.doc[0].get_fonts() if f[4] == item["resource"][1])
        with TTFont(BytesIO(editor.model.doc.extract_font(resource[0])[3])) as embedded:
            assert embedding_allowed(embedded["OS/2"].fsType)
            assert embedded.getBestCmap().get(ord("한"))
        assert "Bold" in item["font_name"]
        editor.set_mode("object")
        editor.select_object(item["id"])
        editor.editor.setPlainText("다시 편집한 한글")
        assert editor.apply_edit()
        assert "Bold" in editor.model.page_objects(0)[0]["font_name"]
        editor.set_mode("text")
        assert editor.selected_font_id == key
        result.update(passed=True, installed_faces=len(choices), default_malgun=True,
                      chosen_font_embedded=True, korean_roundtrip=True,
                      reopened_object_preserves_font=True, last_choice_remembered=True, laptop_picker_accessible=True,
                      dpr=window.devicePixelRatioF(), selected_label=editor.font_combo.currentText())
    finally:
        for i in range(window.tabs.count()):
            current = window.tabs.widget(i)
            current._clear_selection()
            current.model.saved_revision = current.model.revision
        window.exiting = True
        window.close()
        app.processEvents()
        (output / "font-check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0
