from __future__ import annotations

from pathlib import Path
import math
import os
import base64
import json
from dataclasses import asdict

import pymupdf as fitz
from PySide6.QtCore import Qt, QRectF, QSize, Signal, QTimer, QStandardPaths
from PySide6.QtGui import (QPixmap, QImage, QColor, QPen, QBrush, QPainter, QKeySequence,
                          QAction, QIcon, QFontDatabase)
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem,
    QStackedWidget, QListWidget, QListWidgetItem, QAbstractItemView, QSplitter,
    QFormLayout, QDoubleSpinBox, QSpinBox, QTextEdit, QLineEdit, QFileDialog,
    QMessageBox, QInputDialog, QColorDialog, QButtonGroup, QDialog, QApplication, QMenu)

from .document import PdfDocument, EditError, rgb
from .signature import SignatureDialog
from .style import STYLE
from .selection import TextSelection
from .recovery import RecoveryStore, RecoveryDialog


def pixmap_from_fitz(pix):
    return QPixmap.fromImage(QImage(pix.samples, pix.width, pix.height, pix.stride,
                                   QImage.Format.Format_RGB888).copy())


class PageView(QGraphicsView):
    text_selected = Signal(object)
    area_selected = Signal(object)
    page_step = Signal(int)

    def __init__(self, parent):
        super().__init__(parent)
        self.owner = parent
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMouseTracking(True)
        self.mode = "view"
        self.start = None
        self.preview = None
        self.preview_image = None
        self.page_item = None
        self.preview_rendered = False
        self.page_bounds = fitz.Rect()
        self.read_selection = None
        self.read_anchor = None
        self.read_marks = []
        self.read_key = None
        self.object_drag = None
        self.set_mode("view")

    def set_mode(self, mode):
        self.mode = mode
        self.start = None
        self.object_drag = None
        self.clear_read_selection()
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag if mode == "view" else QGraphicsView.DragMode.NoDrag)
        self.viewport().setCursor(Qt.CursorShape.OpenHandCursor if mode == "view" else Qt.CursorShape.CrossCursor)

    def to_pdf(self, point):
        pos = self.mapToScene(point)
        return fitz.Point(pos.x(), pos.y()) * self.owner.model.doc[self.owner.page_number].derotation_matrix

    def show_page(self, keep_position=False):
        self.preview = self.preview_image = None
        self.page_item = None
        self.preview_rendered = False
        self.read_marks = []
        self.scene().clear()
        model = self.owner.model
        if not model.doc:
            return
        page = model.doc[self.owner.page_number]
        key = (model.doc, self.owner.page_number)
        if key != self.read_key:
            self.read_selection = None
            self.read_anchor = None
            self.read_key = key
        self.page_bounds = page.rect
        render_scale = self.render_scale()
        pix = page.get_pixmap(matrix=fitz.Matrix(render_scale, render_scale), alpha=False)
        item = self.scene().addPixmap(pixmap_from_fitz(pix))
        self.page_item = item
        item.setScale(1 / render_scale)
        item.setZValue(0)
        w, h = page.rect.width, page.rect.height
        self.setSceneRect(-26, -26, w + 52, h + 52)
        self.resetTransform()
        self.scale(self.owner.zoom, self.owner.zoom)
        if self.mode == "edit":
            pen = QPen(QColor("#70b4a5"), .7, Qt.PenStyle.DashLine)
            pen.setCosmetic(True)
            for span in model.page_spans(self.owner.page_number):
                box = fitz.Rect(span.bbox) * page.rotation_matrix
                mark = self.scene().addRect(QRectF(box.x0, box.y0, box.width, box.height), pen)
                mark.setZValue(2)
        if self.mode == "object":
            for obj in model.page_objects(self.owner.page_number):
                box = fitz.Rect(obj["rect"]) * page.rotation_matrix
                pen = QPen(QColor("#70b4a5"), .8, Qt.PenStyle.DashLine)
                pen.setCosmetic(True)
                mark = self.scene().addRect(QRectF(box.x0, box.y0, box.width, box.height), pen)
                mark.setZValue(2)
        if not keep_position:
            self.centerOn(w / 2, min(h / 2, self.viewport().height() / self.owner.zoom / 2))
        self.paint_read_selection()
        hit = getattr(self.owner, "search_hit", None)
        if hit is not None and hit[0] == self.owner.page_number:
            self.show_selection(hit[1])

    def selection_model(self):
        if self.read_selection is None:
            self.read_selection = TextSelection(self.owner.model.doc[self.owner.page_number])
        return self.read_selection

    def clear_read_selection(self):
        self.read_anchor = None
        if self.read_selection is not None:
            self.read_selection.select(0, 0)
        for mark in self.read_marks:
            self.scene().removeItem(mark)
        self.read_marks = []

    def paint_read_selection(self):
        for mark in self.read_marks:
            self.scene().removeItem(mark)
        self.read_marks = []
        if self.read_selection is None or not self.owner.model.doc:
            return
        page = self.owner.model.doc[self.owner.page_number]
        for rect in self.read_selection.rectangles():
            box = rect * page.rotation_matrix
            mark = self.scene().addRect(QRectF(box.x0, box.y0, box.width, box.height),
                                       QPen(Qt.PenStyle.NoPen), QBrush(QColor(35, 123, 112, 65)))
            mark.setZValue(3)
            self.read_marks.append(mark)

    def copy_selected_text(self):
        if self.read_selection is None or not self.read_selection.text:
            return False
        if not self.owner.model.doc.permissions & fitz.PDF_PERM_COPY:
            self.owner.statusBar().showMessage("이 PDF에는 복사 제한이 있습니다.", 5000)
            return False
        QApplication.clipboard().setText(self.read_selection.text)
        self.owner.statusBar().showMessage("선택한 텍스트를 복사했습니다.", 3000)
        return True

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete and self.mode == "object":
            self.owner.delete_selected_object()
            event.accept()
        elif event.matches(QKeySequence.StandardKey.Copy) and self.mode == "view":
            self.copy_selected_text()
            event.accept()
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        if self.mode != "view" or self.read_selection is None or not self.read_selection.text:
            return super().contextMenuEvent(event)
        menu = QMenu(self)
        copy = menu.addAction("텍스트 복사  Ctrl+C")
        copy.setEnabled(bool(self.owner.model.doc.permissions & fitz.PDF_PERM_COPY))
        if menu.exec(event.globalPos()) == copy:
            self.copy_selected_text()

    def render_scale(self):
        page = self.owner.model.doc[self.owner.page_number]
        return min(self.owner.zoom * self.devicePixelRatioF(), 3.0,
                   math.sqrt(16_000_000 / max(page.rect.get_area(), 1)))

    def restore_page_image(self):
        if self.preview_rendered and self.page_item is not None:
            page = self.owner.model.doc[self.owner.page_number]
            scale = self.render_scale()
            self.page_item.setPixmap(pixmap_from_fitz(page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)))
            self.preview_rendered = False

    def show_selection(self, rect, signature=None):
        if self.preview is not None:
            self.scene().removeItem(self.preview)
        if self.preview_image is not None:
            self.scene().removeItem(self.preview_image)
            self.preview_image = None
        if not self.owner.model.doc:
            return
        page = self.owner.model.doc[self.owner.page_number]
        box = fitz.Rect(rect) * page.rotation_matrix
        pen = QPen(QColor("#218878"), 1.5)
        pen.setCosmetic(True)
        self.preview = self.scene().addRect(QRectF(box.x0, box.y0, box.width, box.height), pen,
                                            QBrush(QColor(33, 136, 120, 22)))
        self.preview.setZValue(4)
        if self.mode == "object" and self.owner.selected_object:
            corner = fitz.Point(rect.x1, rect.y1) * page.rotation_matrix
            radius = 4 / self.owner.zoom
            handle = QGraphicsRectItem(corner.x-radius, corner.y-radius, radius*2, radius*2, self.preview)
            handle.setBrush(QBrush(QColor("#218878")))
            handle.setPen(pen)
        if signature:
            image = QImage.fromData(signature)
            # 문서 회전이 있는 경우 프리뷰도 PDF 저장 결과와 같은 방향으로 회전한다.
            pix = QPixmap.fromImage(image)
            self.preview_image = self.scene().addPixmap(pix)
            scale = min(rect.width / pix.width(), rect.height / pix.height())
            self.preview_image.setScale(scale)
            x = rect.x0 + (rect.width - pix.width() * scale) / 2
            y = rect.y0 + (rect.height - pix.height() * scale) / 2
            point = fitz.Point(x, y) * page.rotation_matrix
            self.preview_image.setPos(point.x, point.y)
            self.preview_image.setRotation(page.rotation)
            self.preview_image.setOpacity(.85)
            self.preview_image.setZValue(3)

    def mousePressEvent(self, event):
        if not self.owner.model.doc or event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        point = self.to_pdf(event.position().toPoint())
        if self.mode == "view":
            self.owner.search_hit = None
            if self.preview is not None:
                self.scene().removeItem(self.preview)
                self.preview = None
            self.clear_read_selection()
            selection = self.selection_model()
            boundary = selection.boundary(point, require_hit=True)
            if boundary is None:
                return super().mousePressEvent(event)
            self.setFocus()
            self.read_anchor = boundary
            selection.select(boundary, boundary)
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.viewport().setCursor(Qt.CursorShape.IBeamCursor)
            return
        page = self.owner.model.doc[self.owner.page_number]
        if not fitz.Rect(0, 0, page.cropbox.width, page.cropbox.height).contains(point):
            return
        if self.mode == "object":
            self.setFocus()
            owner = self.owner
            resizing = (owner.selected_object is not None and owner.area is not None
                        and abs(point.x-owner.area.x1) <= 8/owner.zoom and abs(point.y-owner.area.y1) <= 8/owner.zoom)
            if not resizing and not (owner.selected_object and owner.area and owner.area.contains(point)):
                candidates = [o for o in owner.model.page_objects(owner.page_number) if fitz.Rect(o["rect"]).contains(point)]
                if not candidates or not owner.select_object(candidates[-1]["id"]):
                    return
            if owner.area is not None:
                self.object_drag = (point, fitz.Rect(owner.area), resizing)
            return
        if self.mode == "edit":
            candidates = [s for s in self.owner.model.page_spans(self.owner.page_number) if fitz.Rect(s.bbox).contains(point)]
            if candidates:
                self.text_selected.emit(min(candidates, key=lambda s: fitz.Rect(s.bbox).get_area()))
            else:
                self.owner.statusBar().showMessage("수정할 글자를 클릭하세요. 스캔본에는 ‘텍스트 추가’를 이용하세요.", 5000)
        else:
            self.start = point

    def mouseMoveEvent(self, event):
        if self.object_drag is not None:
            point = self.to_pdf(event.position().toPoint())
            start, original, resizing = self.object_drag
            page = self.owner.model.doc[self.owner.page_number]
            dx, dy = point.x-start.x, point.y-start.y
            if resizing:
                rect = fitz.Rect(original.x0, original.y0,
                                 min(page.cropbox.width, max(original.x0+8, original.x1+dx)),
                                 min(page.cropbox.height, max(original.y0+8, original.y1+dy)))
            else:
                dx = max(-original.x0, min(page.cropbox.width-original.x1, dx))
                dy = max(-original.y0, min(page.cropbox.height-original.y1, dy))
                rect = original + (dx, dy, dx, dy)
            self.owner.set_area(rect)
        elif self.read_anchor is not None:
            boundary = self.selection_model().boundary(self.to_pdf(event.position().toPoint()))
            if boundary is not None:
                self.read_selection.select(self.read_anchor, boundary)
                self.paint_read_selection()
        elif self.start is not None:
            point = self.to_pdf(event.position().toPoint())
            rect = fitz.Rect(self.start, point).normalize()
            page = self.owner.model.doc[self.owner.page_number]
            rect &= fitz.Rect(0, 0, page.cropbox.width, page.cropbox.height)
            self.show_selection(rect)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.object_drag is not None:
            self.mouseMoveEvent(event)
            self.object_drag = None
            return
        if self.read_anchor is not None:
            self.mouseMoveEvent(event)
            self.read_anchor = None
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            if self.read_selection.text:
                self.owner.statusBar().showMessage(f"{len(self.read_selection.text)}자 선택 · Ctrl+C로 복사", 6000)
            return
        if self.start is not None:
            point = self.to_pdf(event.position().toPoint())
            rect = fitz.Rect(self.start, point).normalize()
            if rect.width < 8 or rect.height < 8:
                rect = fitz.Rect(self.start.x, self.start.y, self.start.x + 210, self.start.y + 65)
            page = self.owner.model.doc[self.owner.page_number]
            rect &= fitz.Rect(0, 0, page.cropbox.width, page.cropbox.height)
            self.start = None
            if rect.width > 5 and rect.height > 5:
                self.area_selected.emit(rect)
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.owner.change_zoom(1.15 if event.angleDelta().y() > 0 else 1 / 1.15)
            event.accept()
            return
        bar = self.verticalScrollBar()
        delta = event.angleDelta().y()
        if (delta < 0 and bar.value() == bar.maximum()) or (delta > 0 and bar.value() == bar.minimum()):
            self.page_step.emit(1 if delta < 0 else -1)
            event.accept()
        else:
            super().wheelEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self.owner, "fit_mode", False) and hasattr(self.owner, "fit_timer"):
            self.owner.fit_timer.start(100)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # offscreen QA와 Windows 플러그인 모두 동일한 실제 한글 글꼴을 쓴다.
        if not getattr(MainWindow, "_fonts_loaded", False):
            for name in ("malgun.ttf", "malgunbd.ttf"):
                QFontDatabase.addApplicationFont(str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / name))
            MainWindow._fonts_loaded = True
        self.model = PdfDocument()
        self.page_number = 0
        self.zoom = 1.0
        self.fit_mode = True
        self.fit_timer = QTimer(self)
        self.fit_timer.setSingleShot(True)
        self.fit_timer.timeout.connect(self.fit_width)
        self.mode = "view"
        self.selected = None
        self.selected_object = None
        self.area = None
        self.signature_data = None
        self._draft_baseline = None
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.refresh_text_preview)
        self.ink = QColor("#203545")
        self._refreshing = False
        self._rendered_thumbs = set()
        self._thumbnail_generation = 0
        self.search_hit = None
        self._search_key = None
        self._search_hits = []
        self._search_cursor = -1
        self._recovery_store = None
        self._recovery_key = None
        self._recovery_busy = False
        self.setWindowTitle("Paperlight")
        self.resize(1360, 900)
        self.setMinimumSize(1020, 700)
        self.setStyleSheet(STYLE)
        self.setAcceptDrops(True)
        self.data_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
        self.build_ui()
        self.editor.textChanged.connect(self.draft_changed)
        self.size_input.valueChanged.connect(self.draft_changed)
        self.bind_shortcuts()
        self.update_state()
        self.recovery_timer = QTimer(self)
        self.recovery_timer.setInterval(5000)
        self.recovery_timer.timeout.connect(self.checkpoint_recovery)
        self.recovery_timer.start()

    def button(self, text, callback, primary=False):
        b = QPushButton(text)
        if primary:
            b.setObjectName("primary")
        b.clicked.connect(callback)
        return b

    def build_ui(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setCentralWidget(root)
        header = QWidget()
        header.setObjectName("header")
        row = QHBoxLayout(header)
        row.setContentsMargins(24, 13, 24, 13)
        brand = QLabel("Paperlight")
        brand.setObjectName("brand")
        row.addWidget(brand)
        row.addSpacing(25)
        self.filename = QLabel("나만의 PDF 작업 공간")
        row.addWidget(self.filename)
        row.addStretch()
        self.save_state = QLabel("내 PC에서만 처리")
        self.save_state.setObjectName("muted")
        row.addWidget(self.save_state)
        self.open_button = self.button("파일 열기", self.open_dialog)
        row.addWidget(self.open_button)
        row.addWidget(self.button("작업 복구", self.offer_recovery))
        self.save_button = self.button("다른 이름으로 저장", self.save_as, True)
        row.addWidget(self.save_button)
        layout.addWidget(header)
        tools = QWidget()
        tools.setObjectName("tools")
        row = QHBoxLayout(tools)
        row.setContentsMargins(18, 7, 18, 7)
        self.modes = QButtonGroup(self)
        self.mode_buttons = {}
        for key, text in [("view", "보기"), ("edit", "본문 수정"), ("text", "텍스트 추가"), ("sign", "서명"), ("object", "배치 편집")]:
            b = self.button(text, lambda checked=False, k=key: self.set_mode(k))
            b.setCheckable(True)
            self.modes.addButton(b)
            self.mode_buttons[key] = b
            row.addWidget(b)
        self.mode_buttons["view"].setChecked(True)
        row.addSpacing(14)
        self.undo_button = self.button("실행 취소", self.undo)
        self.undo_button.setToolTip("Ctrl+Z")
        row.addWidget(self.undo_button)
        self.redo_button = self.button("다시 실행", self.redo)
        self.redo_button.setToolTip("Ctrl+Shift+Z")
        row.addWidget(self.redo_button)
        row.addStretch()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("문서에서 찾기")
        self.search_box.setMaximumWidth(145)
        self.search_box.returnPressed.connect(self.search)
        row.addWidget(self.search_box)
        self.search_count = QLabel("")
        self.search_count.setObjectName("muted")
        self.search_count.setMinimumWidth(40)
        row.addWidget(self.search_count)
        previous = self.button("이전", lambda: self.search(-1))
        previous.setToolTip("이전 검색 결과 · Shift+F3")
        row.addWidget(previous)
        following = self.button("다음", lambda: self.search(1))
        following.setToolTip("다음 검색 결과 · F3")
        row.addWidget(following)
        self.search_box.textChanged.connect(self.invalidate_search)
        row.addWidget(self.button("-", lambda: self.change_zoom(1 / 1.2)))
        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(43)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self.zoom_label)
        row.addWidget(self.button("+", lambda: self.change_zoom(1.2)))
        row.addWidget(self.button("너비 맞춤", self.fit_width))
        layout.addWidget(tools)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)
        welcome = QWidget()
        welcome.setStyleSheet("background: #f4f7f8;")
        center = QVBoxLayout(welcome)
        center.addStretch(3)
        kicker = QLabel("P A P E R L I G H T")
        kicker.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kicker.setStyleSheet("color: #358579; font-weight: 700; font-size: 12px;")
        center.addWidget(kicker)
        title = QLabel("문서에만 집중하세요.")
        title.setObjectName("welcomeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center.addWidget(title)
        body = QLabel("읽고, 고치고, 서명하는 가장 편안한 공간.\nPDF를 여기에 끌어다 놓아도 됩니다.")
        body.setObjectName("welcomeBody")
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.setStyleSheet("line-height: 160%; padding: 15px;")
        center.addWidget(body)
        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(self.button("PDF 파일 열기", self.open_dialog, True))
        actions.addStretch()
        center.addLayout(actions)
        center.addSpacing(35)
        privacy = QLabel("로그인 없이   ·   업로드 없이   ·   원본은 그대로")
        privacy.setObjectName("muted")
        privacy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center.addWidget(privacy)
        center.addStretch(4)
        self.stack.addWidget(welcome)
        work = QSplitter(Qt.Orientation.Horizontal)
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 15, 0, 0)
        self.pages_title = QLabel("   페이지")
        side_layout.addWidget(self.pages_title)
        self.thumbnails = QListWidget()
        self.thumbnails.setIconSize(QSize(112, 146))
        self.thumbnails.setViewMode(QListWidget.ViewMode.IconMode)
        self.thumbnails.setFlow(QListWidget.Flow.TopToBottom)
        self.thumbnails.setWrapping(False)
        self.thumbnails.setMovement(QListWidget.Movement.Static)
        self.thumbnails.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.thumbnails.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.thumbnails.currentRowChanged.connect(self.go_page)
        self.thumbnails.verticalScrollBar().valueChanged.connect(self.schedule_thumbnails)
        side_layout.addWidget(self.thumbnails)
        sidebar.setMinimumWidth(155)
        sidebar.setMaximumWidth(210)
        work.addWidget(sidebar)
        self.view = PageView(self)
        self.view.text_selected.connect(self.select_text)
        self.view.area_selected.connect(self.select_area)
        self.view.page_step.connect(lambda step: self.go_page(self.page_number + step))
        work.addWidget(self.view)
        self.inspector = self.build_inspector()
        work.addWidget(self.inspector)
        work.setSizes([170, 900, 290])
        work.setCollapsible(0, False)
        work.setCollapsible(1, False)
        work.setCollapsible(2, False)
        self.stack.addWidget(work)
        self.page_input = QSpinBox()
        self.page_input.setMinimum(1)
        self.page_input.setMaximumWidth(70)
        self.page_input.valueChanged.connect(lambda value: self.go_page(value - 1))
        self.page_total = QLabel("/ 0")
        self.recovery_status = QLabel("자동 복구 켜짐")
        self.recovery_status.setObjectName("muted")
        self.statusBar().addPermanentWidget(self.recovery_status)
        self.statusBar().addPermanentWidget(self.button("이전", lambda: self.go_page(self.page_number - 1)))
        self.statusBar().addPermanentWidget(self.page_input)
        self.statusBar().addPermanentWidget(self.page_total)
        self.statusBar().addPermanentWidget(self.button("다음", lambda: self.go_page(self.page_number + 1)))
        self.statusBar().showMessage("PDF 파일을 열어 시작하세요.")
        self.inspector.hide()

    def build_inspector(self):
        panel = QWidget()
        panel.setObjectName("inspector")
        panel.setMinimumWidth(270)
        panel.setMaximumWidth(330)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 23, 20, 20)
        layout.setSpacing(13)
        self.panel_title = QLabel("본문 수정")
        self.panel_title.setObjectName("sectionTitle")
        layout.addWidget(self.panel_title)
        self.panel_hint = QLabel("문서에서 수정할 글자를 클릭하세요.")
        self.panel_hint.setWordWrap(True)
        self.panel_hint.setObjectName("muted")
        layout.addWidget(self.panel_hint)
        self.editor = QTextEdit()
        self.editor.setAcceptRichText(False)
        self.editor.setPlaceholderText("내용을 입력하세요")
        self.editor.setMinimumHeight(100)
        self.editor.setMaximumHeight(210)
        layout.addWidget(self.editor)
        self.font_label = QLabel("글꼴: 맑은 고딕")
        self.font_label.setWordWrap(True)
        self.font_label.setObjectName("muted")
        layout.addWidget(self.font_label)
        form = QFormLayout()
        form.setSpacing(12)
        self.size_input = QDoubleSpinBox()
        self.size_input.setRange(5, 160)
        self.size_input.setValue(14)
        self.size_input.setSuffix(" pt")
        form.addRow("글자 크기", self.size_input)
        self.color_button = self.button("글자 색상", self.pick_color)
        form.addRow("색상", self.color_button)
        self.geometry_inputs = {}
        for key, label in [("x", "가로 위치"), ("y", "세로 위치"), ("width", "영역 너비"), ("height", "영역 높이")]:
            spin = QDoubleSpinBox()
            spin.setRange(0 if key in ("x", "y") else 1, 10000)
            spin.setSuffix(" pt")
            spin.valueChanged.connect(self.geometry_changed)
            self.geometry_inputs[key] = spin
            form.addRow(label, spin)
        layout.addLayout(form)
        self.signature_button = self.button("서명 선택 / 새로 만들기", self.choose_signature)
        layout.addWidget(self.signature_button)
        layout.addStretch()
        self.apply_button = self.button("문서에 적용", self.apply_edit, True)
        self.preview_note = QLabel("")
        self.preview_note.setWordWrap(True)
        self.preview_note.setObjectName("muted")
        layout.addWidget(self.preview_note)
        layout.addWidget(self.apply_button)
        self.delete_object_button = self.button("선택 항목 삭제", self.delete_selected_object)
        self.delete_object_button.hide()
        layout.addWidget(self.delete_object_button)
        self.cancel_button = self.button("선택 취소", self.clear_selection)
        layout.addWidget(self.cancel_button)
        self.edit_notice = QLabel("변경 내용은 실행 취소할 수 있습니다.\n파일은 저장 버튼을 눌러야 저장됩니다.")
        self.edit_notice.setObjectName("muted")
        self.edit_notice.setWordWrap(True)
        layout.addWidget(self.edit_notice)
        return panel

    def bind_shortcuts(self):
        for keys, callback in [("Ctrl+O", self.open_dialog), ("Ctrl+Shift+S", self.save_as),
                               ("Ctrl+S", self.save_as), ("Ctrl+Z", self.undo),
                               ("Ctrl+Shift+Z", self.redo), ("Ctrl+Y", self.redo),
                               ("Ctrl+F", self.search_box.setFocus), ("F3", lambda: self.search(1)),
                               ("Shift+F3", lambda: self.search(-1)), ("Escape", self.clear_selection)]:
            action = QAction(self)
            action.setShortcut(QKeySequence(keys))
            action.triggered.connect(callback)
            self.addAction(action)

    def open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "PDF 열기", "", "PDF 문서 (*.pdf)")
        if path:
            self.open_file(path)

    def open_file(self, path):
        if not self.confirm_discard():
            return False
        try:
            self.model.open(path)
        except EditError as exc:
            if "암호" in str(exc):
                password, ok = QInputDialog.getText(self, "암호화된 PDF", "문서 암호", QLineEdit.EchoMode.Password)
                if not ok:
                    return False
                try:
                    self.model.open(path, password)
                except Exception as retry:
                    self.error(retry)
                    return False
            else:
                self.error(exc)
                return False
        except Exception as exc:
            self.error(exc)
            return False
        self.clear_recovery(release=True)
        self.show_open_document()
        return True

    def show_open_document(self):
        self.page_number = 0
        self._clear_selection()
        self.invalidate_search()
        self._rendered_thumbs.clear()
        self._thumbnail_generation += 1
        self.thumbnails.blockSignals(True)
        self.thumbnails.clear()
        for i in range(self.model.doc.page_count):
            item = QListWidgetItem(str(i + 1))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setSizeHint(QSize(132, 172))
            self.thumbnails.addItem(item)
        self.thumbnails.setCurrentRow(0)
        self.thumbnails.blockSignals(False)
        self.stack.setCurrentIndex(1)
        self.page_input.blockSignals(True)
        self.page_input.setMaximum(self.model.doc.page_count)
        self.page_input.setValue(1)
        self.page_input.blockSignals(False)
        self.pages_title.setText(f"   페이지  ·  {self.model.doc.page_count}")
        self.page_total.setText(f"/ {self.model.doc.page_count}")
        self.set_mode("view")
        self.fit_width()
        self.fit_timer.start(0)
        self.update_state()
        self.schedule_thumbnails()
        self.statusBar().showMessage("글자를 드래그하면 선택, 빈 곳을 드래그하면 이동합니다. Ctrl+C로 복사하세요.", 7000)

    def recovery_state(self):
        draft = None
        if self.has_draft:
            draft = dict(mode=self.mode, text=self.editor.toPlainText(), size=self.size_input.value(),
                         color=[self.ink.redF(), self.ink.greenF(), self.ink.blueF()],
                         area=list(self.area) if self.area is not None else None,
                         selected=asdict(self.selected) if self.selected else None,
                         object_id=self.selected_object["id"] if self.selected_object else None,
                         signature=base64.b64encode(self.signature_data).decode("ascii")
                         if self.mode == "sign" and self.signature_data else None)
        return dict(source=str(self.model.path.resolve()), page=self.page_number, dirty=self.model.dirty,
                    zoom=self.zoom, fit=self.fit_mode, draft=draft)

    def checkpoint_recovery(self):
        if self._recovery_busy:
            return False
        if not self.model.doc or not self.model.editable or not (self.model.dirty or self.has_draft):
            self.clear_recovery()
            return False
        try:
            state = self.recovery_state()
            key = (self.model.revision, json.dumps(state, sort_keys=True, allow_nan=False))
            if key == self._recovery_key:
                return True
            if self._recovery_store is None:
                self._recovery_store = RecoveryStore(self.data_dir / "recovery")
            meta = self._recovery_store.write(self.model._bytes(), state)
            self._recovery_key = key
            self.recovery_status.setText("복구본 저장 · " + meta["updated"][11:19])
            self.recovery_status.setToolTip("마지막 복구본 저장 시각입니다. 원본 PDF는 변경하지 않습니다.")
            return True
        except Exception as exc:
            self.recovery_status.setText("복구본 저장 실패 · 직접 저장해 주세요")
            self.recovery_status.setToolTip(str(exc))
            return False

    def clear_recovery(self, release=False):
        self._recovery_key = None
        store = self._recovery_store
        try:
            if store and store.lock.isLocked():
                store.clear()
            self.recovery_status.setText("자동 복구 켜짐")
            self.recovery_status.setToolTip("")
        except Exception as exc:
            self.recovery_status.setText("복구본 정리 실패")
            self.recovery_status.setToolTip(str(exc))
        finally:
            if release and store:
                store.release()
                self._recovery_store = None

    def offer_recovery(self, checked=False, startup=False):
        try:
            records = RecoveryStore.available(self.data_dir / "recovery")
            if not records:
                if not startup:
                    self.statusBar().showMessage("복구할 이전 작업이 없습니다. 다른 창의 작업은 제외합니다.", 6000)
                return False
            dialog = RecoveryDialog(self, records)
            dialog.exec()
            if dialog.action == "recover" and dialog.session_id:
                return self.restore_recovery(dialog.session_id)
            if dialog.action == "discard" and dialog.session_id:
                store = RecoveryStore(self.data_dir / "recovery", dialog.session_id)
                if not store.acquire():
                    raise EditError("다른 창에서 이 복구본을 사용 중입니다.")
                try:
                    store.clear()
                finally:
                    store.release()
            return False
        except Exception as exc:
            self.error(exc)
            return False

    def restore_recovery(self, session_id):
        store = RecoveryStore(self.data_dir / "recovery", session_id)
        candidate = PdfDocument()
        adopted = False
        try:
            if not store.acquire():
                raise EditError("다른 창에서 이 복구본을 사용 중입니다.")
            meta, pdf = store.read()
            state = meta["state"]
            candidate.open_bytes(pdf, state["source"])
            if not candidate.editable:
                raise EditError("읽기 전용 문서의 복구본은 열 수 없습니다.")
            page = state["page"]
            if not isinstance(page, int) or not 0 <= page < candidate.doc.page_count:
                raise EditError("복구할 페이지 정보가 올바르지 않습니다.")
            zoom = float(state["zoom"])
            if not math.isfinite(zoom) or not .25 <= zoom <= 3:
                raise EditError("복구 화면 배율이 올바르지 않습니다.")
            draft = state.get("draft")
            selected = None
            signature = None
            if draft:
                if draft["mode"] not in ("edit", "text", "object", "sign") or not isinstance(draft["text"], str):
                    raise EditError("복구 입력 정보가 올바르지 않습니다.")
                if not 5 <= draft["size"] <= 160 or len(draft["color"]) != 3 or not all(0 <= v <= 1 for v in draft["color"]):
                    raise EditError("복구 글자 서식이 올바르지 않습니다.")
                if draft["area"] is not None:
                    box = fitz.Rect(draft["area"])
                    if not all(math.isfinite(v) for v in box):
                        raise EditError("복구 영역이 올바르지 않습니다.")
                if draft["mode"] == "edit":
                    old = draft["selected"]
                    selected = next((s for s in candidate.page_spans(page) if s.index == old["index"]
                                     and s.text == old["text"] and all(abs(a-b) < .02 for a, b in zip(s.bbox, old["bbox"]))), None)
                    if selected is None:
                        raise EditError("입력 중이던 본문 위치를 찾지 못했습니다. 복구본은 유지합니다.")
                if draft["mode"] == "object" and not any(o["id"] == draft["object_id"] for o in candidate.page_objects(page)):
                    raise EditError("입력 중이던 추가 항목을 찾지 못했습니다. 복구본은 유지합니다.")
                if draft["mode"] == "sign":
                    signature = base64.b64decode(draft["signature"], validate=True)
                    if QImage.fromData(signature).isNull():
                        raise EditError("복구 서명 이미지를 읽지 못했습니다.")
            if not self.confirm_discard():
                return False
            self._recovery_busy = True
            self.clear_recovery(release=True)
            if self.model.doc:
                self.model.doc.close()
            self.model = candidate
            candidate.revision = candidate._serial = 1
            candidate.saved_revision = 0
            self._recovery_store = store
            adopted = True
            self.show_open_document()
            self.go_page(page)
            self.fit_mode = bool(state.get("fit", True))
            if not self.fit_mode:
                self.fit_timer.stop()
                self.zoom = zoom
                self.zoom_label.setText(f"{round(zoom * 100)}%")
                self.view.show_page()
            if draft:
                if signature:
                    self.signature_data = signature
                self.set_mode(draft["mode"])
                if selected:
                    self.select_text(selected)
                elif draft["mode"] == "object":
                    self.select_object(draft["object_id"])
                if draft["area"] is not None:
                    self.set_area(fitz.Rect(draft["area"]))
                self.editor.setPlainText(draft["text"])
                self.size_input.setValue(draft["size"])
                self.ink = QColor.fromRgbF(*draft["color"])
                self.color_button.setStyleSheet(f"color: {self.ink.name()};")
                self.draft_changed()
            self.update_state()
            self.recovery_status.setText("이전 작업 복구됨 · 저장이 필요합니다")
            self.statusBar().showMessage("이전 작업을 복구했습니다. 원본은 바뀌지 않았습니다. 확인 후 다른 이름으로 저장하세요.", 15000)
            return True
        except Exception as exc:
            self.error(exc)
            return False
        finally:
            self._recovery_busy = False
            if not adopted:
                store.release()
                if candidate.doc:
                    candidate.doc.close()

    def schedule_thumbnails(self, *_):
        if not self.model.doc:
            return
        generation = self._thumbnail_generation
        visible = [i for i in range(min(self.thumbnails.count(), self.model.doc.page_count))
                   if self.thumbnails.visualItemRect(self.thumbnails.item(i)).intersects(self.thumbnails.viewport().rect())]
        pending = [i for i in visible if i not in self._rendered_thumbs]
        if not pending:
            return
        number = pending[0]
        self._rendered_thumbs.add(number)
        def render():
            if (generation != self._thumbnail_generation or not self.model.doc or self.model.doc.is_closed
                    or number >= self.model.doc.page_count or self.thumbnails.item(number) is None):
                return
            page = self.model.doc[number]
            pix = page.get_pixmap(matrix=fitz.Matrix(110 / page.rect.width, 110 / page.rect.width), alpha=False)
            thumbnail = pixmap_from_fitz(pix)
            icon = QIcon(thumbnail)
            # Qt's generated Selected icon tints page colors with the OS accent.
            icon.addPixmap(thumbnail, QIcon.Mode.Selected)
            self.thumbnails.item(number).setIcon(icon)
            self.schedule_thumbnails()
        QTimer.singleShot(0, render)

    def go_page(self, number):
        if not self.model.doc or not 0 <= number < self.model.doc.page_count:
            return False
        if number == self.page_number:
            return True
        if not self.resolve_draft():
            self.sync_page_controls()
            return False
        self.page_number = number
        self._clear_selection()
        self.sync_page_controls()
        if self.fit_mode:
            self.fit_width()
        else:
            self.view.show_page()
        self.schedule_thumbnails()
        return True

    def sync_page_controls(self):
        self.thumbnails.blockSignals(True)
        self.thumbnails.setCurrentRow(self.page_number)
        self.thumbnails.blockSignals(False)
        self.page_input.blockSignals(True)
        self.page_input.setValue(self.page_number + 1)
        self.page_input.blockSignals(False)

    def set_mode(self, mode):
        if not self.model.doc:
            return
        if mode == self.mode:
            return
        if not self.resolve_draft():
            self.mode_buttons[self.mode].setChecked(True)
            return
        self.mode = mode
        self.mode_buttons[mode].setChecked(True)
        self.view.set_mode(mode)
        self._clear_selection()
        self.inspector.setVisible(mode != "view")
        titles = {"view": "보기", "edit": "본문 수정", "text": "텍스트 추가", "sign": "서명 넣기", "object": "배치 편집"}
        hints = {"view": "", "edit": "점선으로 표시된 글자를 클릭하세요. 내용을 모두 지우고 적용하면 본문이 삭제됩니다.",
                 "text": "문서 위에서 드래그해 텍스트 영역을 지정하세요.",
                 "sign": "서명을 고른 뒤 문서 위에서 드래그해 위치와 크기를 지정하세요.",
                 "object": "추가한 항목을 클릭하세요. 안쪽을 드래그하면 이동, 모서리 점을 드래그하면 크기가 바뀝니다."}
        self.panel_title.setText(titles[mode])
        self.panel_hint.setText(hints[mode])
        self.editor.setVisible(mode in ("edit", "text"))
        self.font_label.setVisible(mode in ("edit", "text"))
        self.size_input.setEnabled(mode in ("edit", "text"))
        self.color_button.setEnabled(mode in ("edit", "text"))
        self.signature_button.setVisible(mode == "sign")
        self.delete_object_button.setVisible(mode == "object")
        if mode == "text":
            self.size_input.setValue(14)
            self.ink = QColor("#203545")
            self.color_button.setStyleSheet(f"color: {self.ink.name()};")
            self.font_label.setText("글꼴: 맑은 고딕")
        for key, spin in self.geometry_inputs.items():
            spin.setEnabled(mode != "edit" or key == "width")
        self.view.show_page(True)
        if mode == "sign" and not self.signature_data:
            self.choose_signature()

    def choose_signature(self):
        dialog = SignatureDialog(self, self.data_dir / "signature.png")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.signature_data = dialog.data
            self.signature_button.setText("서명 변경")
            self.update_preview()
        self.update_state()

    def select_text(self, span):
        if span == self.selected:
            return
        if not self.resolve_draft():
            return
        # 방금 다른 본문을 적용했다면 추출 순서가 달라질 수 있다.
        span = next((s for s in self.model.page_spans(self.page_number)
                     if s.text == span.text and s.bbox == span.bbox), None)
        if span is None:
            self.statusBar().showMessage("문서가 바뀌었습니다. 수정할 글자를 다시 선택하세요.", 5000)
            return
        self.selected = span
        self.editor.setPlainText(span.text)
        self.size_input.setValue(span.size)
        self.ink = QColor.fromRgbF(*rgb(span.color))
        self.color_button.setStyleSheet(f"color: {self.ink.name()};")
        self.font_label.setText(f"원본 글꼴: {span.font}\n새 글자가 없으면 맑은 고딕으로 대체합니다.")
        self.set_area(fitz.Rect(span.bbox))
        self._draft_baseline = self.draft_signature()
        self.editor.setFocus()
        self.draft_changed()

    def select_area(self, rect):
        self.selected = None
        self.set_area(rect)
        if self.mode == "text":
            self.editor.setFocus()
        self.update_state()

    def select_object(self, object_id):
        if self.selected_object and self.selected_object["id"] == object_id:
            return True
        if not self.resolve_draft():
            return False
        item = next((o for o in self.model.page_objects(self.page_number) if o["id"] == object_id), None)
        if item is None:
            return False
        self.selected_object = item
        self.selected = None
        if item["kind"] == "text":
            self.editor.setPlainText(item["text"])
            self.size_input.setValue(item["size"])
            self.ink = QColor.fromRgbF(*item["color"])
            self.color_button.setStyleSheet(f"color: {self.ink.name()};")
            self.font_label.setText("추가한 텍스트 · 맑은 고딕")
        else:
            self.editor.clear()
        self.set_area(fitz.Rect(item["rect"]))
        self._draft_baseline = self.draft_signature()
        self.draft_changed()
        return True

    def delete_selected_object(self):
        if self.mode != "object" or self.selected_object is None:
            return False
        try:
            self.model.delete_object(self.page_number, self.selected_object["id"])
            self.after_edit()
            self.statusBar().showMessage("추가 항목을 삭제했습니다. 실행 취소로 되돌릴 수 있습니다.", 8000)
            return True
        except Exception as exc:
            self.error(exc)
            return False

    def set_area(self, rect):
        self.area = fitz.Rect(rect)
        self._refreshing = True
        for key, value in zip(("x", "y", "width", "height"), (rect.x0, rect.y0, rect.width, rect.height)):
            self.geometry_inputs[key].setValue(value)
        self._refreshing = False
        self.update_preview()

    def geometry_changed(self):
        if self._refreshing or self.area is None:
            return
        x, y, w, h = (self.geometry_inputs[key].value() for key in ("x", "y", "width", "height"))
        self.area = fitz.Rect(x, y, x + w, y + h)
        self.update_preview()
        self.update_state()

    def update_preview(self):
        if self.area is not None:
            self.view.show_selection(self.area, self.signature_data if self.mode == "sign" else None)
        self.draft_changed()

    def draft_changed(self):
        self.update_state()
        self.preview_timer.stop()
        if self.mode in ("edit", "text", "object") and self.area is not None and self.has_draft:
            self.preview_note.setText("미리보기 준비 중…")
            self.preview_timer.start(220)
        else:
            self.preview_note.clear()
            self.view.restore_page_image()

    def refresh_text_preview(self):
        self.preview_timer.stop()
        if self.area is None or self.mode not in ("edit", "text", "object") or not self.has_draft:
            return
        try:
            if self.mode == "object":
                pix = self.model.preview_object(self.page_number, self.selected_object["id"], self.area,
                    self.editor.toPlainText(), self.size_input.value(),
                    (self.ink.redF(), self.ink.greenF(), self.ink.blueF()), self.view.render_scale())
                result = None
            else:
                pix, result = self.model.preview_text(
                    self.page_number, self.area, self.editor.toPlainText(), self.size_input.value(),
                    (self.ink.redF(), self.ink.greenF(), self.ink.blueF()), self.view.render_scale(), self.selected)
            self.view.page_item.setPixmap(pixmap_from_fitz(pix))
            self.view.preview_rendered = True
            message = "미리보기 · 아직 문서에 적용하지 않았습니다."
            if result and result.get("deleted"):
                message = "삭제 미리보기 · 적용하거나 저장하면 선택한 본문이 삭제됩니다."
            elif result and result["substituted"]:
                message += "\n맑은 고딕으로 표시됩니다."
            self.preview_note.setText(message)
        except Exception as exc:
            self.view.restore_page_image()
            self.preview_note.setText("적용할 수 없음 · " + str(exc))

    def clear_selection(self):
        if not self.resolve_draft():
            return False
        self._clear_selection()
        return True

    def _clear_selection(self):
        self.preview_timer.stop()
        self.view.clear_read_selection()
        self.search_hit = None
        self.selected = self.area = None
        self.selected_object = None
        self._draft_baseline = None
        self.editor.clear()
        if self.model.doc:
            self.view.show_page(True)
        self.update_state()

    def pick_color(self):
        color = QColorDialog.getColor(self.ink, self, "글자 색상")
        if color.isValid():
            self.ink = color
            self.color_button.setStyleSheet(f"color: {color.name()};")
            self.draft_changed()

    def draft_signature(self):
        return (self.editor.toPlainText(), self.size_input.value(), self.ink.rgb(),
                tuple(self.area) if self.area is not None else None)

    @property
    def has_draft(self):
        if self.mode == "object":
            return self.selected_object is not None and self.draft_signature() != self._draft_baseline
        if self.mode == "edit":
            return self.selected is not None and self.draft_signature() != self._draft_baseline
        if self.mode == "text":
            return bool(self.editor.toPlainText().strip())
        if self.mode == "sign":
            return self.area is not None and self.signature_data is not None
        return False

    def _ask_draft_action(self):
        box = QMessageBox(self)
        box.setWindowTitle("입력한 내용 처리")
        box.setText("아직 문서에 적용하지 않은 내용이 있습니다.")
        apply = box.addButton("적용하고 계속", QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton("입력 버리기", QMessageBox.ButtonRole.DestructiveRole)
        cancel = box.addButton("취소", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(cancel)
        box.exec()
        return "apply" if box.clickedButton() == apply else "discard" if box.clickedButton() == discard else "cancel"

    def resolve_draft(self):
        if not self.has_draft:
            return True
        action = self._ask_draft_action()
        if action == "apply":
            return self.apply_edit()
        if action == "discard":
            self._clear_selection()
            return True
        return False

    def apply_edit(self):
        if self.area is None:
            self.error(EditError("문서 위에서 텍스트를 넣을 영역을 먼저 지정해 주세요."))
            return False
        try:
            color = (self.ink.redF(), self.ink.greenF(), self.ink.blueF())
            result = None
            if self.mode == "object" and self.selected_object:
                self.model.update_object(self.page_number, self.selected_object["id"], self.area,
                    self.editor.toPlainText(), self.size_input.value(), color)
            elif self.mode == "edit" and self.selected:
                result = self.model.replace_text(self.page_number, self.selected, self.editor.toPlainText(),
                                                 self.size_input.value(), color, self.area.width)
            elif self.mode == "text":
                self.model.add_text(self.page_number, self.area, self.editor.toPlainText(), self.size_input.value(), color)
            elif self.mode == "sign" and self.signature_data:
                self.model.add_signature(self.page_number, self.area, self.signature_data)
            else:
                return False
            self.after_edit()
            message = "변경 내용을 적용했습니다. 파일로 남기려면 저장해 주세요."
            if result and result.get("deleted"):
                message = "선택한 본문을 삭제했습니다. 실행 취소로 되돌릴 수 있습니다."
            elif result:
                message = f"본문 수정 완료 · {result['font']} · {result['size']:.1f} pt"
                if result["substituted"]:
                    message += " · 원본 글꼴의 글자·문자 매핑을 보존할 수 없어 글꼴을 대체했습니다."
            self.statusBar().showMessage(message, 12000)
            return True
        except Exception as exc:
            self.error(exc)
            return False

    def after_edit(self):
        self._clear_selection()
        self.invalidate_search()
        self._thumbnail_generation += 1
        self._rendered_thumbs.clear()
        self.schedule_thumbnails()
        self.update_state()

    def undo(self):
        if self.editor.hasFocus() and self.editor.document().isUndoAvailable():
            self.editor.undo()
            return
        if not self.resolve_draft():
            return
        self.model.undo()
        self.after_edit()

    def redo(self):
        if self.editor.hasFocus() and self.editor.document().isRedoAvailable():
            self.editor.redo()
            return
        if not self.resolve_draft():
            return
        self.model.redo()
        self.after_edit()

    def save_as(self):
        if not self.model.doc:
            return False
        source = self.model.path
        suggestion = source.with_name(source.stem + "_편집.pdf")
        path, _ = QFileDialog.getSaveFileName(self, "PDF 저장", str(suggestion), "PDF 문서 (*.pdf)")
        if not path:
            return False
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
            if Path(path).exists():
                answer = QMessageBox.question(self, "파일 덮어쓰기", "같은 이름의 PDF가 있습니다. 교체할까요?",
                                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                              QMessageBox.StandardButton.No)
                if answer != QMessageBox.StandardButton.Yes:
                    return False
        return self.save_to(path)

    def save_to(self, path):
        try:
            if self.has_draft and not self.apply_edit():
                return False
            self.model.save(path)
            self.clear_recovery()
            self.update_state()
            self.statusBar().showMessage(f"저장 완료 · {path}", 15000)
            return True
        except Exception as exc:
            self.error(exc)
            return False

    def update_state(self):
        opened = self.model.doc is not None
        self.save_button.setEnabled(opened and not self.model.encrypted and not self.model.signed)
        for key, button in self.mode_buttons.items():
            button.setEnabled(opened and (key == "view" or self.model.editable))
        self.undo_button.setEnabled(self.model.can_undo)
        self.redo_button.setEnabled(self.model.can_redo)
        self.apply_button.setEnabled(self.area is not None and (self.mode != "sign" or self.signature_data is not None))
        self.delete_object_button.setEnabled(self.selected_object is not None)
        if self.mode == "object":
            text_object = self.selected_object is not None and self.selected_object["kind"] == "text"
            self.editor.setVisible(text_object)
            self.font_label.setVisible(text_object)
            self.size_input.setEnabled(text_object)
            self.color_button.setEnabled(text_object)
        deleting = self.mode == "edit" and self.selected is not None and not self.editor.toPlainText().strip()
        self.apply_button.setText("본문 삭제 적용" if deleting else "문서에 적용")
        self.filename.setText(self.model.path.name if opened else "나만의 PDF 작업 공간")
        self.save_state.setText("읽기 전용 문서" if opened and not self.model.editable else
                               "적용 전 입력이 있습니다" if self.has_draft else
                               "저장하지 않은 변경 사항" if self.model.dirty else "내 PC에서만 처리")
        self.setWindowTitle((self.model.path.name + (" *" if self.model.dirty or self.has_draft else "") + " — " if opened else "") + "Paperlight")

    def change_zoom(self, factor):
        if not self.model.doc:
            return
        self.fit_mode = False
        self.fit_timer.stop()
        self.zoom = max(.25, min(3, self.zoom * factor))
        self.zoom_label.setText(f"{round(self.zoom * 100)}%")
        self.view.show_page(True)
        self.update_preview()

    def fit_width(self):
        if not self.model.doc:
            return
        self.fit_mode = True
        width = self.model.doc[self.page_number].rect.width
        self.zoom = max(.25, min(2, (self.view.viewport().width() - 70) / width))
        self.zoom_label.setText(f"{round(self.zoom * 100)}%")
        self.view.show_page()
        self.update_preview()

    def invalidate_search(self):
        self._search_key = None
        self._search_hits = []
        self._search_cursor = -1
        self.search_hit = None
        self.search_count.clear()
        if hasattr(self, "view") and self.area is None and self.view.preview is not None:
            self.view.scene().removeItem(self.view.preview)
            self.view.preview = None

    def search(self, direction=1):
        text = self.search_box.text().strip()
        if not self.model.doc or not text:
            return
        if not self.resolve_draft():
            return
        key = (self.model.doc, text)
        if key != self._search_key:
            self._search_hits = [(i, rect) for i in range(self.model.doc.page_count)
                                 for rect in self.model.doc[i].search_for(text)]
            self._search_key = key
            self._search_cursor = -1
        if not self._search_hits:
            self.search_count.setText("0 / 0")
            self.statusBar().showMessage(f"‘{text}’ 검색 결과가 없습니다.", 5000)
            return
        if self._search_cursor >= 0 and self.search_hit is not None:
            cursor = (self._search_cursor + direction) % len(self._search_hits)
        elif direction > 0:
            cursor = next((i for i, hit in enumerate(self._search_hits) if hit[0] >= self.page_number), 0)
        else:
            cursor = next((i for i in range(len(self._search_hits) - 1, -1, -1)
                           if self._search_hits[i][0] <= self.page_number), len(self._search_hits) - 1)
        index, rect = self._search_hits[cursor]
        if not self.go_page(index):
            return
        self.view.clear_read_selection()
        self.search_hit = (index, rect)
        self._search_cursor = cursor
        self.search_count.setText(f"{cursor + 1} / {len(self._search_hits)}")
        self.view.show_selection(rect)
        box = rect * self.model.doc[index].rotation_matrix
        self.view.centerOn((box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2)
        self.statusBar().showMessage(f"‘{text}’ · {cursor + 1}/{len(self._search_hits)}번째 · {index + 1}페이지", 5000)

    def confirm_discard(self):
        if not self.model.dirty and not self.has_draft:
            return True
        box = QMessageBox(self)
        box.setWindowTitle("변경 내용 저장")
        box.setText("저장하지 않은 변경 내용이 있습니다.")
        save = box.addButton("저장", QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton("저장하지 않음", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("취소", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() == save:
            return self.save_as()
        return box.clickedButton() == discard

    def error(self, exc):
        QMessageBox.warning(self, "작업을 완료할 수 없습니다", str(exc))

    def closeEvent(self, event):
        if self.confirm_discard():
            self.recovery_timer.stop()
            self.clear_recovery(release=True)
            self._thumbnail_generation += 1
            self.fit_timer.stop()
            self.preview_timer.stop()
            event.accept()
        else:
            self.checkpoint_recovery()
            event.ignore()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(u.toLocalFile().lower().endswith(".pdf") for u in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if url.toLocalFile().lower().endswith(".pdf"):
                if self.open_file(url.toLocalFile()):
                    event.acceptProposedAction()
                else:
                    event.ignore()
                break
