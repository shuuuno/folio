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
from PySide6.QtCore import QSettings, QTimer
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
        values = registration_values(self.root / "한글 폴더" / "Paperlight.exe")
        command = next(value for path, name, value in values if path.endswith("open\\command"))
        self.assertEqual(command, f'"{self.root / "한글 폴더" / "Paperlight.exe"}" "%1"')
        self.assertFalse(any("UserChoice" in path for path, _, _ in values))


if __name__ == "__main__":
    unittest.main()
