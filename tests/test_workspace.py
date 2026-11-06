import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QSettings, QTimer, Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QTabBar
from paperlight.workspace import Workspace
from paperlight.instance import InstanceServer
from paperlight.windows_integration import registration_values
from fixtures import make_pdf

APP = QApplication.instance() or QApplication([])


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.a, self.b = self.root / "첫 문서.pdf", self.root / "둘째 문서.pdf"
        make_pdf(self.a, subset=True)
        make_pdf(self.b, subset=True)
        settings = QSettings(str(self.root / "settings.ini"), QSettings.Format.IniFormat)
        self.window = Workspace(data_dir=self.root / "data", settings=settings, tray_enabled=False)
        self.window.show()

    def tearDown(self):
        for i in range(self.window.tabs.count()):
            self.window.tabs.widget(i).confirm_discard = lambda: True
        self.window.quit_app()
        APP.processEvents()
        self.temp.cleanup()

    def test_tabs_keep_edits_draft_undo_and_duplicate_path(self):
        self.window.open_files([self.a, self.b])
        self.assertEqual(self.window.tabs.count(), 2)
        first, second = self.window.tabs.widget(0), self.window.tabs.widget(1)
        first.model.add_text(0, (50, 480, 400, 550), "첫 탭만 편집")
        first.after_edit()
        first.set_mode("edit")
        first.select_text(next(s for s in first.model.page_spans(0) if s.text == "담당자: 김하늘"))
        first.editor.setPlainText("미적용 입력 보존")
        self.window.tabs.setCurrentIndex(1)
        self.assertNotIn("첫 탭만 편집", second.model.doc[0].get_text())
        self.assertFalse(second.model.can_undo)
        self.window.open_files([self.a])
        self.assertEqual(self.window.tabs.count(), 2)
        self.assertIs(self.window.current, first)
        self.assertTrue(first.has_draft)
        self.assertEqual(first.editor.toPlainText(), "미적용 입력 보존")
        self.assertTrue(first.model.can_undo)

    def test_close_cancel_keeps_tab_and_recovery(self):
        self.window.open_files([self.a, self.b])
        paths = []
        for i in range(2):
            editor = self.window.tabs.widget(i)
            editor.model.add_text(0, (50, 480, 400, 550), f"작업 {i}")
            editor.checkpoint_recovery()
            paths.append(editor._recovery_store.path)
        with patch.object(self.window.tabs.widget(0), "confirm_discard", return_value=True), \
             patch.object(self.window.tabs.widget(1), "confirm_discard", return_value=False):
            self.window.quit_app()
        self.assertEqual(self.window.tabs.count(), 2)
        self.assertTrue(all(p.exists() for p in paths))
        with patch.object(self.window.current, "confirm_discard", return_value=False):
            self.assertFalse(self.window.close_tab(1))
        self.assertEqual(self.window.tabs.count(), 2)

    def test_header_save_follows_active_document_and_tab_close_after_reorder(self):
        self.assertFalse(self.window.save_button.isEnabled())
        self.window.open_files([self.a, self.b])
        first = self.window.tabs.widget(0)
        self.assertTrue(self.window.save_button.isEnabled())
        with patch.object(self.window.current, "save_as") as save:
            self.window.save_button.click()
            save.assert_called_once()
        self.assertTrue(first.header.isHidden())
        self.window.tabs.tabBar().moveTab(0, 1)
        close = self.window.tabs.tabBar().tabButton(1, QTabBar.ButtonPosition.RightSide)
        close.click()
        self.assertEqual(self.window.tabs.count(), 1)
        self.assertEqual(self.window.current.model.path, self.b)
        self.window.new_tab()
        self.assertFalse(self.window.save_button.isEnabled())

    def test_compact_edit_fit_and_sidebar_toggle(self):
        self.window.open_files([self.a])
        editor = self.window.current
        self.window.resize(1050, 760)
        editor.mode_buttons["edit"].click()
        APP.processEvents()
        editor.fit_width()
        self.assertTrue(editor.inspector.isVisible())
        self.assertTrue(editor.apply_button.isVisible())
        self.assertEqual(editor.view.horizontalScrollBar().maximum(), 0)
        self.assertEqual(self.window.height(), 760)
        status = editor.statusBar()
        self.assertLess(status.mapTo(self.window, status.rect().bottomRight()).y(), 760)
        editor.sidebar_button.click()
        self.assertTrue(editor.sidebar.isHidden())
        editor.sidebar_button.click()
        self.assertFalse(editor.sidebar.isHidden())

    def test_titlebar_controls_and_active_tab_reorder(self):
        self.window.open_files([self.a, self.b])
        self.window.tabs.setCurrentIndex(0)
        active = self.window.current
        self.window.tabs.tabBar().moveTab(0, 1)
        self.assertIs(self.window.current, active)
        self.assertEqual(self.window.tabs.currentIndex(), 1)
        self.assertEqual(self.window.tabs.tabBar().currentIndex(), 1)
        self.window.window_bar.maximize_button.click()
        self.assertTrue(self.window.isMaximized())
        self.assertEqual(self.window.window_bar.maximize_button.accessibleName(), "이전 크기로 복원")
        self.window.window_bar.maximize_button.click()
        self.assertFalse(self.window.isMaximized())
        QTest.mouseDClick(self.window.window_bar, Qt.MouseButton.LeftButton, pos=QPoint(700, 22))
        self.assertTrue(self.window.isMaximized())
        self.window.showNormal()
        with patch.object(self.window.windowHandle(), "startSystemMove", return_value=True) as move:
            QTest.mouseClick(self.window.window_bar, Qt.MouseButton.LeftButton, pos=QPoint(700, 22))
            move.assert_called_once()
        with patch.object(active, "confirm_discard", return_value=False):
            self.window.window_bar.close_button.click()
            self.assertTrue(self.window.isVisible())
            self.assertEqual(self.window.tabs.count(), 2)

    def test_laptop_inspector_actions_stay_visible_while_fields_scroll(self):
        self.window.open_files([self.a])
        self.window.resize(960, 640)
        editor = self.window.current
        editor.set_mode("edit")
        editor.select_text(next(s for s in editor.model.page_spans(0) if s.text == "담당자: 김하늘"))
        editor.editor.setPlainText("담당자: 이서준")
        QTest.qWait(200)
        self.assertEqual(self.window.size().width(), 960)
        self.assertEqual(self.window.size().height(), 640)
        self.assertGreater(editor.inspector_scroll.verticalScrollBar().maximum(), 0)
        self.assertEqual(editor.inspector_scroll.horizontalScrollBar().maximum(), 0)
        original = editor.apply_button.mapTo(editor.inspector, QPoint(0, 0))
        for value in (editor.inspector_scroll.verticalScrollBar().maximum(), 0):
            editor.inspector_scroll.verticalScrollBar().setValue(value)
            APP.processEvents()
            self.assertEqual(editor.apply_button.mapTo(editor.inspector, QPoint(0, 0)), original)
            for button in (editor.apply_button, editor.cancel_button):
                self.assertTrue(editor.inspector.rect().contains(button.mapTo(editor.inspector, button.rect().topLeft())))
                self.assertTrue(editor.inspector.rect().contains(button.mapTo(editor.inspector, button.rect().bottomRight())))
        self.assertEqual(editor.editor.toPlainText(), "담당자: 이서준")
        editor.apply_button.click()
        self.assertIn("담당자: 이서준", editor.model.doc[0].get_text())

    def test_overflow_tabs_leave_window_controls_accessible(self):
        self.window.resize(1050, 760)
        for index in range(14):
            self.window.new_tab()
            self.window.tabs.setTabText(index, f"긴 문서 이름과 여러 항목 {index}.pdf")
        APP.processEvents()
        bar = self.window.window_bar
        self.assertLessEqual(bar.close_button.geometry().right(), self.window.width())
        self.assertLess(bar.add_button.geometry().right(), bar.minimize_button.geometry().left())
        self.window.tabs.tabBar().moveTab(0, 14)
        self.assertIs(self.window.current, self.window.tabs.widget(self.window.tabs.tabBar().currentIndex()))

    def test_tray_hide_preserves_and_reveal_restores(self):
        class Tray:
            visible = True
            def isVisible(self): return self.visible
            def showMessage(self, *args): pass
            def hide(self): self.visible = False
        self.window.tray = Tray()
        self.window.open_files([self.a])
        self.window.current.model.add_text(0, (50, 480, 400, 550), "트레이 작업")
        self.assertFalse(self.window.close())
        self.assertFalse(self.window.isVisible())
        self.assertTrue(self.window.current._recovery_store.path.exists())
        self.window.reveal()
        self.assertTrue(self.window.isVisible())
        self.assertIn("트레이 작업", self.window.current.model.doc[0].get_text())

    def test_instance_forwards_real_second_process(self):
        self.check_forwarding(False)

    def test_instance_waits_for_primary_startup(self):
        self.check_forwarding(True)

    def check_forwarding(self, delayed):
        server = InstanceServer(self.root / "ipc")
        if delayed:
            self.assertTrue(server.lock.tryLock(0))
            QTimer.singleShot(1500, lambda: server.server.listen(server.name))
        else:
            self.assertTrue(server.start_or_forward([]))
        received = []
        server.requested.connect(received.append)
        code = "from PySide6.QtCore import QCoreApplication; from paperlight.instance import InstanceServer; import sys; app=QCoreApplication([]); s=InstanceServer(sys.argv[1]); assert not s.start_or_forward([sys.argv[2]])"
        child = subprocess.Popen([sys.executable, "-c", code, str(self.root / "ipc"), str(self.a)],
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline = time.monotonic() + 15
            while child.poll() is None and time.monotonic() < deadline:
                APP.processEvents()
                time.sleep(.01)
            self.assertEqual(child.wait(timeout=2), 0)
            self.assertEqual(received, [[str(self.a.resolve())]])
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
            server.close()

    def test_registration_quotes_unicode_path_without_userchoice(self):
        values = registration_values(self.root / "한글 폴더" / "Folio.exe")
        command = next(value for path, name, value in values if path.endswith("open\\command"))
        self.assertEqual(command, f'"{self.root / "한글 폴더" / "Folio.exe"}" "%1"')
        self.assertFalse(any("UserChoice" in path for path, _, _ in values))
        self.assertIn((r"Software\Classes\.pdf\OpenWithProgids", "Paperlight.PDF", ""), values)
        self.assertIn((r"Software\Paperlight\Capabilities", "ApplicationName", "Folio"), values)
        self.assertIn((r"Software\RegisteredApplications", "Folio", r"Software\Paperlight\Capabilities"), values)

    def test_document_controls_follow_empty_tab_and_page_limits(self):
        empty = self.window.current
        self.assertTrue(all(not w.isEnabled() for w in empty.document_controls))
        self.assertFalse(self.window.save_action.isEnabled())
        self.window.open_files([self.a])
        editor = self.window.current
        self.assertTrue(editor.search_box.isEnabled())
        self.assertFalse(editor.previous_page.isEnabled())
        self.assertTrue(editor.next_page.isEnabled())
        editor.next_page.click()
        self.assertEqual(editor.page_number, 1)
        self.assertTrue(editor.previous_page.isEnabled())
        self.assertFalse(editor.next_page.isEnabled())
        self.window.new_tab()
        self.assertFalse(self.window.current.page_input.isEnabled())
        self.assertFalse(self.window.save_action.isEnabled())

    def test_conversion_options_follow_format_sources_and_current_tab(self):
        from paperlight.conversion_dialog import ConversionDialog
        dialog = ConversionDialog(self.window)
        self.assertFalse(dialog.current_button.isEnabled())
        self.assertFalse(dialog.start_button.isEnabled())
        self.assertFalse(dialog.mode.isEnabled())
        dialog.sources.addItem(str(self.a))
        dialog.destination.setText(str(self.root))
        self.assertTrue(dialog.start_button.isEnabled())
        dialog.format.setCurrentIndex(dialog.format.findData("pdf"))
        self.assertFalse(dialog.dpi.isEnabled())
        self.assertFalse(dialog.mode.isEnabled())
        dialog.format.setCurrentIndex(dialog.format.findData("docx"))
        self.assertTrue(dialog.mode.isEnabled())
        self.assertIn("표", dialog.format_hint.text())
        dialog.mode.setCurrentIndex(1)
        self.assertIn("편집할 수 없습니다", dialog.format_hint.text())
        dialog.sources.clear()
        self.assertFalse(dialog.start_button.isEnabled())
        self.window.open_files([self.a])
        dialog.show()
        APP.processEvents()
        self.assertTrue(dialog.current_button.isEnabled())
        dialog.close()

    def test_signature_action_follows_ink_and_clear(self):
        from paperlight.signature import SignatureDialog
        from PySide6.QtCore import QPointF
        path = self.root / "data" / "signature.png"
        dialog = SignatureDialog(self.window, path)
        self.assertFalse(dialog.use_button.isEnabled())
        dialog.pad.last = QPointF(10, 10)
        dialog.pad.stroke(QPointF(30, 30))
        self.assertTrue(dialog.use_button.isEnabled())
        dialog.pad.clear()
        self.assertFalse(dialog.use_button.isEnabled())
        dialog.pad.last = QPointF(10, 10)
        dialog.pad.stroke(QPointF(50, 30))
        dialog.use_button.click()
        self.assertTrue(path.read_bytes().startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
