import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import pymupdf as fitz
from PySide6.QtCore import Qt, QPointF, QPoint, QMimeData, QUrl, QSize
from PySide6.QtGui import QInputMethodEvent, QDragEnterEvent, QDropEvent, QIcon
from PySide6.QtWidgets import QApplication, QFileDialog
from PySide6.QtTest import QTest

from paperlight.window import MainWindow
from paperlight.signature import SignatureDialog
from fixtures import make_pdf


APP = QApplication.instance() or QApplication([])
APP.setStyle("Fusion")
APP.setApplicationName("PaperlightTests")


class UiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "input.pdf"
        make_pdf(self.source, subset=True)
        self.window = MainWindow()
        self.window.data_dir = self.root / "appdata"
        self.window.show()
        APP.processEvents()
        self.errors = []
        self.window.error = lambda exc: self.errors.append(str(exc))
        self.assertTrue(self.window.open_file(self.source))
        APP.processEvents()
        self.window.zoom = .75
        self.window.fit_mode = False
        self.window.fit_timer.stop()
        self.window.view.show_page()

    def tearDown(self):
        self.window.confirm_discard = lambda: True
        self.window.model.saved_revision = self.window.model.revision
        self.window.close()
        self.window.model.doc.close()
        APP.processEvents()
        self.temp.cleanup()

    def click_pdf(self, x, y):
        page = self.window.model.doc[self.window.page_number]
        p = fitz.Point(x, y) * page.rotation_matrix
        point = self.window.view.mapFromScene(QPointF(p.x, p.y))
        QTest.mouseClick(self.window.view.viewport(), Qt.MouseButton.LeftButton, pos=point)
        APP.processEvents()

    def drag_pdf(self, a, b):
        start = self.window.view.mapFromScene(QPointF(*a))
        end = self.window.view.mapFromScene(QPointF(*b))
        QTest.mousePress(self.window.view.viewport(), Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(self.window.view.viewport(), end)
        QTest.mouseRelease(self.window.view.viewport(), Qt.MouseButton.LeftButton, pos=end)
        APP.processEvents()

    def test_full_edit_signature_save_flow(self):
        w = self.window
        QTest.mouseClick(w.mode_buttons["edit"], Qt.MouseButton.LeftButton)
        span = next(s for s in w.model.page_spans(0) if s.text == "담당자: 김하늘")
        self.click_pdf((span.bbox[0] + span.bbox[2]) / 2, (span.bbox[1] + span.bbox[3]) / 2)
        self.assertEqual(w.editor.toPlainText(), span.text)
        w.editor.setPlainText("담당자: 이서준")
        w.geometry_inputs["width"].setValue(185)
        QTest.mouseClick(w.apply_button, Qt.MouseButton.LeftButton)
        self.assertEqual(self.errors, [])
        self.assertIn("담당자: 이서준", w.model.doc[0].get_text())
        QTest.mouseClick(w.mode_buttons["text"], Qt.MouseButton.LeftButton)
        self.drag_pdf((64, 480), (500, 555))
        w.editor.setPlainText("검토를 마쳤습니다.\n서명 후 보관해 주세요.")
        QTest.mouseClick(w.apply_button, Qt.MouseButton.LeftButton)
        self.assertEqual(self.errors, [])
        self.assertIn("검토를 마쳤습니다.", w.model.doc[0].get_text())

        dialog = SignatureDialog(w, self.root / "signature.png")
        dialog.show()
        APP.processEvents()
        QTest.mousePress(dialog.pad, Qt.MouseButton.LeftButton, pos=QPoint(70, 100))
        for x, y in [(100, 70), (120, 150), (155, 80), (185, 140), (230, 95), (300, 125), (390, 85)]:
            QTest.mouseMove(dialog.pad, QPoint(x, y))
        QTest.mouseRelease(dialog.pad, Qt.MouseButton.LeftButton, pos=QPoint(390, 85))
        dialog.use()
        self.assertTrue(dialog.data)
        self.assertTrue((self.root / "signature.png").exists())
        w.signature_data = dialog.data
        QTest.mouseClick(w.mode_buttons["sign"], Qt.MouseButton.LeftButton)
        self.drag_pdf((165, 658), (375, 700))
        self.assertIsNotNone(w.area)
        QTest.mouseClick(w.apply_button, Qt.MouseButton.LeftButton)
        self.assertEqual(self.errors, [])
        self.assertGreater(len(w.model.doc[0].get_images()), 0)
        target = self.root / "output.pdf"
        with patch.object(QFileDialog, "getSaveFileName", return_value=(str(target), "PDF")):
            QTest.mouseClick(w.save_button, Qt.MouseButton.LeftButton)
        self.assertTrue(target.exists())
        self.assertFalse(w.model.dirty)
        with fitz.open(target) as doc:
            self.assertNotIn("담당자: 김하늘", doc[0].get_text())
            self.assertIn("담당자: 이서준", doc[0].get_text())
            self.assertIn("검토를 마쳤습니다.", doc[0].get_text())
        evidence = Path(__file__).resolve().parents[1] / "evidence"
        evidence.mkdir(exist_ok=True)
        (evidence / "편집-검증.pdf").write_bytes(target.read_bytes())
        w.set_mode("edit")
        w.filename.setText("프로젝트 검토서.pdf")
        w.select_text(next(s for s in w.model.page_spans(0) if s.text == "담당자: 이서준"))
        w.zoom = .78
        w.zoom_label.setText("78%")
        w.view.show_page()
        w.update_preview()
        APP.processEvents()
        w.grab().save(str(evidence / "editor.png"))
        with fitz.open(target) as doc:
            doc[0].get_pixmap(matrix=fitz.Matrix(1.4, 1.4)).save(str(evidence / "saved-page.png"))

    def test_rotated_text_selection_search_navigation_undo(self):
        w = self.window
        w.model.doc[0].set_rotation(90)
        w.set_mode("edit")
        span = next(s for s in w.model.page_spans(0) if s.text == "Project status: Draft")
        self.click_pdf((span.bbox[0] + span.bbox[2]) / 2, (span.bbox[1] + span.bbox[3]) / 2)
        self.assertEqual(w.editor.toPlainText(), span.text)
        w.editor.setPlainText("Project status: Final")
        w.geometry_inputs["width"].setValue(210)
        w.apply_edit()
        self.assertEqual(self.errors, [])
        w.undo_button.click()
        self.assertIn("Project status: Draft", w.model.doc[0].get_text())
        w.redo_button.click()
        self.assertIn("Project status: Final", w.model.doc[0].get_text())
        w.search_box.setText("두 번째")
        w.search()
        self.assertEqual(w.page_number, 1)
        self.assertEqual(w.page_input.value(), 2)
        w.go_page(0)
        self.assertEqual(w.page_number, 0)

    def test_welcome_screenshot(self):
        self.window.stack.setCurrentIndex(0)
        self.window.filename.setText("나만의 PDF 작업 공간")
        evidence = Path(__file__).resolve().parents[1] / "evidence"
        evidence.mkdir(exist_ok=True)
        self.window.grab().save(str(evidence / "welcome.png"))

    def prepare_draft(self):
        w = self.window
        w.set_mode("edit")
        span = next(s for s in w.model.page_spans(0) if s.text == "담당자: 김하늘")
        w.select_text(span)
        w.editor.setPlainText("담당자: 이서준")
        w.geometry_inputs["width"].setValue(185)
        return span

    def test_save_includes_unapplied_input(self):
        self.prepare_draft()
        target = self.root / "draft-saved.pdf"
        with patch.object(QFileDialog, "getSaveFileName", return_value=(str(target), "PDF")):
            self.assertTrue(self.window.save_as())
        with fitz.open(target) as doc:
            self.assertIn("담당자: 이서준", doc[0].get_text())
            self.assertNotIn("담당자: 김하늘", doc[0].get_text())

    def test_clicking_same_text_preserves_input(self):
        span = self.prepare_draft()
        self.window.select_text(span)
        self.assertEqual(self.window.editor.toPlainText(), "담당자: 이서준")

    def test_open_resets_page_controls(self):
        w = self.window
        w.go_page(1)
        self.assertEqual(w.page_input.value(), 2)
        w.open_file(self.source)
        self.assertEqual(w.page_number, 0)
        self.assertEqual(w.page_input.value(), 1)

    def test_cancel_page_navigation_retains_draft_and_controls(self):
        self.prepare_draft()
        w = self.window
        w._ask_draft_action = lambda: "cancel"
        w.page_input.setValue(2)
        self.assertEqual(w.page_number, 0)
        self.assertEqual(w.page_input.value(), 1)
        self.assertEqual(w.thumbnails.currentRow(), 0)
        self.assertEqual(w.editor.toPlainText(), "담당자: 이서준")

    def test_failed_pending_edit_prevents_save(self):
        self.prepare_draft()
        w = self.window
        w.editor.setPlainText("너무 긴 문장 " * 100)
        target = self.root / "must-not-save.pdf"
        with patch.object(QFileDialog, "getSaveFileName", return_value=(str(target), "PDF")):
            self.assertFalse(w.save_as())
        self.assertFalse(target.exists())
        self.assertEqual(len(self.errors), 1)

    def test_cancel_mode_change_restores_selected_tool(self):
        self.prepare_draft()
        w = self.window
        w._ask_draft_action = lambda: "cancel"
        w.mode_buttons["view"].click()
        self.assertEqual(w.mode, "edit")
        self.assertTrue(w.mode_buttons["edit"].isChecked())
        self.assertEqual(w.editor.toPlainText(), "담당자: 이서준")

    def test_preview_is_isolated_and_matches_applied_page(self):
        self.prepare_draft()
        w = self.window
        w.refresh_text_preview()
        self.assertTrue(w.view.preview_rendered)
        before = w.view.page_item.pixmap().toImage()
        self.assertIn("담당자: 김하늘", w.model.doc[0].get_text())
        self.assertNotIn("담당자: 이서준", w.model.doc[0].get_text())
        self.assertFalse(w.model.dirty)
        self.assertFalse(w.model.can_undo)
        w.apply_edit()
        after = w.view.page_item.pixmap().toImage()
        self.assertEqual(before, after)

    def test_invalid_preview_keeps_original_and_draft(self):
        self.prepare_draft()
        w = self.window
        original = w.view.page_item.pixmap().toImage()
        w.editor.setPlainText("너무 긴 문장 " * 100)
        w.refresh_text_preview()
        self.assertIn("적용할 수 없음", w.preview_note.text())
        self.assertEqual(original, w.view.page_item.pixmap().toImage())
        self.assertFalse(w.model.dirty)
        self.assertTrue(w.has_draft)

    def test_apply_and_discard_pending_navigation(self):
        self.prepare_draft()
        w = self.window
        w._ask_draft_action = lambda: "apply"
        self.assertTrue(w.go_page(1))
        self.assertIn("담당자: 이서준", w.model.doc[0].get_text())
        w.set_mode("text")
        w.editor.setPlainText("버릴 입력")
        w._ask_draft_action = lambda: "discard"
        w.go_page(0)
        self.assertFalse(w.has_draft)
        self.assertNotIn("버릴 입력", w.model.doc[1].get_text())

    def test_unmodified_selection_is_not_pending(self):
        w = self.window
        w.set_mode("edit")
        w.select_text(next(s for s in w.model.page_spans(0) if s.text == "담당자: 김하늘"))
        self.assertFalse(w.has_draft)
        self.assertEqual(w.preview_note.text(), "")
        self.assertFalse(w.preview_timer.isActive())

    def test_undo_from_other_page_refreshes_changed_thumbnail(self):
        self.prepare_draft()
        w = self.window
        w.apply_edit()
        APP.processEvents()
        changed = w.thumbnails.item(0).icon().cacheKey()
        w.go_page(1)
        w.undo()
        APP.processEvents()
        self.assertIn("담당자: 김하늘", w.model.doc[0].get_text())
        self.assertNotEqual(changed, w.thumbnails.item(0).icon().cacheKey())

    def select_read_text(self, text, reverse=False):
        w = self.window
        w.set_mode("view")
        span = next(s for s in w.model.page_spans(0) if s.text == text)
        box = fitz.Rect(span.bbox)
        a = fitz.Point(box.x0 + .2, (box.y0 + box.y1) / 2) * w.model.doc[0].rotation_matrix
        b = fitz.Point(box.x1 - .2, (box.y0 + box.y1) / 2) * w.model.doc[0].rotation_matrix
        self.drag_pdf(tuple(b if reverse else a), tuple(a if reverse else b))
        return w.view.read_selection.text

    def test_read_drag_copy_zoom_and_page_change(self):
        w = self.window
        self.assertEqual(self.select_read_text("담당자: 김하늘"), "담당자: 김하늘")
        with patch("paperlight.window.QApplication.clipboard") as clipboard:
            QTest.keyClick(w.view, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
            clipboard.return_value.setText.assert_called_once_with("담당자: 김하늘")
        w.change_zoom(1.2)
        self.assertEqual(w.view.read_selection.text, "담당자: 김하늘")
        self.assertGreater(len(w.view.read_marks), 0)
        self.assertFalse(w.model.dirty)
        w.go_page(1)
        with patch("paperlight.window.QApplication.clipboard") as clipboard:
            self.assertFalse(w.view.copy_selected_text())
            clipboard.assert_not_called()

    def test_rotated_reverse_read_selection(self):
        w = self.window
        w.model.doc[0].set_rotation(90)
        w.view.show_page()
        self.assertEqual(self.select_read_text("Project status: Draft", reverse=True), "Project status: Draft")

    def test_read_selection_preserves_line_breaks(self):
        w = self.window
        spans = w.model.page_spans(0)
        first = next(s for s in spans if s.text == "검토 상태: 확인 대기")
        last = next(s for s in spans if s.text == "담당자: 김하늘")
        self.drag_pdf((first.bbox[0] + .2, (first.bbox[1] + first.bbox[3]) / 2),
                      (last.bbox[2] - .2, (last.bbox[1] + last.bbox[3]) / 2))
        self.assertEqual(w.view.read_selection.text, "검토 상태: 확인 대기\n담당자: 김하늘")

    def test_read_copy_respects_pdf_permission(self):
        w = self.window
        locked = self.root / "copy-locked.pdf"
        w.model.doc.save(locked, encryption=fitz.PDF_ENCRYPT_AES_256,
                         owner_pw="owner", user_pw="reader", permissions=fitz.PDF_PERM_PRINT)
        w.model.open(locked, "reader")
        w.view.show_page()
        self.assertEqual(self.select_read_text("담당자: 김하늘"), "담당자: 김하늘")
        with patch("paperlight.window.QApplication.clipboard") as clipboard:
            self.assertFalse(w.view.copy_selected_text())
            clipboard.assert_not_called()

    def test_search_forward_backward_wrap_and_highlight_zoom(self):
        w = self.window
        w.search_box.setText("본문")
        w.search()
        self.assertEqual(w.search_count.text(), "1 / 1")
        self.assertEqual(w.page_number, 1)
        w.search_box.setText("문서")
        w.go_page(0)
        w.search()
        count = len(w._search_hits)
        self.assertGreater(count, 1)
        self.assertEqual(w._search_cursor, 0)
        w.search(-1)
        self.assertEqual(w._search_cursor, count - 1)
        w.search(1)
        self.assertEqual(w._search_cursor, 0)
        hit = w.search_hit
        w.change_zoom(1.1)
        self.assertEqual(w.search_hit, hit)
        self.assertIsNotNone(w.view.preview)
        w.search_box.setText("없는문자열999")
        w.search()
        self.assertEqual(w.search_count.text(), "0 / 0")
        self.assertIsNone(w.search_hit)

    def test_delete_preview_save_and_search_invalidation(self):
        self.prepare_draft()
        w = self.window
        w.editor.clear()
        w.refresh_text_preview()
        self.assertIn("삭제 미리보기", w.preview_note.text())
        self.assertEqual(w.apply_button.text(), "본문 삭제 적용")
        self.assertIn("담당자: 김하늘", w.model.doc[0].get_text())
        target = self.root / "deleted-ui.pdf"
        with patch.object(QFileDialog, "getSaveFileName", return_value=(str(target), "PDF")):
            self.assertTrue(w.save_as())
        with fitz.open(target) as saved:
            self.assertNotIn("담당자: 김하늘", saved[0].get_text())
        w.search_box.setText("담당자")
        w.search()
        self.assertEqual(w.search_count.text(), "0 / 0")
        w.undo_button.click()
        w.search()
        self.assertEqual(w.search_count.text(), "1 / 1")

    def test_input_method_preedit_commit_and_unicode_save(self):
        # Synthetic Qt input-method events; this does not exercise Windows IME.
        w = self.window
        self.prepare_draft()
        w.editor.clear()
        w.editor.setFocus()
        APP.sendEvent(w.editor, QInputMethodEvent("ㅎ", []))
        self.assertEqual(w.editor.toPlainText(), "")
        APP.sendEvent(w.editor, QInputMethodEvent("한", []))
        commit = QInputMethodEvent()
        commit.setCommitString("한글 입력 확인")
        APP.sendEvent(w.editor, commit)
        self.assertEqual(w.editor.toPlainText(), "한글 입력 확인")
        target = self.root / "한글 공백 경로" / "계약서 검토 완료.pdf"
        target.parent.mkdir()
        with patch.object(QFileDialog, "getSaveFileName", return_value=(str(target), "PDF")):
            self.assertTrue(w.save_as())
        with fitz.open(target) as saved:
            self.assertIn("한글 입력 확인", saved[0].get_text())
        self.assertEqual(self.errors, [])

    def test_open_dialog_unicode_path_and_cancel(self):
        path = self.root / "한글 문서 (1).PDF"
        path.write_bytes(self.source.read_bytes())
        with patch.object(QFileDialog, "getOpenFileName", return_value=(str(path), "PDF")):
            self.window.open_dialog()
        self.assertEqual(self.window.model.path, path)
        self.prepare_draft()
        with patch.object(QFileDialog, "getOpenFileName", return_value=("", "")):
            self.window.open_dialog()
        self.assertEqual(self.window.model.path, path)
        self.assertTrue(self.window.has_draft)

    def drop(self, url):
        mime = QMimeData()
        mime.setUrls([url])
        enter = QDragEnterEvent(QPoint(20, 20), Qt.DropAction.CopyAction, mime,
                                Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        APP.sendEvent(self.window, enter)
        drop = QDropEvent(QPointF(20, 20), Qt.DropAction.CopyAction, mime,
                          Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        if enter.isAccepted():
            APP.sendEvent(self.window, drop)
        return enter.isAccepted(), drop.isAccepted()

    def test_drop_unicode_pdf_reports_acceptance(self):
        path = self.root / "한글 공백 파일.PDF"
        path.write_bytes(self.source.read_bytes())
        self.assertEqual(self.drop(QUrl.fromLocalFile(str(path))), (True, True))
        self.assertEqual(self.window.model.path, path)

    def test_selected_thumbnail_preserves_document_colors(self):
        APP.processEvents()
        icon = self.window.thumbnails.item(0).icon()
        self.assertFalse(icon.isNull())
        size = QSize(110, 160)
        self.assertEqual(icon.pixmap(size, QIcon.Mode.Normal).toImage(),
                         icon.pixmap(size, QIcon.Mode.Selected).toImage())

    def test_large_to_small_document_switch_cancels_old_thumbnails(self):
        long_path = self.root / "long.pdf"
        with fitz.open() as doc:
            for i in range(60):
                page = doc.new_page()
                page.insert_text((30, 50), str(i + 1))
            doc.save(long_path)
        w = self.window
        callbacks = []
        with patch.object(sys, "excepthook", lambda *error: callbacks.append(error)):
            w.open_file(long_path)
            w.go_page(49)
            for _ in range(4):
                APP.processEvents()
            w.open_file(self.source)
            for _ in range(4):
                APP.processEvents()
        self.assertEqual(callbacks, [])
        self.assertEqual(w.thumbnails.count(), 2)
        self.assertEqual(w.page_input.value(), 1)
        self.assertFalse(w.thumbnails.item(0).icon().isNull())

    def prepare_object(self):
        w = self.window
        oid = w.model.add_text(0, (64, 480, 364, 540), "옮길 텍스트", 14)
        w.after_edit()
        w.set_mode("object")
        self.click_pdf(100, 500)
        self.assertEqual(w.selected_object["id"], oid)
        self.assertFalse(w.has_draft)
        return oid

    def test_object_drag_resize_preview_save_reopen_delete_undo(self):
        w = self.window
        oid = self.prepare_object()
        self.drag_pdf((100, 500), (130, 530))
        self.assertTrue(w.has_draft)
        self.assertAlmostEqual(w.area.x0, 94, delta=2)
        w.refresh_text_preview()
        preview = w.view.page_item.pixmap().toImage()
        self.assertEqual(w.model.page_objects(0)[0]["rect"], [64, 480, 364, 540])
        self.assertTrue(w.apply_edit())
        self.assertEqual(w.view.page_item.pixmap().toImage(), preview)
        w.select_object(oid)
        corner = (w.area.x1, w.area.y1)
        self.drag_pdf(corner, (corner[0]+40, corner[1]+20))
        self.assertAlmostEqual(w.area.width, 340, delta=2)
        w.editor.setPlainText("이동 후 내용 변경")
        target = self.root / "배치 저장.pdf"
        with patch.object(QFileDialog, "getSaveFileName", return_value=(str(target), "PDF")):
            self.assertTrue(w.save_as())
        self.assertTrue(w.open_file(target))
        w.set_mode("object")
        self.assertTrue(w.select_object(oid))
        self.assertEqual(w.editor.toPlainText(), "이동 후 내용 변경")
        w.view.setFocus()
        QTest.keyClick(w.view, Qt.Key.Key_Delete)
        self.assertEqual(w.model.page_objects(0), [])
        w.undo()
        self.assertEqual(w.model.page_objects(0)[0]["id"], oid)
        self.assertEqual(self.errors, [])

    def test_object_pending_navigation_cancel_and_failed_resize(self):
        w = self.window
        oid = self.prepare_object()
        w.geometry_inputs["x"].setValue(100)
        w._ask_draft_action = lambda: "cancel"
        self.assertFalse(w.go_page(1))
        self.assertEqual(w.selected_object["id"], oid)
        w.geometry_inputs["width"].setValue(2)
        w.geometry_inputs["height"].setValue(2)
        self.assertFalse(w.apply_edit())
        self.assertEqual(w.model.page_objects(0)[0]["rect"], [64, 480, 364, 540])
        self.assertEqual(len(self.errors), 1)

    def test_signature_object_drag_on_rotated_page(self):
        w = self.window
        pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 40), False)
        pix.clear_with(80)
        w.model.doc[0].set_rotation(90)
        oid = w.model.add_signature(0, (64, 480, 264, 560), pix.tobytes("png"))
        w.after_edit()
        w.set_mode("object")
        self.click_pdf(100, 500)
        self.assertEqual(w.selected_object["id"], oid)
        self.assertFalse(w.editor.isVisible())
        a = fitz.Point(100, 500) * w.model.doc[0].rotation_matrix
        b = fitz.Point(140, 520) * w.model.doc[0].rotation_matrix
        self.drag_pdf(tuple(a), tuple(b))
        self.assertAlmostEqual(w.area.x0, 104, delta=2)
        self.assertAlmostEqual(w.area.y0, 500, delta=2)
        self.assertTrue(w.apply_edit())
        self.assertEqual(self.errors, [])

    def test_cancel_drop_keeps_draft_and_rejects_event(self):
        self.prepare_draft()
        self.window.confirm_discard = lambda: False
        self.assertEqual(self.drop(QUrl.fromLocalFile(str(self.source))), (True, False))
        self.assertTrue(self.window.has_draft)
        self.assertEqual(self.window.editor.toPlainText(), "담당자: 이서준")

    def test_remote_and_invalid_pdf_drop_preserve_document(self):
        before = self.window.model.doc[0].get_text()
        self.assertEqual(self.drop(QUrl("https://example.invalid/document.pdf")), (False, False))
        path = self.root / "invalid.pdf"
        path.write_bytes(b"not a PDF")
        self.assertEqual(self.drop(QUrl.fromLocalFile(str(path))), (True, False))
        self.assertEqual(self.window.model.doc[0].get_text(), before)
        self.assertEqual(len(self.errors), 1)


if __name__ == "__main__":
    unittest.main()
