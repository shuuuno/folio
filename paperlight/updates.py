"""설치판의 공개 GitHub 피드만 사용한다. 문서·설정은 전송하지 않는다."""
import sys
import threading

import velopack

REPOSITORY = "https://github.com/shuuuno/folio"


def bootstrap():
    # Qt·단일 인스턴스 검사보다 먼저 설치/제거 훅을 처리해야 한다.
    from .windows_integration import register_pdf_app, unregister_pdf_app
    (velopack.App().set_auto_apply_on_startup(False)
     .on_after_install_fast_callback(lambda version: register_pdf_app())
     .on_after_update_fast_callback(lambda version: register_pdf_app())
     .on_before_uninstall_fast_callback(lambda version: unregister_pdf_app())
     .run())


def installed_manager():
    if not getattr(sys, "frozen", False):
        return None
    try:
        manager = velopack.UpdateManager(velopack.GithubSource(REPOSITORY))
        return None if manager.get_is_portable() else manager
    except Exception:
        # 개발 실행·기존 NSIS·일반 ZIP은 Velopack 설치 정보가 없다.
        return None


def download_update(manager):
    pending = manager.get_update_pending_restart()
    if pending:
        return pending
    update = manager.check_for_updates()
    if update:
        # 다운로드 크기와 해시 검증은 Velopack이 수행한다.
        manager.download_updates(update)
        return update.TargetFullRelease
    return None


def attach_updates(window):
    # 개발·포터블에서는 네트워크 요청도 업데이트 메뉴도 만들지 않는다.
    manager = installed_manager()
    if manager is None:
        return None
    from PySide6.QtCore import QObject, Signal, Slot, QTimer
    from PySide6.QtWidgets import QMessageBox

    class Updates(QObject):
        finished = Signal(object, str)

        def __init__(self):
            super().__init__(window)
            self.asset = None
            self.running = False
            self.action = window.app_menu.addAction("업데이트 확인")
            window.app_menu.insertAction(window.tray_preference, self.action)
            self.action.triggered.connect(self.activate)
            self.finished.connect(self.complete)
            QTimer.singleShot(1500, self.check)

        def check(self):
            if self.running or self.asset:
                return
            self.running = True
            self.action.setEnabled(False)
            self.action.setText("업데이트 확인·다운로드 중…")

            def work():
                try:
                    asset, error = download_update(manager), ""
                except Exception:
                    asset, error = None, "업데이트 서버에 연결하거나 파일을 검증하지 못했습니다. 나중에 다시 확인하세요."
                try:
                    self.finished.emit(asset, error)
                except RuntimeError:
                    pass  # 창이 종료된 뒤 도착한 결과

            threading.Thread(target=work, name="folio-update", daemon=True).start()

        @Slot(object, str)
        def complete(self, asset, error):
            self.running = False
            self.asset = asset
            self.action.setEnabled(True)
            self.action.setText(f"업데이트 {asset.Version} 설치 및 재시작…" if asset else
                                ("업데이트 확인 재시도" if error else "최신 버전 · 다시 확인"))
            self.action.setToolTip(error)
            if asset and not window.isHidden():
                self.activate()

        def activate(self):
            if not self.asset:
                self.check()
                return
            answer = QMessageBox.question(window, "Folio 업데이트",
                f"새 버전 {self.asset.Version}을 다운로드했습니다. 지금 재시작해 적용할까요?\n"
                "미저장 작업은 종료 전에 확인합니다. ‘아니요’를 선택하면 나중에 메뉴에서 적용할 수 있습니다.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer == QMessageBox.StandardButton.Yes:
                window.restart_for_update(lambda: manager.wait_exit_then_apply_updates(
                    self.asset, silent=True, restart=True, restart_args=[]))

    return Updates()
