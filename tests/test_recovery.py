import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import pymupdf as fitz
from PySide6.QtWidgets import QApplication, QFileDialog
from PySide6.QtGui import QCloseEvent
from paperlight.window import MainWindow
from paperlight.recovery import RecoveryStore, RecoveryDialog
from paperlight.fonts import default_font_id
from fixtures import make_pdf

APP = QApplication.instance() or QApplication([])
APP.setStyle("Fusion")


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "한글 원본.pdf"
        make_pdf(self.source, subset=True)
        self.original = self.source.read_bytes()
        self.windows = []

    def window(self, opened=True):
        window = MainWindow()
        window.data_dir = self.root / "appdata"
        window.error = lambda exc: self.fail(str(exc))
        window.show()
        self.windows.append(window)
        if opened:
            self.assertTrue(window.open_file(self.source))
        APP.processEvents()
        return window

    def tearDown(self):
        for window in self.windows:
            window.confirm_discard = lambda: True
            window.close()
            if window.model.doc and not window.model.doc.is_closed:
                window.model.doc.close()
        APP.processEvents()
        self.temp.cleanup()

    def pending_text(self, window):
        window.set_mode("edit")
        window.select_text(next(s for s in window.model.page_spans(0) if s.text == "담당자: 김하늘"))
        window.editor.setPlainText("담당자: 이서준")
        window.geometry_inputs["width"].setValue(200)

    def abandon(self, window):
        self.assertTrue(window.checkpoint_recovery())
        store = window._recovery_store
        window.recovery_timer.stop()
        store.release()
        window._recovery_store = None
        return store.id

    def test_pending_input_recovered_without_source_and_normal_save_clears(self):
        first = self.window()
        self.pending_text(first)
        session = self.abandon(first)
        self.source.unlink()
        restored = self.window(opened=False)
        self.assertTrue(restored.restore_recovery(session))
        self.assertEqual(restored.editor.toPlainText(), "담당자: 이서준")
        self.assertTrue(restored.has_draft)
        self.assertTrue(restored.model.dirty)
        self.assertIn("담당자: 김하늘", restored.model.doc[0].get_text())
        target = self.root / "복구 결과.pdf"
        with patch.object(QFileDialog, "getSaveFileName", return_value=(str(target), "PDF")):
            self.assertTrue(restored.save_as())
        with fitz.open(target) as doc:
            self.assertIn("담당자: 이서준", doc[0].get_text())
        self.assertFalse(restored._recovery_store.path.exists())
        self.assertFalse(self.source.exists())

    def test_font_choice_in_pending_draft_is_recovered(self):
        first = self.window()
        self.pending_text(first)
        key = default_font_id(True)
        first.font_combo.setCurrentIndex(first.font_combo.findData(key))
        session = self.abandon(first)
        restored = self.window(opened=False)
        self.assertTrue(restored.restore_recovery(session))
        self.assertEqual(restored.selected_font_id, key)
        self.assertTrue(restored.has_draft)
        self.assertTrue(restored.apply_edit())
        self.assertTrue(any("Bold" in f[3] for f in restored.model.doc[0].get_fonts()))

    def test_object_draft_and_signature_draft_restore(self):
        for mode in ("object", "sign", "text"):
            first = self.window()
            oid = first.model.add_text(0, (64, 480, 400, 550), "추가 항목")
            first.after_edit()
            if mode == "object":
                first.set_mode(mode)
                first.select_object(oid)
                first.geometry_inputs["y"].setValue(510)
                first.editor.setPlainText("복구한 추가 항목")
            elif mode == "sign":
                image = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 80, 30), False)
                image.clear_with(70)
                first.signature_data = image.tobytes("png")
                first.set_mode(mode)
                first.select_area(fitz.Rect(160, 660, 360, 700))
            else:
                first.set_mode(mode)
                first.editor.setPlainText("아직 영역을 지정하지 않은 입력")
            session = self.abandon(first)
            restored = self.window(opened=False)
            self.assertTrue(restored.restore_recovery(session))
            self.assertEqual(restored.mode, mode)
            self.assertTrue(restored.has_draft)
            if mode == "text":
                self.assertIsNone(restored.area)
                self.assertEqual(restored.editor.toPlainText(), "아직 영역을 지정하지 않은 입력")
            else:
                self.assertTrue(restored.apply_edit())
                if mode == "object":
                    self.assertEqual(restored.model.page_objects(0)[0]["rect"][1], 510)
                else:
                    self.assertEqual(len(restored.model.page_objects(0)), 2)
            self.assertEqual(self.source.read_bytes(), self.original)

    def test_write_failure_keeps_previous_snapshot_and_dirty_state(self):
        window = self.window()
        self.pending_text(window)
        self.assertTrue(window.checkpoint_recovery())
        old = window._recovery_store.path.read_bytes()
        window.editor.setPlainText("다른 미적용 입력")
        with patch("paperlight.recovery.os.replace", side_effect=PermissionError("disk unavailable")):
            self.assertFalse(window.checkpoint_recovery())
        self.assertEqual(window._recovery_store.path.read_bytes(), old)
        self.assertTrue(window.has_draft)
        self.assertIn("실패", window.recovery_status.text())
        self.assertEqual(list(window._recovery_store.directory.glob("*.tmp")), [])
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_failed_open_and_cancel_close_keep_recovery(self):
        window = self.window()
        self.pending_text(window)
        self.assertTrue(window.checkpoint_recovery())
        store = window._recovery_store
        window.confirm_discard = lambda: True
        errors = []
        window.error = lambda exc: errors.append(str(exc))
        self.assertFalse(window.open_file(self.root / "missing.pdf"))
        self.assertTrue(store.path.exists())
        window.confirm_discard = lambda: False
        event = QCloseEvent()
        window.closeEvent(event)
        self.assertFalse(event.isAccepted())
        self.assertTrue(store.path.exists())
        self.assertTrue(window.recovery_timer.isActive())
        window.confirm_discard = lambda: True
        window.closeEvent(event)
        self.assertTrue(event.isAccepted())
        self.assertFalse(store.path.exists())

    def test_live_instances_are_excluded_and_later_preserves(self):
        first, second = self.window(), self.window()
        self.pending_text(first)
        self.pending_text(second)
        first.checkpoint_recovery()
        second.checkpoint_recovery()
        self.assertNotEqual(first._recovery_store.id, second._recovery_store.id)
        self.assertEqual(RecoveryStore.available(first.data_dir / "recovery"), [])
        session = self.abandon(first)
        records = RecoveryStore.available(first.data_dir / "recovery")
        self.assertEqual([r["id"] for r in records], [session])
        with patch.object(RecoveryDialog, "exec", return_value=0):
            self.assertFalse(second.offer_recovery())
        self.assertTrue((first.data_dir / "recovery" / (session + ".plr")).exists())
        errors = []
        second.error = lambda exc: errors.append(str(exc))
        self.assertFalse(second.restore_recovery(second._recovery_store.id))
        self.assertEqual(len(errors), 1)

    def test_cancel_and_failed_save_keep_checkpoint(self):
        window = self.window()
        self.pending_text(window)
        window.checkpoint_recovery()
        path = window._recovery_store.path
        old = path.read_bytes()
        with patch.object(QFileDialog, "getSaveFileName", return_value=("", "")):
            self.assertFalse(window.save_as())
        self.assertEqual(path.read_bytes(), old)
        errors = []
        window.error = lambda exc: errors.append(str(exc))
        target = self.root / "실패.pdf"
        with patch.object(QFileDialog, "getSaveFileName", return_value=(str(target), "PDF")):
            with patch.object(window.model, "save", side_effect=OSError("full")):
                self.assertFalse(window.save_as())
        self.assertTrue(path.exists())
        self.assertTrue(window.model.dirty)
        self.assertIn("담당자: 이서준", window.model.doc[0].get_text())
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_successful_document_switch_discards_only_own_checkpoint(self):
        first, second = self.window(), self.window()
        for window in (first, second):
            self.pending_text(window)
            window.checkpoint_recovery()
        own = first._recovery_store.path
        other = second._recovery_store.path
        first.confirm_discard = lambda: True
        self.assertTrue(first.open_file(self.source))
        self.assertFalse(own.exists())
        self.assertTrue(other.exists())

    def test_cancel_recovery_keeps_both_current_work_and_snapshot(self):
        first = self.window()
        self.pending_text(first)
        session = self.abandon(first)
        second = self.window()
        second.model.add_text(0, (64, 480, 400, 550), "현재 창의 내용")
        second.after_edit()
        second.checkpoint_recovery()
        own = second._recovery_store.path
        second.confirm_discard = lambda: False
        self.assertFalse(second.restore_recovery(session))
        self.assertTrue(own.exists())
        self.assertTrue((second.data_dir / "recovery" / (session + ".plr")).exists())
        self.assertIn("현재 창의 내용", second.model.doc[0].get_text())

    def test_discard_recovery_dialog_removes_only_selected_snapshot(self):
        first = self.window()
        self.pending_text(first)
        session = self.abandon(first)
        second = self.window()
        self.pending_text(second)
        second.checkpoint_recovery()
        own = second._recovery_store.path

        def discard(dialog):
            dialog.choose("discard")
            return 1

        with patch.object(RecoveryDialog, "exec", discard):
            self.assertFalse(second.offer_recovery())
        self.assertTrue(own.exists())
        self.assertFalse((second.data_dir / "recovery" / (session + ".plr")).exists())

    def test_corrupt_snapshot_keeps_current_document_and_file(self):
        first = self.window()
        self.pending_text(first)
        session = self.abandon(first)
        path = first.data_dir / "recovery" / (session + ".plr")
        path.write_bytes(b"broken recovery")
        second = self.window()
        before = second.model.doc[0].get_text()
        errors = []
        second.error = lambda exc: errors.append(str(exc))
        self.assertFalse(second.restore_recovery(session))
        self.assertEqual(second.model.doc[0].get_text(), before)
        self.assertTrue(path.exists())
        self.assertEqual(len(errors), 1)

    def test_clean_and_encrypted_documents_do_not_create_plaintext_snapshot(self):
        window = self.window()
        self.assertFalse(window.checkpoint_recovery())
        encrypted = self.root / "encrypted.pdf"
        window.model.doc.save(encrypted, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="reader")
        window.model.open(encrypted, "reader")
        window.model.revision = 1
        self.assertFalse(window.checkpoint_recovery())
        self.assertEqual(list((window.data_dir / "recovery").glob("*.plr")), [])

    def test_real_process_termination_after_automatic_checkpoint(self):
        script = self.root / "crash_worker.py"
        script.write_text('''import os, sys, json
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
import pymupdf as fitz
from paperlight.window import MainWindow
app = QApplication([])
app.setStyle("Fusion")
w = MainWindow()
w.data_dir = Path(sys.argv[2])
w.open_file(sys.argv[1])
w.model.add_text(0, (64, 480, 400, 550), "자동 저장 메모")
pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 80, 30), False)
pix.clear_with(70)
w.model.add_signature(0, (160, 660, 360, 700), pix.tobytes("png"))
w.after_edit()
w.set_mode("edit")
w.select_text(next(s for s in w.model.page_spans(0) if s.text == "담당자: 김하늘"))
w.editor.setPlainText("담당자: 이서준")
w.geometry_inputs["width"].setValue(200)
def ready():
    if w._recovery_store and w._recovery_store.path.exists():
        Path(sys.argv[3]).write_text(w._recovery_store.id)
timer = QTimer()
timer.timeout.connect(ready)
timer.start(100)
app.exec()
''', encoding="utf-8")
        ready = self.root / "ready.txt"
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
        with open(self.root / "child.log", "w", encoding="utf-8") as log:
            child = subprocess.Popen([sys.executable, str(script), str(self.source), str(self.root / "appdata"), str(ready)],
                                     env=env, stdout=log, stderr=log,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            try:
                deadline = time.monotonic() + 20
                while not ready.exists() and child.poll() is None and time.monotonic() < deadline:
                    time.sleep(.05)
                self.assertTrue(ready.exists(), (self.root / "child.log").read_text(encoding="utf-8"))
                child.kill()
                child.wait(timeout=10)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=10)
        restored = self.window(opened=False)
        session = ready.read_text()
        self.assertIn(session, [r["id"] for r in RecoveryStore.available(restored.data_dir / "recovery")])
        self.assertTrue(restored.restore_recovery(session))
        self.assertEqual(restored.editor.toPlainText(), "담당자: 이서준")
        self.assertIn("자동 저장 메모", restored.model.doc[0].get_text())
        self.assertEqual(len(restored.model.page_objects(0)), 2)
        self.assertTrue(restored.apply_edit())
        text_id = next(o["id"] for o in restored.model.page_objects(0) if o["kind"] == "text")
        restored.model.update_object(0, text_id, (80, 500, 410, 570))
        target = self.root / "강제 종료 복구.pdf"
        with patch.object(QFileDialog, "getSaveFileName", return_value=(str(target), "PDF")):
            self.assertTrue(restored.save_as())
        with fitz.open(target) as doc:
            self.assertIn("담당자: 이서준", doc[0].get_text())
        self.assertEqual(self.source.read_bytes(), self.original)
        evidence = Path(__file__).resolve().parents[1] / "evidence"
        evidence.mkdir(exist_ok=True)
        (evidence / "recovery-process-check.json").write_text(json.dumps(dict(passed=True,
            automatic_interval_ms=5000, child_exit=child.returncode, killed_after_checkpoint=True,
            pending_input_restored=True, text_and_signature_restored=True, objects_reedited=True,
            saved_and_reopened=True, source_unchanged=True), indent=2), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
