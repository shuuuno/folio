"""문서 탭과 창 조작부를 함께 배치하는 Windows 상단 바."""
import sys

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QWidget, QHBoxLayout, QToolButton, QTabBar, QStackedWidget, QSizePolicy, QMenu, QLabel
from .icons import icon


class DocumentTabs(QStackedWidget):
    """탭 표시 위치와 문서 스택을 분리하되 순서·선택은 함께 유지한다."""
    def __init__(self):
        super().__init__()
        self.bar = QTabBar()
        self.bar.setObjectName("documentTabs")
        self.bar.setDrawBase(False)
        self.bar.setExpanding(False)
        self.bar.setMovable(True)
        self.bar.setTabsClosable(True)
        self.bar.setUsesScrollButtons(True)
        self.bar.setElideMode(Qt.TextElideMode.ElideMiddle)
        self.bar.setFixedHeight(40)
        self.bar.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.bar.currentChanged.connect(self.setCurrentIndex)
        self.currentChanged.connect(self.bar.setCurrentIndex)
        self.bar.tabMoved.connect(self.move_document)

    def tabBar(self):
        return self.bar

    def addTab(self, widget, text):
        self.blockSignals(True)
        index = self.addWidget(widget)
        self.blockSignals(False)
        self.bar.addTab(text)
        self.currentChanged.emit(self.currentIndex())
        return index

    def removeTab(self, index):
        self.blockSignals(True)
        self.bar.blockSignals(True)
        self.removeWidget(self.widget(index))
        self.bar.removeTab(index)
        self.setCurrentIndex(self.bar.currentIndex())
        self.bar.blockSignals(False)
        self.blockSignals(False)
        self.currentChanged.emit(self.currentIndex())

    def setTabText(self, index, text):
        self.bar.setTabText(index, text)

    def setTabToolTip(self, index, text):
        self.bar.setTabToolTip(index, text)

    def move_document(self, source, target):
        active = self.currentWidget()
        document = self.widget(source)
        self.blockSignals(True)
        self.removeWidget(document)
        self.insertWidget(target, document)
        self.setCurrentWidget(active)
        self.blockSignals(False)
        self.currentChanged.emit(self.currentIndex())


class WindowBar(QWidget):
    def __init__(self, owner, tabs, open_callback):
        super().__init__(owner)
        self.owner = owner
        self.setObjectName("windowBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setFixedHeight(40)
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 0, 0, 0)
        row.setSpacing(0)
        self.wordmark = QLabel("Folio")
        self.wordmark.setObjectName("wordmark")
        self.wordmark.setAccessibleName("Folio")
        self.wordmark.setFixedWidth(70)
        self.wordmark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.wordmark.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row.addWidget(self.wordmark)
        row.addWidget(tabs.bar)
        self.add_button = QToolButton()
        self.add_button.setObjectName("iconButton")
        self.add_button.setIcon(icon("plus"))
        self.add_button.setFixedSize(34, 32)
        self.add_button.setToolTip("PDF 파일 열기 · Ctrl+O")
        self.add_button.setAccessibleName("PDF 파일 열기")
        self.add_button.clicked.connect(open_callback)
        row.addWidget(self.add_button)
        row.addSpacing(80)  # 탭이 많아도 창을 잡을 자리를 남긴다.
        row.addStretch()
        self.minimize_button = self.control("minus", "최소화", owner.showMinimized)
        self.maximize_button = self.control("maximize", "최대화", self.toggle_maximized)
        self.close_button = self.control("close", "창 닫기", owner.close)
        self.close_button.setObjectName("windowClose")
        for button in (self.minimize_button, self.maximize_button, self.close_button):
            row.addWidget(button)

    def control(self, symbol, label, callback):
        button = QToolButton()
        button.setObjectName("windowControl")
        button.setFixedSize(46, 40)
        button.setIcon(icon(symbol))
        button.setIconSize(QSize(16, 16))
        button.setToolTip(label)
        button.setAccessibleName(label)
        button.clicked.connect(callback)
        return button

    def toggle_maximized(self):
        self.owner.showNormal() if self.owner.isMaximized() else self.owner.showMaximized()

    def sync_state(self):
        maximized = self.owner.isMaximized()
        self.maximize_button.setIcon(icon("restore" if maximized else "maximize"))
        label = "이전 크기로 복원" if maximized else "최대화"
        self.maximize_button.setToolTip(label)
        self.maximize_button.setAccessibleName(label)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.owner.windowHandle():
            self.owner.windowHandle().startSystemMove()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximized()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        self.show_system_menu(event.globalPos())

    def show_system_menu(self, position=None):
        menu = QMenu(self)
        restore = menu.addAction("이전 크기로 복원", self.owner.showNormal)
        restore.setEnabled(self.owner.isMaximized())
        menu.addAction("최소화", self.owner.showMinimized)
        maximize = menu.addAction("최대화", self.owner.showMaximized)
        maximize.setEnabled(not self.owner.isMaximized())
        menu.addSeparator()
        menu.addAction("창 닫기", self.owner.close)
        menu.exec(position or self.mapToGlobal(self.rect().bottomLeft()))


def resize_hit(window, message):
    """Windows에 가장자리 크기 조절을 맡긴다. 좌표는 화면 물리 픽셀."""
    if sys.platform != "win32" or window.isMaximized() or window.isFullScreen():
        return None
    import ctypes
    from ctypes import wintypes
    msg = wintypes.MSG.from_address(int(message))
    if msg.message != 0x0084:  # WM_NCHITTEST
        return None
    bounds = wintypes.RECT()
    get_rect = ctypes.windll.user32.GetWindowRect
    get_rect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    if not get_rect(msg.hWnd, ctypes.byref(bounds)):
        return None
    x, y = ctypes.c_short(msg.lParam & 0xffff).value, ctypes.c_short((msg.lParam >> 16) & 0xffff).value
    margin = round(6 * window.devicePixelRatioF())
    left, right = bounds.left <= x < bounds.left + margin, bounds.right - margin <= x < bounds.right
    top, bottom = bounds.top <= y < bounds.top + margin, bounds.bottom - margin <= y < bounds.bottom
    if top: return 13 if left else 14 if right else 12
    if bottom: return 16 if left else 17 if right else 15
    if left: return 10
    if right: return 11
    return None
