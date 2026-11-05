from pathlib import Path

from PySide6.QtCore import Qt, QPointF, QBuffer, QIODevice
from PySide6.QtGui import QImage, QPainter, QPen, QColor
from PySide6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QFileDialog, QMessageBox)


def png_bytes(image):
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data())


class InkPad(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(560, 240)
        self.image = QImage(1120, 480, QImage.Format.Format_ARGB32)
        self.image.fill(Qt.GlobalColor.transparent)
        self.last = None
        self.has_ink = False
        self.bounds = None
        self.setCursor(Qt.CursorShape.CrossCursor)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#ffffff"))
        p.setPen(QPen(QColor("#dbe3e8"), 1, Qt.PenStyle.DashLine))
        p.drawLine(24, int(self.height() * .72), self.width() - 24, int(self.height() * .72))
        p.drawImage(self.rect(), self.image)

    def point(self, event):
        return QPointF(event.position().x() * self.image.width() / self.width(),
                       event.position().y() * self.image.height() / self.height())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.last = self.point(event)
            self.stroke(self.last)

    def mouseMoveEvent(self, event):
        if self.last is not None:
            self.stroke(self.point(event))

    def mouseReleaseEvent(self, event):
        self.last = None

    def stroke(self, point):
        p = QPainter(self.image)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#152d44"), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawLine(self.last, point)
        p.end()
        for pt in (self.last, point):
            x, y = pt.x(), pt.y()
            if self.bounds is None:
                self.bounds = [x, y, x, y]
            else:
                self.bounds = [min(x, self.bounds[0]), min(y, self.bounds[1]),
                               max(x, self.bounds[2]), max(y, self.bounds[3])]
        self.last, self.has_ink = point, True
        self.update()

    def clear(self):
        self.image.fill(Qt.GlobalColor.transparent)
        self.has_ink, self.bounds = False, None
        self.update()

    def result(self):
        if not self.bounds:
            return None
        a, b, c, d = self.bounds
        left, top = max(0, int(a) - 12), max(0, int(b) - 12)
        return self.image.copy(left, top, min(self.image.width() - left, int(c - a) + 24),
                               min(self.image.height() - top, int(d - b) + 24))


class SignatureDialog(QDialog):
    def __init__(self, parent, saved_path: Path):
        super().__init__(parent)
        self.setWindowTitle("서명 만들기")
        self.saved_path = saved_path
        self.data = None
        self.resize(620, 390)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("나만의 서명")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        layout.addWidget(QLabel("아래에 그리거나, 가지고 있는 서명 이미지를 가져오세요."))
        self.pad = InkPad()
        layout.addWidget(self.pad)
        row = QHBoxLayout()
        clear = QPushButton("다시 그리기")
        clear.clicked.connect(self.pad.clear)
        row.addWidget(clear)
        load = QPushButton("이미지 가져오기")
        load.clicked.connect(self.load)
        row.addWidget(load)
        if saved_path.exists():
            reuse = QPushButton("저장한 서명")
            reuse.clicked.connect(self.reuse)
            row.addWidget(reuse)
        row.addStretch()
        use = QPushButton("이 서명 사용")
        use.setObjectName("primary")
        use.clicked.connect(self.use)
        row.addWidget(use)
        layout.addLayout(row)
        hint = QLabel("서명은 이 PC에만 저장됩니다. 인증서 전자서명이 아닌 이미지 서명입니다.")
        hint.setObjectName("muted")
        layout.addWidget(hint)

    def finish_image(self, image):
        if image.isNull():
            QMessageBox.warning(self, "이미지 확인", "이미지를 읽을 수 없습니다.")
            return
        if image.width() > 2400 or image.height() > 2400:
            image = image.scaled(2400, 2400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.data = png_bytes(image)
        try:
            self.saved_path.parent.mkdir(parents=True, exist_ok=True)
            self.saved_path.write_bytes(self.data)
        except OSError as exc:
            QMessageBox.warning(self, "서명 보관", "서명을 이번 문서에 사용할 수 있지만 재사용용 저장에 실패했습니다.\n" + str(exc))
        self.accept()

    def use(self):
        image = self.pad.result()
        if image is None:
            QMessageBox.information(self, "서명 그리기", "서명을 먼저 그려 주세요.")
            return
        self.finish_image(image)

    def load(self):
        path, _ = QFileDialog.getOpenFileName(self, "서명 이미지", "", "이미지 (*.png *.jpg *.jpeg)")
        if path:
            self.finish_image(QImage(path))

    def reuse(self):
        self.finish_image(QImage(str(self.saved_path)))
