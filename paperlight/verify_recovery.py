"""격리된 합성 문서로 자동 저장 후 프로세스 종료·재실행을 검증한다."""
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback


def worker(output):
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    import pymupdf as fitz
    from .window import MainWindow
    app = QApplication([])
    app.setApplicationName("PaperlightRecoveryCheck")
    window = MainWindow()
    window.data_dir = output / "test-appdata"
    assert window.open_file(output / "복구실험원본.pdf")
    window.model.add_text(0, (64, 480, 400, 550), "자동 저장된 텍스트")
    with fitz.open() as ink:
        page = ink.new_page(width=120, height=40)
        page.draw_polyline([(5, 30), (30, 5), (45, 33), (110, 10)], color=(.12, .2, .3), width=2)
        window.model.add_signature(0, (165, 660, 375, 700), page.get_pixmap(alpha=True).tobytes("png"))
    window.after_edit()
    window.set_mode("edit")
    window.select_text(next(s for s in window.model.page_spans(0) if s.text == "담당자: 김하늘"))
    window.editor.setPlainText("담당자: 복구완료")
    window.geometry_inputs["width"].setValue(200)
    ready = output / "worker-ready.json"

    def notify():
        store = window._recovery_store
        if store and store.path.exists() and not ready.exists():
            temporary = ready.with_suffix(".tmp")
            temporary.write_text(json.dumps(dict(session=store.id, interval_ms=window.recovery_timer.interval())), encoding="utf-8")
            os.replace(temporary, ready)

    timer = QTimer()
    timer.timeout.connect(notify)
    timer.start(100)
    return app.exec()


def verify(output, native=False):
    os.environ["QT_QPA_PLATFORM"] = "windows" if native else "offscreen"
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer, QEventLoop
    import pymupdf as fitz
    from .window import MainWindow
    from .recovery import RecoveryStore, RecoveryDialog
    from . import __version__
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    app.setStyle("Fusion")
    app.setApplicationName("PaperlightRecoveryCheck")
    root = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1] / "assets"
    source = output / "복구실험원본.pdf"
    shutil.copy2(root / "시작하기.pdf", source)
    original = sha256(source.read_bytes()).hexdigest()
    ready = output / "worker-ready.json"
    ready.unlink(missing_ok=True)
    command = [sys.executable]
    if not getattr(sys, "frozen", False):
        command += ["-m", "paperlight"]
    command += ["--verify-recovery-worker", str(output)]
    window = None
    child = None
    started = time.perf_counter()
    errors = []
    old_hook = sys.excepthook
    sys.excepthook = lambda *exc: errors.append("".join(traceback.format_exception(*exc)))
    try:
        with open(output / "worker.log", "w", encoding="utf-8") as log:
            child = subprocess.Popen(command, stdout=log, stderr=log,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            deadline = time.monotonic() + 25
            session = None
            while child.poll() is None and time.monotonic() < deadline:
                try:
                    session = json.loads(ready.read_text(encoding="utf-8"))
                    break
                except (FileNotFoundError, PermissionError, json.JSONDecodeError):
                    # Windows의 일시적인 파일 공유 잠금까지 해제된 뒤 읽는다.
                    pass
                time.sleep(.05)
            assert session is not None, "자동 복구본 준비 실패: worker.log 확인"
            directory = output / "test-appdata/recovery"
            assert session["session"] not in [r["id"] for r in RecoveryStore.available(directory)]
            child.kill()
            child.wait(timeout=10)
        window = MainWindow()
        window.data_dir = output / "test-appdata"
        window.error = lambda exc: errors.append(str(exc))
        window.show()
        selected = []
        chooser = QTimer()
        attempts = [0]

        def choose():
            attempts[0] += 1
            dialog = app.activeModalWidget()
            if isinstance(dialog, RecoveryDialog):
                for i in range(dialog.list.count()):
                    from PySide6.QtCore import Qt
                    if dialog.list.item(i).data(Qt.ItemDataRole.UserRole) == session["session"]:
                        dialog.list.setCurrentRow(i)
                        break
                dialog.grab().save(str(output / "recovery-prompt.png"))
                selected.append(True)
                chooser.stop()
                dialog.choose("recover")
            elif attempts[0] > 30:
                chooser.stop()
                if dialog:
                    dialog.reject()

        chooser.timeout.connect(choose)
        chooser.start(100)
        assert window.offer_recovery(startup=True)
        assert selected and not errors, errors
        assert window.has_draft and window.model.dirty
        assert window.editor.toPlainText() == "담당자: 복구완료"
        assert "담당자: 김하늘" in window.model.doc[0].get_text()
        assert "자동 저장된 텍스트" in window.model.doc[0].get_text()
        assert len(window.model.page_objects(0)) == 2
        loop = QEventLoop()
        QTimer.singleShot(300, loop.quit)
        loop.exec()
        window.refresh_text_preview()
        assert window.view.preview_rendered
        app.processEvents()
        window.grab().save(str(output / "recovered-work.png"))
        assert window.apply_edit()
        window.set_mode("object")
        item = next(o for o in window.model.page_objects(0) if o["kind"] == "text")
        assert window.select_object(item["id"])
        window.geometry_inputs["y"].setValue(510)
        target = output / "복구-최종.pdf"
        snapshot = window._recovery_store.path
        assert window.save_to(target)
        assert not snapshot.exists()
        assert window.open_file(target)
        assert len(window.model.page_objects(0)) == 2
        with fitz.open(target) as saved:
            assert "담당자: 복구완료" in saved[0].get_text()
            assert "담당자: 김하늘" not in saved[0].get_text()
        assert sha256(source.read_bytes()).hexdigest() == original
        assert not errors, errors
        report = dict(passed=True, version=__version__, frozen=bool(getattr(sys, "frozen", False)),
                      qt_platform=app.platformName(), window_visible=window.isVisible(),
                      elapsed_seconds=round(time.perf_counter()-started, 2), child_exit=child.returncode,
                      automatic_interval_ms=session["interval_ms"], terminated_only_test_child=True,
                      live_session_excluded=True, startup_dialog_restored=True, pending_input_restored=True,
                      text_and_signature_restored=True, object_reedited=True, save_reopen_passed=True,
                      snapshot_cleared_after_save=True, original_unchanged=True,
                      interaction="Qt 내부 호출, 외부 OS 입력 자동화 아님")
        (output / "recovery-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0
    except Exception:
        (output / "recovery-error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        return 1
    finally:
        if child is not None and child.poll() is None:
            child.kill()
            child.wait(timeout=10)
        if window:
            window.confirm_discard = lambda: True
            window.close()
        sys.excepthook = old_hook
