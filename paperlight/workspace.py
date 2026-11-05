"""문서별 편집 상태를 보존하는 탭 창과 트레이."""
from pathlib import Path

from PySide6.QtCore import Qt, QSettings, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QToolButton,
                              QSystemTrayIcon, QMenu, QMessageBox)
from .window import MainWindow
from .style import STYLE


class Workspace(QMainWindow):
    def __init__(self, *, data_dir=None, settings=None, tray_enabled=True):
        super().__init__()
        self.data_dir = data_dir
        self.settings = settings if settings is not None else QSettings()
        self.exiting = False
        self.conversion_dialog = None
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.active_changed)
        self.setCentralWidget(self.tabs)
        self.setWindowTitle("Paperlight")
        self.setWindowIcon(QIcon(str(Path(__file__).resolve().parents[1] / "assets/paperlight.ico")))
        self.resize(1400, 960)
        self.setMinimumSize(1050, 760)
        self.setStyleSheet(STYLE + "QTabBar::tab { padding: 10px 18px; background: #edf2f4; }"
                          "QTabBar::tab:selected { background: white; color: #146b66; }"
                          "QTabWidget::pane { border: 0; }")
        add = QToolButton()
        add.setText("+ 파일 열기")
        add.clicked.connect(lambda: self.current.open_dialog())
        self.tabs.setCornerWidget(add)
        files = self.menuBar().addMenu("파일")
        files.addAction("PDF 여러 개 열기", lambda: self.current.open_dialog())
        close = files.addAction("현재 탭 닫기", lambda: self.close_tab(self.tabs.currentIndex()))
        close.setShortcut(QKeySequence("Ctrl+W"))
        files.addAction("완전히 종료", self.quit_app)
        convert = self.menuBar().addMenu("변환")
        convert.addAction("파일 변환…", self.show_conversion)
        app_menu = self.menuBar().addMenu("앱")
        app_menu.addAction("PDF 기본 앱 설정…", self.open_default_settings)
        self.tray_preference = app_menu.addAction("창을 닫으면 트레이에 유지")
        self.tray_preference.setCheckable(True)
        self.tray_preference.setChecked(self.settings.value("closeToTray", True, type=bool))
        self.tray_preference.toggled.connect(lambda v: self.settings.setValue("closeToTray", v))
        app_menu.addAction("트레이로 숨기기", self.hide_to_tray)
        self.tray = None
        if tray_enabled and QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(self.windowIcon(), self)
            self.tray.setToolTip("Paperlight")
            menu = QMenu(self)
            menu.addAction("Paperlight 열기", self.reveal)
            menu.addAction("PDF 열기…", self.open_from_tray)
            menu.addAction("파일 변환…", self.show_conversion)
            menu.addSeparator()
            menu.addAction("완전히 종료", self.quit_app)
            self.tray.setContextMenu(menu)
            self.tray.activated.connect(self.tray_activated)
            self.tray.show()
        for keys, step in (("Ctrl+Tab", 1), ("Ctrl+Shift+Tab", -1)):
            action = QAction(self)
            action.setShortcut(QKeySequence(keys))
            action.triggered.connect(lambda checked=False, delta=step:
                                     self.tabs.setCurrentIndex((self.tabs.currentIndex() + delta) % self.tabs.count()))
            self.addAction(action)
        self.new_tab()

    @property
    def current(self):
        return self.tabs.currentWidget()

    def new_tab(self):
        editor = MainWindow()
        editor.setWindowFlags(Qt.WindowType.Widget)
        if self.data_dir is not None:
            editor.data_dir = Path(self.data_dir)
        editor.open_files_handler = self.open_files
        editor.windowTitleChanged.connect(lambda title, w=editor: self.update_tab(w))
        self.tabs.addTab(editor, "새 문서")
        self.tabs.setCurrentWidget(editor)
        return editor

    def update_tab(self, editor):
        index = self.tabs.indexOf(editor)
        if index < 0:
            return
        label = editor.model.path.name if editor.model.path else "새 문서"
        if editor.model.dirty or editor.has_draft:
            label += " *"
        self.tabs.setTabText(index, label)
        self.tabs.setTabToolTip(index, str(editor.model.path or "PDF를 열어 시작하세요"))
        if editor is self.current:
            self.setWindowTitle(editor.windowTitle())

    def active_changed(self, index):
        if self.current:
            self.update_tab(self.current)
            self.current.view.setFocus()

    def open_files(self, paths):
        for name in paths:
            path = Path(name).resolve()
            if path.suffix.lower() != ".pdf":
                continue
            existing = next((self.tabs.widget(i) for i in range(self.tabs.count())
                             if self.tabs.widget(i).model.path and
                             self.tabs.widget(i).model.path.resolve() == path), None)
            if existing:
                self.tabs.setCurrentWidget(existing)
                continue
            editor = self.current if self.current and self.current.model.doc is None else self.new_tab()
            if editor.open_file(path):
                self.update_tab(editor)
            elif self.tabs.count() > 1:
                self.close_tab(self.tabs.indexOf(editor))
        self.reveal()

    def close_tab(self, index):
        editor = self.tabs.widget(index)
        if editor is None or not editor.close():
            return False
        self.tabs.removeTab(index)
        if editor.model.doc:
            editor.model.doc.close()
        editor.deleteLater()
        if not self.tabs.count() and not self.exiting:
            self.new_tab()
        return True

    def reveal(self):
        self.showNormal() if self.isMinimized() else self.show()
        self.raise_()
        self.activateWindow()

    def open_from_tray(self):
        self.reveal()
        self.current.open_dialog()

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.reveal()

    def hide_to_tray(self):
        if not self.tray or not self.tray.isVisible():
            QMessageBox.information(self, "트레이를 사용할 수 없습니다", "현재 Windows 환경에서는 알림 영역을 사용할 수 없습니다.")
            return False
        for i in range(self.tabs.count()):
            self.tabs.widget(i).checkpoint_recovery()
        self.hide()
        if not self.settings.value("trayHintShown", False, type=bool):
            self.tray.showMessage("Paperlight", "트레이에서 다시 열 수 있습니다. 종료하려면 ‘완전히 종료’를 선택하세요.")
            self.settings.setValue("trayHintShown", True)
        return True

    def quit_app(self):
        self.exiting = True
        if not self.close():
            self.exiting = False

    def closeEvent(self, event):
        if not self.exiting and self.tray_preference.isChecked() and self.tray and self.tray.isVisible():
            self.hide_to_tray()
            event.ignore()
            return
        if self.conversion_dialog and self.conversion_dialog.running:
            self.reveal()
            QMessageBox.information(self, "변환 중", "파일 변환이 끝나거나 취소된 뒤 종료해 주세요.")
            self.exiting = False
            event.ignore()
            return
        # 뒤쪽 탭에서 취소해도 앞쪽 탭의 복구본/미저장 내용을 버리지 않는다.
        for i in range(self.tabs.count()):
            editor = self.tabs.widget(i)
            self.tabs.setCurrentIndex(i)
            if not editor.confirm_discard():
                self.exiting = False
                self.reveal()
                event.ignore()
                return
        self.exiting = True
        while self.tabs.count():
            self.current._close_confirmed = True
            self.close_tab(self.tabs.currentIndex())
        if self.tray:
            self.tray.hide()
        if self.conversion_dialog:
            self.conversion_dialog.hide()
        event.accept()

    def open_default_settings(self):
        from .windows_integration import register_pdf_app
        try:
            register_pdf_app()
            if not QDesktopServices.openUrl(QUrl("ms-settings:defaultapps?registeredAppUser=Paperlight")):
                raise RuntimeError("Windows 설정을 열지 못했습니다. 설정 → 앱 → 기본 앱에서 Paperlight를 선택하세요.")
        except Exception as exc:
            QMessageBox.warning(self, "기본 앱 설정", str(exc))

    def show_conversion(self):
        from .conversion_dialog import ConversionDialog
        self.reveal()
        if self.conversion_dialog is None:
            self.conversion_dialog = ConversionDialog(self)
            self.conversion_dialog.pdf_ready.connect(lambda p: self.open_files([p]))
        self.conversion_dialog.show()
        self.conversion_dialog.raise_()
        self.conversion_dialog.activateWindow()
