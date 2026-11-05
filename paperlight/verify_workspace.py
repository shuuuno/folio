"""사용자 문서·설정과 분리한 탭/변환/트레이 실행 파일 점검."""
from .theme import create_application
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback


def verify(output, native=False):
    os.environ["QT_QPA_PLATFORM"] = "windows" if native else "offscreen"
    from PySide6.QtCore import QSettings, QTimer
    from PySide6.QtWidgets import QSystemTrayIcon
    from .workspace import Workspace
    from . import __version__
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    app = create_application([])
    app.setStyle("Fusion")
    app.setApplicationName("PaperlightWorkspaceCheck")
    def settle():
        until = time.monotonic() + .3
        while time.monotonic() < until:
            app.processEvents()
            time.sleep(.01)
    root = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1] / "assets"
    first, second = output / "첫 번째.pdf", output / "두 번째.pdf"
    shutil.copy2(root / "시작하기.pdf", first)
    shutil.copy2(first, second)
    settings = QSettings(str(output / "settings.ini"), QSettings.Format.IniFormat)
    window = Workspace(data_dir=output / "data", settings=settings, tray_enabled=native)
    result = dict(passed=False, version=__version__, frozen=bool(getattr(sys, "frozen", False)), native=native)
    errors = []
    old_hook = sys.excepthook
    sys.excepthook = lambda *exc: errors.append("".join(traceback.format_exception(*exc)))
    try:
        window.show()
        window.open_files([first, second])
        assert window.tabs.count() == 2
        first_tab = window.tabs.widget(0)
        first_tab.model.add_text(0, (60, 480, 380, 550), "탭 독립 편집")
        first_tab.after_edit()
        assert "탭 독립 편집" not in window.current.model.doc[0].get_text()
        window.open_files([first])
        assert window.tabs.count() == 2 and window.current is first_tab
        window.show_conversion()
        dialog = window.conversion_dialog
        dialog.sources.addItem(str(first))
        dialog.destination.setText(str(output))
        dialog.format.setCurrentIndex(dialog.format.findData("pptx"))
        dialog.dpi.setCurrentIndex(0)
        dialog.start()
        deadline = time.monotonic() + 90
        while dialog.running and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.02)
        assert not dialog.running and dialog.outputs, dialog.status.text()
        from pptx import Presentation
        assert len(Presentation(dialog.outputs[0]).slides) == 2
        result["conversion_worker_completed"] = True
        from .instance import InstanceServer
        instance = InstanceServer(output / "ipc")
        assert instance.lock.tryLock(0)
        received = []
        instance.requested.connect(received.append)
        # 주 실행 파일이 아직 파이프를 만들기 전의 동시 실행을 재현한다.
        QTimer.singleShot(1500, lambda: instance.server.listen(instance.name))
        command = [sys.executable] + ([] if getattr(sys, "frozen", False) else ["-m", "paperlight"])
        command += ["--verify-ipc-client", str(output / "ipc"), str(first)]
        child = subprocess.Popen(command, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            deadline = time.monotonic() + 25
            while child.poll() is None and time.monotonic() < deadline:
                app.processEvents()
                time.sleep(.02)
            assert child.poll() == 0 and received == [[str(first)]], "시작 중 파일 전달 실패"
            result["second_process_waited_for_startup_and_forwarded"] = True
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=10)
            instance.close()
        settle()
        dialog.grab().save(str(output / "conversion.png"))
        dialog.hide()
        settle()
        window.grab().save(str(output / "tabs.png"))
        first_tab.set_mode("edit")
        settle()
        assert first_tab.view.horizontalScrollBar().maximum() == 0, "편집 모드 너비 맞춤 넘침"
        window.grab().save(str(output / "edit.png"))
        window.resize(1050, 760)
        settle()
        assert first_tab.view.horizontalScrollBar().maximum() == 0, "너비 맞춤 가로 넘침"
        assert first_tab.inspector.geometry().right() < first_tab.width(), "편집 패널 잘림"
        assert first_tab.apply_button.isVisible(), "적용 버튼 누락"
        assert window.size().height() == 760, "최소 창 높이 초과"
        assert first_tab.statusBar().mapTo(window, first_tab.statusBar().rect().bottomRight()).y() < 760, "하단 탐색줄 잘림"
        window.grab().save(str(output / "compact-edit.png"))
        first_tab.select_text(next(s for s in first_tab.model.page_spans(0) if s.text == "담당자: 김하늘"))
        settle()
        window.grab().save(str(output / "compact-selected.png"))
        from unittest.mock import patch
        with patch.object(first_tab, "choose_signature"):
            first_tab.set_mode("sign")
        settle()
        window.grab().save(str(output / "compact-sign.png"))
        first_tab.set_mode("view")
        window.resize(1400, 960)
        window.new_tab()
        app.processEvents()
        window.grab().save(str(output / "empty.png"))
        window.tabs.setCurrentWidget(first_tab)
        app.processEvents()
        result["compact_edit_layout_and_fit"] = True
        result["tabs_independent_and_deduplicated"] = True
        if native:
            import ctypes
            result["native_window_visible"] = bool(ctypes.windll.user32.IsWindowVisible(int(window.winId())))
            result["tray_available"] = QSystemTrayIcon.isSystemTrayAvailable()
            assert result["native_window_visible"]
            from ctypes import wintypes
            rect = wintypes.RECT()
            get_rect = ctypes.windll.user32.GetWindowRect
            get_rect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
            assert get_rect(int(window.winId()), ctypes.byref(rect))
            send = ctypes.windll.user32.SendMessageW
            send.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
            send.restype = wintypes.LPARAM
            for x, y, expected in ((rect.left + 2, rect.top + 2, 13),
                                   (rect.right - 2, rect.top + 2, 14),
                                   (rect.left + 2, rect.bottom - 2, 16),
                                   (rect.right - 2, rect.bottom - 2, 17)):
                assert send(int(window.winId()), 0x84, 0, (y & 0xffff) << 16 | (x & 0xffff)) == expected
            window.window_bar.maximize_button.click()
            settle()
            assert window.isMaximized()
            assert window.screen().availableGeometry().contains(window.geometry()), "최대화 창이 작업 영역을 벗어남"
            window.grab().save(str(output / "maximized.png"))
            window.window_bar.maximize_button.click()
            settle()
            assert not window.isMaximized()
            window.window_bar.minimize_button.click()
            settle()
            assert window.isMinimized()
            window.reveal()
            settle()
            assert window.isVisible() and not window.isMinimized()
            result["integrated_chrome_resize_maximize_minimize_restore"] = True
            if result["tray_available"]:
                assert window.hide_to_tray() and not window.isVisible()
                assert first_tab._recovery_store.path.exists()
                window.reveal()
                app.processEvents()
                assert window.isVisible()
                result["real_tray_hide_restore"] = True
        assert not errors, errors
        result["passed"] = True
        return 0
    except Exception:
        result["error"] = traceback.format_exc()
        return 1
    finally:
        # 검증 프로세스가 정상 종료되도록 자체 변환 완료를 기다린 뒤 닫는다.
        if window.conversion_dialog and window.conversion_dialog.running:
            window.conversion_dialog.cancel()
            while window.conversion_dialog.running:
                app.processEvents()
                time.sleep(.02)
        for i in range(window.tabs.count()):
            window.tabs.widget(i).confirm_discard = lambda: True
        window.quit_app()
        sys.excepthook = old_hook
        (output / "workspace-check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
