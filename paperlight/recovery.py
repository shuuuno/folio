"""창별 로컬 복구본. PDF와 입력 상태를 한 파일로 원자적으로 교체한다."""
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import tempfile
from uuid import uuid4
from zipfile import ZipFile, ZIP_STORED

from PySide6.QtCore import QLockFile, Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QHBoxLayout, QPushButton


class RecoveryStore:
    def __init__(self, directory, session_id=None):
        self.directory = Path(directory)
        self.id = session_id or uuid4().hex
        if not re.fullmatch(r"[a-f0-9]{32}", self.id):
            raise ValueError("올바르지 않은 복구본 이름입니다.")
        self.path = self.directory / (self.id + ".plr")
        self.lock = QLockFile(str(self.directory / (self.id + ".lock")))
        self.lock.setStaleLockTime(0)

    def acquire(self):
        if self.lock.isLocked():
            return True
        self.directory.mkdir(parents=True, exist_ok=True)
        return self.lock.tryLock(0)

    def release(self):
        self.lock.unlock()

    def _require_lock(self):
        if not self.lock.isLocked():
            raise RuntimeError("다른 창에서 사용 중인 복구본입니다.")

    def write(self, pdf, state):
        if not self.acquire():
            raise RuntimeError("복구본을 잠그지 못했습니다.")
        meta = dict(version=1, session=self.id, updated=datetime.now().astimezone().isoformat(timespec="seconds"),
                    pdf_sha256=sha256(pdf).hexdigest(), state=state)
        fd, temporary = tempfile.mkstemp(prefix=self.id + "-", suffix=".tmp", dir=self.directory)
        os.close(fd)
        try:
            with ZipFile(temporary, "w", compression=ZIP_STORED) as archive:
                archive.writestr("document.pdf", pdf)
                archive.writestr("state.json", json.dumps(meta, ensure_ascii=False, allow_nan=False).encode("utf-8"))
            with open(temporary, "r+b") as stream:
                os.fsync(stream.fileno())
            self._read(Path(temporary), full=True)
            os.replace(temporary, self.path)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return meta

    def _read(self, path, full):
        with ZipFile(path) as archive:
            if set(archive.namelist()) != {"document.pdf", "state.json"}:
                raise ValueError("복구본 구성을 확인하지 못했습니다.")
            if archive.getinfo("state.json").file_size > 32 * 1024 * 1024:
                raise ValueError("복구 입력 정보가 너무 큽니다.")
            meta = json.loads(archive.read("state.json"))
            if (meta.get("version") != 1 or meta.get("session") != self.id
                    or not isinstance(meta.get("state"), dict)
                    or not isinstance(meta["state"].get("source"), str)
                    or not Path(meta["state"]["source"]).is_absolute()
                    or not isinstance(meta.get("updated"), str)):
                raise ValueError("지원하지 않거나 손상된 복구본입니다.")
            pdf = archive.read("document.pdf") if full else None
            if full and sha256(pdf).hexdigest() != meta.get("pdf_sha256"):
                raise ValueError("복구 PDF의 검증값이 일치하지 않습니다.")
            return meta, pdf

    def read(self):
        self._require_lock()
        return self._read(self.path, full=True)

    def clear(self):
        self._require_lock()
        self.path.unlink(missing_ok=True)

    @classmethod
    def available(cls, directory):
        result = []
        for path in Path(directory).glob("*.plr"):
            if not re.fullmatch(r"[a-f0-9]{32}", path.stem):
                continue
            store = cls(directory, path.stem)
            if not store.acquire():
                continue
            try:
                meta, _ = store._read(path, full=False)
                result.append(dict(id=store.id, source=meta["state"]["source"], updated=meta["updated"], error=False))
            except Exception:
                result.append(dict(id=store.id, source="손상된 복구본", updated="", error=True))
            finally:
                store.release()
        return sorted(result, key=lambda item: item["updated"], reverse=True)


class RecoveryDialog(QDialog):
    def __init__(self, parent, records):
        super().__init__(parent)
        self.action = "later"
        self.session_id = None
        self.setWindowTitle("이전 작업 복구")
        self.resize(560, 330)
        layout = QVBoxLayout(self)
        explanation = QLabel("저장되지 않은 작업의 복구본이 있습니다.\n원본을 바꾸지 않고 마지막 복구본에서 이어갑니다.")
        layout.addWidget(explanation)
        self.list = QListWidget()
        for record in records:
            name = Path(record["source"]).name
            try:
                updated = datetime.fromisoformat(record["updated"]).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                updated = "읽을 수 없는 복구본"
            item = QListWidgetItem(f"{name}\n{updated}")
            item.setToolTip(record["source"])
            item.setData(Qt.ItemDataRole.UserRole, record["id"])
            self.list.addItem(item)
        layout.addWidget(self.list)
        self.list.setCurrentRow(0)
        buttons = QHBoxLayout()
        for label, action in [("선택 복구본 삭제", "discard"), ("나중에", "later"), ("복구", "recover")]:
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, value=action: self.choose(value))
            buttons.addWidget(button)
            if action == "recover":
                button.setObjectName("primary")
                button.setDefault(True)
        layout.addLayout(buttons)

    def choose(self, action):
        item = self.list.currentItem()
        self.session_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        self.action = action
        self.accept()
