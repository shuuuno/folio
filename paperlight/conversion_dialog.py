import json
from pathlib import Path
import sys
import tempfile

from PySide6.QtCore import QProcess, QUrl, Signal, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget,
                              QComboBox, QLineEdit, QFileDialog, QProgressBar, QMessageBox)


class ConversionDialog(QDialog):
    pdf_ready = Signal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("파일 변환")
        self.resize(700, 620)
        self.setModal(False)
        self.running = False
        self.process = None
        self.temporary = None
        self.outputs = []
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("PDF ↔ 이미지 · Word · PowerPoint"))
        row = QHBoxLayout()
        add = QPushButton("파일 선택")
        add.clicked.connect(self.choose_sources)
        row.addWidget(add)
        current = QPushButton("현재 탭의 PDF 사용")
        current.clicked.connect(self.use_current)
        row.addWidget(current)
        self.source_controls = [add, current]
        layout.addLayout(row)
        self.sources = QListWidget()
        layout.addWidget(self.sources)
        self.format = QComboBox()
        for label, value in (("PDF (.pdf)", "pdf"), ("PNG — 페이지별 이미지", "png"),
                             ("JPG — 페이지별 이미지", "jpg"), ("Word (.docx)", "docx"), ("PowerPoint (.pptx)", "pptx")):
            self.format.addItem(label, value)
        self.format.setCurrentIndex(1)
        layout.addWidget(self.format)
        self.mode = QComboBox()
        self.mode.addItem("편집용 — 글자·이미지로 재구성", "editable")
        self.mode.addItem("모양 보존 — 페이지를 이미지로 넣기", "appearance")
        layout.addWidget(self.mode)
        self.dpi = QComboBox()
        for dpi in (96, 150, 300):
            self.dpi.addItem(f"이미지 해상도 {dpi} DPI", dpi)
        self.dpi.setCurrentIndex(1)
        layout.addWidget(self.dpi)
        hint = QLabel("Word/PPT → PDF: Microsoft Office 또는 LibreOffice가 필요합니다.\n"
                      "PDF → Word 편집용: 본문·그림 순서로 재구성하므로 표·단·배치가 달라질 수 있습니다.\n"
                      "PDF → PPT 편집용: 가로 본문은 글자 상자, 도형은 배경으로 보존합니다. 회전/세로쓰기 페이지는 이미지로 유지합니다.\n"
                      "스캔 PDF는 이미지로 유지되며 OCR은 하지 않습니다. 원본은 변경하지 않습니다.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        row = QHBoxLayout()
        self.destination = QLineEdit()
        self.destination.setPlaceholderText("결과 폴더")
        row.addWidget(self.destination)
        browse = QPushButton("폴더 선택")
        browse.clicked.connect(self.choose_destination)
        row.addWidget(browse)
        self.source_controls += [self.format, self.mode, self.dpi, self.destination, browse]
        layout.addLayout(row)
        self.status = QLabel("파일을 선택하세요. 같은 이름의 결과는 덮어쓰지 않습니다.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        layout.addWidget(self.progress)
        row = QHBoxLayout()
        self.start_button = QPushButton("변환 시작")
        self.start_button.setObjectName("primary")
        self.start_button.clicked.connect(self.start)
        row.addWidget(self.start_button)
        self.cancel_button = QPushButton("변환 취소")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel)
        row.addWidget(self.cancel_button)
        self.open_folder = QPushButton("결과 폴더 열기")
        self.open_folder.setEnabled(False)
        self.open_folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.destination.text())))
        row.addWidget(self.open_folder)
        self.open_pdf = QPushButton("결과 PDF 탭으로 열기")
        self.open_pdf.setEnabled(False)
        self.open_pdf.clicked.connect(lambda: [self.pdf_ready.emit(p) for p in self.outputs if p.lower().endswith(".pdf")])
        row.addWidget(self.open_pdf)
        layout.addLayout(row)
        self.current_snapshot = None

    def choose_sources(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "변환할 파일", "", "지원 파일 (*.pdf *.jpg *.jpeg *.png *.doc *.docx *.ppt *.pptx)")
        if paths:
            self.sources.clear()
            self.sources.addItems(paths)
            self.format.setCurrentIndex(1 if all(Path(p).suffix.lower() == ".pdf" for p in paths) else 0)
            if not self.destination.text():
                self.destination.setText(str(Path(paths[0]).parent))

    def use_current(self):
        editor = self.parent().current
        if not editor.model.doc:
            return
        if editor.model.encrypted or not (editor.model.doc.permissions & 16):
            QMessageBox.warning(self, "변환 제한", "암호화 또는 복사 제한 문서는 변환하지 않습니다.")
            return
        if not editor.resolve_draft():
            return
        if self.current_snapshot:
            self.current_snapshot.cleanup()
        self.current_snapshot = tempfile.TemporaryDirectory(prefix="paperlight-current-")
        path = Path(self.current_snapshot.name) / editor.model.path.name
        path.write_bytes(editor.model.doc.tobytes(garbage=3, deflate=True))
        self.sources.clear()
        self.sources.addItem(editor.model.path.name + " (현재 편집본)")
        self.sources.item(0).setData(Qt.ItemDataRole.UserRole, str(path))
        self.destination.setText(str(editor.model.path.parent))
        self.format.setCurrentIndex(1)
        self.status.setText("현재 탭의 편집 내용을 복사했습니다. 원본 파일에는 저장하지 않았습니다.")

    def choose_destination(self):
        path = QFileDialog.getExistingDirectory(self, "결과 폴더", self.destination.text())
        if path:
            self.destination.setText(path)

    def start(self):
        if self.running:
            return
        sources = [self.sources.item(i).data(Qt.ItemDataRole.UserRole) or self.sources.item(i).text()
                   for i in range(self.sources.count())]
        if not sources or not Path(self.destination.text()).is_dir():
            QMessageBox.information(self, "파일 변환", "입력 파일과 결과 폴더를 선택하세요.")
            return
        self.temporary = tempfile.TemporaryDirectory(prefix="paperlight-job-")
        root = Path(self.temporary.name)
        request = dict(sources=sources, destination=self.destination.text(), format=self.format.currentData(),
                       mode=self.mode.currentData(), dpi=self.dpi.currentData(), cancel_file=str(root / "cancel"))
        (root / "request.json").write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        self.process = QProcess(self)
        self.process.finished.connect(self.process_finished)
        self.process.errorOccurred.connect(self.failed_to_start)
        arguments = [] if getattr(sys, "frozen", False) else ["-m", "paperlight"]
        arguments += ["--convert-worker", str(root / "request.json"), str(root / "result.json")]
        self.running = True
        self.outputs = []
        self.open_folder.setEnabled(False)
        self.open_pdf.setEnabled(False)
        for widget in self.source_controls + [self.start_button]:
            widget.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setRange(0, 0)
        self.status.setText("변환 중입니다. 다른 탭의 PDF는 계속 사용할 수 있습니다.")
        self.process.start(sys.executable, arguments)

    def cancel(self):
        if self.running:
            (Path(self.temporary.name) / "cancel").touch()
            self.status.setText("취소 요청됨 · 현재 Office 파일 처리 중이면 완료 후 취소합니다.")
            self.cancel_button.setEnabled(False)

    def failed_to_start(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.process_finished()

    def process_finished(self, *args):
        if not self.running:
            return
        path = Path(self.temporary.name) / "result.json"
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
            self.outputs = result.get("outputs", [])
            if result["status"] == "ok":
                self.status.setText(f"변환 완료 · 결과 {len(self.outputs)}개\n" + "\n".join(Path(p).name for p in self.outputs))
            elif result["status"] == "cancelled":
                self.status.setText("변환을 취소했습니다. 결과 파일을 만들지 않았습니다.")
            else:
                self.status.setText("변환 실패 · " + result.get("error", "알 수 없는 오류"))
        except Exception:
            self.status.setText("변환 프로세스가 종료되었습니다. 입력 파일과 저장 공간을 확인해 주세요.")
        self.running = False
        self.progress.setRange(0, 1)
        self.progress.setValue(1 if self.outputs else 0)
        self.cancel_button.setEnabled(False)
        self.open_folder.setEnabled(bool(self.outputs))
        self.open_pdf.setEnabled(any(p.lower().endswith(".pdf") for p in self.outputs))
        for widget in self.source_controls + [self.start_button]:
            widget.setEnabled(True)
        self.process.deleteLater()
        self.process = None
        self.temporary.cleanup()
        self.temporary = None

    def closeEvent(self, event):
        # 닫기는 창만 숨긴다. 실행 중 프로세스는 종료하지 않는다.
        self.hide()
        event.ignore()
