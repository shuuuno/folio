"""배포 실행 파일 자체의 offscreen / Windows 네이티브 검증 진입점."""
from .theme import create_application
import json
import os
from pathlib import Path
import sys
import time
import traceback


def verify(output: Path, native=False):
    os.environ["QT_QPA_PLATFORM"] = "windows" if native else "offscreen"
    from PySide6.QtCore import Qt, QTimer, QEventLoop, QMimeData, QUrl, QPoint, QPointF, QSize
    from PySide6.QtGui import QImage, QPainter, QColor, QPen, QInputMethodEvent, QDragEnterEvent, QDropEvent, QIcon
    from .signature import png_bytes
    from .window import MainWindow
    from . import __version__
    import pymupdf as fitz
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    app = create_application([])
    app.setStyle("Fusion")
    app.setApplicationName("Paperlight")
    app.setOrganizationName("Paperlight")
    window = MainWindow()
    window.data_dir = output.resolve() / "test-appdata"
    errors = []
    window.error = lambda exc: errors.append(str(exc))
    def settle():
        loop = QEventLoop()
        QTimer.singleShot(150, loop.quit)
        loop.exec()
    try:
        root = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1] / "assets"
        window.show()
        settle()
        assert window.open_file(root / "시작하기.pdf")
        app.processEvents()
        window.set_mode("edit")
        settle()
        assert window.size_input.lineEdit().width() > 30
        assert window.page_input.lineEdit().width() > 10
        selected = next(s for s in window.model.page_spans(0) if s.text == "담당자: 김하늘")
        window.select_text(selected)
        window.editor.clear()
        window.editor.setFocus()
        app.sendEvent(window.editor, QInputMethodEvent("담", []))
        assert not window.editor.toPlainText()
        commit = QInputMethodEvent()
        commit.setCommitString("담당자: 이서준")
        app.sendEvent(window.editor, commit)
        assert window.editor.toPlainText() == "담당자: 이서준"
        window.geometry_inputs["width"].setValue(180)
        window.refresh_text_preview()
        assert window.view.preview_rendered
        assert "담당자: 김하늘" in window.model.doc[0].get_text()
        app.processEvents()
        window.grab().save(str(output / "edit-preview.png"))
        window.apply_button.click()
        assert not errors, errors
        window.set_mode("text")
        window.select_area(fitz.Rect(64, 480, 500, 550))
        window.editor.setPlainText("실행 파일 검증 완료")
        window.apply_button.click()
        assert not errors, errors
        image = QImage(320, 100, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        p = QPainter(image)
        p.setPen(QPen(QColor("#203545"), 3))
        p.drawLine(20, 70, 100, 20)
        p.drawLine(100, 20, 130, 80)
        p.drawLine(130, 80, 270, 35)
        p.end()
        window.signature_data = png_bytes(image)
        window.set_mode("sign")
        window.select_area(fitz.Rect(165, 660, 375, 700))
        window.apply_button.click()
        assert not errors, errors
        destination = output / "패키지-검증.pdf"
        window.model.save(destination)
        with fitz.open(destination) as doc:
            assert "담당자: 김하늘" not in doc[0].get_text()
            assert "담당자: 이서준" in doc[0].get_text()
            assert "실행 파일 검증 완료" in doc[0].get_text()
            assert len(doc[0].get_images()) > 0
        window.set_mode("view")
        window.fit_mode = False
        window.fit_timer.stop()
        window.zoom = .78
        window.zoom_label.setText("78%")
        window.view.show_page()
        settle()
        assert window.isVisible()
        assert window.page_input.value() == 1
        assert window.page_input.text().strip() == "1"
        assert not window.thumbnails.item(1).icon().isNull()
        icon = window.thumbnails.item(0).icon()
        assert icon.pixmap(QSize(110, 160), QIcon.Mode.Normal).toImage() == icon.pixmap(QSize(110, 160), QIcon.Mode.Selected).toImage()
        window.grab().save(str(output / "packaged-app.png"))
        selection = window.view.selection_model()
        target = "담당자: 이서준"
        start = "".join(c.text for c in selection.characters).index(target)
        selection.select(start, start + len(target))
        window.view.paint_read_selection()
        assert selection.text == target
        app.processEvents()
        window.grab().save(str(output / "reading-selection.png"))
        window.search_box.setText("문서")
        window.search(1)
        count = len(window._search_hits)
        assert count > 1
        window.search(-1)
        assert window._search_cursor == count - 1
        window.search(1)
        assert window._search_cursor == 0
        app.processEvents()
        window.grab().save(str(output / "search-results.png"))
        window.set_mode("edit")
        window.select_text(next(s for s in window.model.page_spans(0) if s.text == "실행 파일 검증 완료"))
        window.editor.clear()
        window.refresh_text_preview()
        assert "삭제 미리보기" in window.preview_note.text()
        assert "실행 파일 검증 완료" in window.model.doc[0].get_text()
        window.apply_button.click()
        assert not errors, errors
        deleted = output / "삭제-검증.pdf"
        window.model.save(deleted)
        with fitz.open(deleted) as doc:
            assert "실행 파일 검증 완료" not in doc[0].get_text()
            assert "담당자: 이서준" in doc[0].get_text()
        window.undo_button.click()
        assert "실행 파일 검증 완료" in window.model.doc[0].get_text()
        window.set_mode("object")
        text_object = next(o for o in window.model.page_objects(0) if o["kind"] == "text")
        assert window.select_object(text_object["id"])
        window.geometry_inputs["y"].setValue(500)
        window.geometry_inputs["width"].setValue(390)
        window.editor.setPlainText("배치 편집 후 다시 저장")
        window.refresh_text_preview()
        assert window.view.preview_rendered
        settle()
        window.grab().save(str(output / "object-preview.png"))
        assert window.apply_edit()
        sign = next(o for o in window.model.page_objects(0) if o["kind"] == "signature")
        assert window.select_object(sign["id"])
        window.geometry_inputs["x"].setValue(240)
        window.geometry_inputs["width"].setValue(160)
        assert window.apply_edit()
        arranged = output / "배치-검증.pdf"
        window.model.save(arranged)
        assert window.open_file(arranged)
        window.set_mode("object")
        assert window.select_object(sign["id"])
        assert window.delete_selected_object()
        assert all(o["id"] != sign["id"] for o in window.model.page_objects(0))
        window.undo_button.click()
        assert any(o["id"] == sign["id"] for o in window.model.page_objects(0))
        assert not errors, errors
        # App-level drag/drop delivery, not an OS Explorer mouse gesture.
        window.model.saved_revision = window.model.revision
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(destination.resolve()))])
        enter = QDragEnterEvent(QPoint(20, 20), Qt.DropAction.CopyAction, mime,
                                Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        app.sendEvent(window, enter)
        assert enter.isAccepted()
        drop = QDropEvent(QPointF(20, 20), Qt.DropAction.CopyAction, mime,
                          Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        app.sendEvent(window, drop)
        assert drop.isAccepted()
        assert window.model.path == destination.resolve()
        report = {"passed": True, "version": __version__, "frozen": bool(getattr(sys, "frozen", False)),
                  "platform": sys.platform, "qt_platform": app.platformName(),
                  "window_visible": window.isVisible(), "native_window_created": bool(window.winId()) if native else None,
                  "elapsed_seconds": round(time.perf_counter() - started, 2),
                  "input_method_scope": "synthetic Qt preedit/commit events, not Windows IME",
                  "drag_drop_scope": "synthetic Qt events, not Explorer gesture",
                  "checks": ["한글 UI 구성", "PDF 열기", "기존 한글 제거와 교체", "텍스트 추가", "투명 서명 삽입", "PDF 저장 및 재개방",
                             "텍스트 선택", "검색 이전/다음", "본문 삭제 미리보기·저장·실행 취소", "Qt 한글 조합·확정 이벤트", "Qt PDF 드롭 수락", "선택 썸네일 색 보존",
                             "추가 텍스트·서명 이동·크기 조절", "배치 미리보기", "저장 후 항목 재선택·삭제·실행 취소"]}
        (output / "package-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0
    except Exception:
        (output / "package-error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        return 1
    finally:
        window.model.saved_revision = window.model.revision
        window.close()
