import functools
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import velopack
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox
from paperlight.updates import attach_updates, bootstrap, download_update, installed_manager, REPOSITORY
from paperlight.workspace import Workspace

APP = QApplication.instance() or QApplication([])


def manifest(version):
    return (f'<package><metadata><id>Folio</id><version>{version}</version>'
            '<title>Folio</title><authors>Folio</authors><description>검증</description>'
            '<mainExe>Folio.exe</mainExe><channel>win</channel><runtime>win-x64</runtime>'
            '</metadata></package>')


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class LocalFeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.feed = self.root / "feed"
        self.feed.mkdir()
        current = self.root / "current"
        current.mkdir()
        (current / "sq.version").write_text(manifest("0.11.0"), encoding="utf-8")
        (self.root / "packages").mkdir()
        (self.root / "Update.exe").write_bytes(b"not-executed-by-feed-tests")
        locator = velopack.VelopackLocatorConfig(self.root, self.root / "Update.exe",
            self.root / "packages", current / "sq.version", current, False)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(self.feed)))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        source = velopack.HttpSource(f"http://127.0.0.1:{self.server.server_port}/",
                                     velopack.HttpOptions([], 2000))
        self.manager = velopack.UpdateManager(source, locator=locator)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def write_feed(self, version="0.12.0", *, corrupt=False):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            archive.writestr("Folio.nuspec", manifest(version))
            archive.writestr("lib/app/Folio.exe", b"local-feed-fixture")
        package = data.getvalue()
        name = f"Folio-{version}-full.nupkg"
        (self.feed / name).write_bytes(package + (b"tampered" if corrupt else b""))
        asset = dict(PackageId="Folio", Version=version, Type="Full", FileName=name,
                     SHA1=hashlib.sha1(package).hexdigest(), SHA256=hashlib.sha256(package).hexdigest(),
                     Size=len(package), NotesMarkdown="", NotesHtml="")
        (self.feed / "releases.win.json").write_text(json.dumps(dict(Assets=[asset])), encoding="utf-8")
        return name

    def test_real_sdk_download_and_cached_pending_update(self):
        name = self.write_feed()
        asset = download_update(self.manager)
        self.assertEqual(asset.Version, "0.12.0")
        self.assertEqual((self.root / "packages" / name).read_bytes(), (self.feed / name).read_bytes())
        # 이미 검증한 다운로드는 네트워크 없이 재시작 대기 상태로 재사용한다.
        (self.feed / "releases.win.json").unlink()
        self.assertEqual(download_update(self.manager).Version, "0.12.0")

    def test_same_older_and_empty_feed_do_not_update(self):
        for version in ("0.11.0", "0.10.0"):
            self.write_feed(version)
            self.assertIsNone(download_update(self.manager))
        (self.feed / "releases.win.json").write_text('{"Assets": []}', encoding="utf-8")
        self.assertIsNone(download_update(self.manager))

    def test_corrupt_package_is_rejected_and_not_pending(self):
        self.write_feed(corrupt=True)
        with self.assertRaises(Exception):
            download_update(self.manager)
        self.assertIsNone(self.manager.get_update_pending_restart())

    def test_missing_feed_is_reported_without_app_state_changes(self):
        with self.assertRaises(Exception):
            download_update(self.manager)
        self.assertEqual(self.manager.get_current_version(), "0.11.0")


class UpdateUiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.window = Workspace(data_dir=root / "data", tray_enabled=False,
            settings=QSettings(str(root / "settings.ini"), QSettings.Format.IniFormat))

    def tearDown(self):
        for i in range(self.window.tabs.count()):
            self.window.tabs.widget(i).confirm_discard = lambda: True
        self.window.quit_app()
        self.window.deleteLater()
        APP.processEvents()
        self.temp.cleanup()

    def test_development_and_portable_never_check_network(self):
        with patch("paperlight.updates.velopack.UpdateManager") as create:
            self.assertIsNone(installed_manager())
            create.assert_not_called()
        with patch("paperlight.updates.sys.frozen", True, create=True), \
             patch("paperlight.updates.velopack.UpdateManager") as create:
            create.return_value.get_is_portable.return_value = True
            self.assertIsNone(installed_manager())
            create.return_value.check_for_updates.assert_not_called()

    def test_installed_uses_public_stable_github_source_without_token(self):
        with patch("paperlight.updates.sys.frozen", True, create=True), \
             patch("paperlight.updates.velopack.GithubSource") as source, \
             patch("paperlight.updates.velopack.UpdateManager") as create:
            create.return_value.get_is_portable.return_value = False
            self.assertIs(installed_manager(), create.return_value)
            source.assert_called_once_with(REPOSITORY)
            create.assert_called_once_with(source.return_value)

    def test_bootstrap_disables_unconfirmed_startup_apply(self):
        with patch("paperlight.updates.velopack.App") as create:
            app = create.return_value
            app.set_auto_apply_on_startup.return_value = app
            app.on_after_install_fast_callback.return_value = app
            app.on_after_update_fast_callback.return_value = app
            app.on_before_uninstall_fast_callback.return_value = app
            bootstrap()
            app.set_auto_apply_on_startup.assert_called_once_with(False)
            app.run.assert_called_once()

    def test_offline_failure_allows_retry_and_editing(self):
        manager = Mock()
        manager.get_update_pending_restart.return_value = None
        manager.check_for_updates.side_effect = OSError("offline")
        with patch("paperlight.updates.installed_manager", return_value=manager):
            updater = attach_updates(self.window)
        updater.check()
        deadline = time.monotonic() + 3
        while updater.running and time.monotonic() < deadline:
            APP.processEvents()
            time.sleep(.01)
        self.assertFalse(updater.running)
        self.assertTrue(updater.action.isEnabled())
        self.assertEqual(updater.action.text(), "업데이트 확인 재시도")
        self.assertEqual(self.window.tabs.count(), 1)

    def test_background_download_keeps_ui_responsive(self):
        release = threading.Event()
        manager = Mock()
        manager.get_update_pending_restart.return_value = None
        manager.check_for_updates.side_effect = lambda: release.wait(3) and None
        with patch("paperlight.updates.installed_manager", return_value=manager):
            updater = attach_updates(self.window)
        updater.check()
        self.window.new_tab()
        APP.processEvents()
        self.assertEqual(self.window.tabs.count(), 2)
        self.assertTrue(updater.running)
        release.set()
        deadline = time.monotonic() + 3
        while updater.running and time.monotonic() < deadline:
            APP.processEvents()
            time.sleep(.01)
        self.assertFalse(updater.running)

    def test_all_tabs_confirm_before_apply_and_cancel_preserves_tabs(self):
        self.window.new_tab()
        callback = Mock()
        with patch.object(self.window.tabs.widget(0), "confirm_discard", return_value=True), \
             patch.object(self.window.tabs.widget(1), "confirm_discard", return_value=False):
            self.window.restart_for_update(callback)
        callback.assert_not_called()
        self.assertEqual(self.window.tabs.count(), 2)
        self.assertFalse(self.window.exiting)
        self.assertIsNone(self.window._update_callback)

    def test_apply_failure_preserves_tabs(self):
        with patch.object(self.window.current, "confirm_discard", return_value=True), \
             patch.object(QMessageBox, "warning"):
            self.window.restart_for_update(Mock(side_effect=OSError("helper unavailable")))
        self.assertEqual(self.window.tabs.count(), 1)
        self.assertFalse(self.window.exiting)

    def test_active_conversion_prevents_update(self):
        self.window.conversion_dialog = Mock(running=True)
        callback = Mock()
        with patch.object(QMessageBox, "information"):
            self.window.restart_for_update(callback)
        callback.assert_not_called()
        self.assertEqual(self.window.tabs.count(), 1)
        self.window.conversion_dialog.running = False

    def test_success_schedules_graceful_update_before_tabs_close(self):
        counts = []
        with patch.object(self.window.current, "confirm_discard", return_value=True):
            self.window.restart_for_update(lambda: counts.append(self.window.tabs.count()))
        self.assertEqual(counts, [1])
        self.assertEqual(self.window.tabs.count(), 0)

    def test_decline_does_not_apply_and_restart_uses_no_document_paths(self):
        manager = Mock()
        asset = Mock(Version="0.12.0")
        with patch("paperlight.updates.installed_manager", return_value=manager):
            updater = attach_updates(self.window)
        updater.complete(asset, "")
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            updater.activate()
        manager.wait_exit_then_apply_updates.assert_not_called()
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes), \
             patch.object(self.window.current, "confirm_discard", return_value=True):
            updater.activate()
        manager.wait_exit_then_apply_updates.assert_called_once_with(asset, silent=True, restart=True, restart_args=[])


if __name__ == "__main__":
    unittest.main()
