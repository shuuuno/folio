from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import os
import tempfile
import math
import base64

import pymupdf as fitz
from . import objects as placed


class EditError(Exception):
    pass


@dataclass(frozen=True)
class TextSpan:
    text: str
    bbox: tuple
    origin: tuple
    font: str
    size: float
    color: int
    direction: tuple
    index: int


def spans(page) -> list[TextSpan]:
    result = []
    for block in page.get_text("dict", flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES)["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                if span["text"].strip():
                    result.append(TextSpan(span["text"], tuple(span["bbox"]), tuple(span["origin"]),
                                           span["font"], span["size"], span["color"],
                                           tuple(line["dir"]), len(result)))
    return result


def rgb(value: int):
    return ((value >> 16 & 255) / 255, (value >> 8 & 255) / 255, (value & 255) / 255)


def _character_positions(page, excluded_index=None):
    """Keep per-character coordinates: equal extracted strings can still move."""
    result = []
    index = 0
    for block in page.get_text("rawdict", flags=fitz.TEXTFLAGS_RAWDICT & ~fitz.TEXT_PRESERVE_IMAGES)["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                chars = span["chars"]
                if not "".join(c["c"] for c in chars).strip():
                    continue
                if index != excluded_index:
                    result.extend((c["c"], tuple(c["origin"]), tuple(c["bbox"])) for c in chars)
                index += 1
    return result


def system_font(bold=False):
    path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / ("malgunbd.ttf" if bold else "malgun.ttf")
    if not path.exists():
        raise EditError("한글 글꼴을 찾지 못했습니다. Windows 맑은 고딕을 설치해 주세요.")
    return fitz.Font(fontfile=str(path))


def _font_roundtrips(font, text):
    # Some embedded CFF subsets report glyph coverage but lose Unicode mapping
    # when reinserted as a new font resource. Probe before removing any content.
    with fitz.open() as probe:
        page = probe.new_page(width=max(100, font.text_length(text, fontsize=10) + 30), height=100)
        page.insert_font(fontname="Probe", fontbuffer=font.buffer)
        page.insert_text((10, 40), text, fontsize=10, fontname="Probe")
        return text in page.get_text()


class PdfDocument:
    def __init__(self):
        self.doc = None
        self.path = None
        self._undo = []
        self._redo = []
        self.revision = 0
        self.saved_revision = 0
        self._serial = 0
        self.encrypted = False
        self.editable = True
        self.signed = False

    def open(self, path, password=""):
        return self.open_bytes(Path(path).read_bytes(), path, password)

    def open_bytes(self, data, path, password=""):
        candidate = fitz.open(stream=data, filetype="pdf")
        encrypted = candidate.needs_pass or bool(candidate.metadata and candidate.metadata.get("encryption"))
        if candidate.needs_pass and not candidate.authenticate(password):
            candidate.close()
            raise EditError("암호가 필요하거나 암호가 올바르지 않습니다.")
        if not candidate.is_pdf or candidate.page_count == 0:
            candidate.close()
            raise EditError("열 수 있는 PDF 페이지가 없습니다.")
        if self.doc:
            self.doc.close()
        self.doc, self.path = candidate, Path(path)
        self.encrypted = encrypted
        self.signed = candidate.get_sigflags() > 0
        self.editable = not encrypted and not self.signed and bool(candidate.permissions & fitz.PDF_PERM_MODIFY)
        self._undo.clear()
        self._redo.clear()
        self.revision = self.saved_revision = self._serial = 0

    @property
    def dirty(self):
        return self.revision != self.saved_revision

    @property
    def can_undo(self):
        return bool(self._undo)

    @property
    def can_redo(self):
        return bool(self._redo)

    def _bytes(self):
        return self.doc.tobytes(garbage=3, deflate=True, encryption=fitz.PDF_ENCRYPT_NONE)

    def _edit(self, operation):
        if not self.doc:
            raise EditError("먼저 PDF를 열어 주세요.")
        if not self.editable:
            raise EditError("암호화·전자서명 필드·편집 제한이 있는 PDF는 읽기 전용으로 엽니다.")
        before = self._bytes()
        candidate = fitz.open(stream=before, filetype="pdf")
        try:
            result = operation(candidate)
        except ValueError as exc:
            candidate.close()
            raise EditError(str(exc)) from exc
        except Exception:
            candidate.close()
            raise
        self._undo.append((before, self.revision))
        while len(self._undo) > 1 and (len(self._undo) > 20 or sum(len(x[0]) for x in self._undo) > 96 * 1024 * 1024):
            self._undo.pop(0)
        self._redo.clear()
        self.doc.close()
        self.doc = candidate
        self._serial += 1
        self.revision = self._serial
        return result

    def undo(self):
        if self._undo:
            self._restore(self._undo, self._redo)

    def redo(self):
        if self._redo:
            self._restore(self._redo, self._undo)

    def _restore(self, source, target):
        target.append((self._bytes(), self.revision))
        data, revision = source.pop()
        self.doc.close()
        self.doc = fitz.open(stream=data, filetype="pdf")
        self.revision = revision

    def page_spans(self, number):
        return spans(self.doc[number])

    def page_objects(self, number):
        return placed.objects(self.doc[number])

    def update_object(self, number, object_id, rect, text=None, size=None, color=None):
        def operation(doc):
            page = doc[number]
            item = next((o for o in placed.objects(page) if o["id"] == object_id), None)
            if item is None:
                raise EditError("추가 항목을 찾지 못했습니다. 다시 선택해 주세요.")
            box = fitz.Rect(rect)
            self._check_rect(page, box)
            position = page.get_contents().index(item["xref"])
            page = placed.remove(page, [item])
            item["rect"] = list(box)
            if item["kind"] == "text":
                item.update(text=item["text"] if text is None else text,
                            size=item["size"] if size is None else size,
                            color=item["color"] if color is None else color)
                if not item["text"].strip():
                    raise EditError("내용을 입력하거나 ‘선택 항목 삭제’를 이용해 주세요.")
            font = self._font(doc, page, None, item["text"])[0] if item["kind"] == "text" else None
            placed.insert(page, item, font)
            new = next(o for o in placed.objects(page) if o["id"] == object_id)
            contents = [x for x in page.get_contents() if x != new["xref"]]
            contents.insert(position, new["xref"])
            placed.set_contents(page, contents)
        return self._edit(operation)

    def delete_object(self, number, object_id):
        def operation(doc):
            page = doc[number]
            item = next((o for o in placed.objects(page) if o["id"] == object_id), None)
            if item is None:
                raise EditError("추가 항목을 찾지 못했습니다. 다시 선택해 주세요.")
            placed.remove(page, [item])
        return self._edit(operation)

    def preview_object(self, number, object_id, rect, text, size, color, scale):
        preview = PdfDocument()
        preview.doc = fitz.open()
        preview.editable = self.editable
        try:
            preview.doc.insert_pdf(self.doc, from_page=number, to_page=number)
            preview.update_object(0, object_id, rect, text, size, color)
            return preview.doc[0].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        finally:
            preview.doc.close()

    def _font(self, doc, page, span, text):
        if span:
            target = span.font.split("+")[-1].replace(" ", "").lower()
            for item in page.get_fonts(full=True):
                name = item[3].split("+")[-1].replace(" ", "").lower()
                if name != target or not item[0]:
                    continue
                try:
                    _, _, _, buffer = doc.extract_font(item[0])
                    font = fitz.Font(fontbuffer=buffer)
                    if all(c.isspace() or font.has_glyph(ord(c), fallback=False) for c in text) and _font_roundtrips(font, text):
                        return font, False
                except (ValueError, RuntimeError):
                    pass
            base = {"Helvetica": "helv", "Helvetica-Bold": "hebo", "Times-Roman": "tiro", "Courier": "cour"}.get(span.font)
            if base and all(ord(c) < 256 for c in text):
                return fitz.Font(base), False
        font = system_font(bool(span and "bold" in span.font.lower()))
        if not all(c.isspace() or font.has_glyph(ord(c), fallback=False) for c in text):
            raise EditError("선택한 글꼴에서 표시할 수 없는 문자가 있습니다.")
        return font, bool(span)

    def replace_text(self, number, selected: TextSpan, text: str, size=None, color=None, width=None):
        deleting = not text.strip()
        if not deleting and ("\n" in text or "\r" in text):
            raise EditError("본문은 한 줄씩 수정합니다. 여러 줄은 텍스트 추가로 넣어 주세요.")

        def operation(doc, selected=selected):
            page = doc[number]
            current = spans(page)
            if selected.index >= len(current) or current[selected.index] != selected:
                raise EditError("문서가 바뀌었습니다. 수정할 글자를 다시 선택해 주세요.")
            managed = placed.objects(page)
            if managed:
                page = placed.remove(page, managed)
                current = spans(page)
                found = next((s for s in current if s.text == selected.text and s.bbox == selected.bbox), None)
                if found is None:
                    item = next((o for o in managed if o["kind"] == "text" and o["text"] == selected.text
                                 and fitz.Rect(o["rect"]).intersects(fitz.Rect(selected.bbox))), None)
                    if item is None:
                        raise EditError("추가한 텍스트는 ‘배치 편집’에서 수정해 주세요.")
                    for other in managed:
                        if other["id"] == item["id"]:
                            if deleting:
                                continue
                            other.update(text=text, size=size or other["size"], color=color or other["color"])
                        placed.insert(page, other, system_font() if other["kind"] == "text" else None)
                    return {"deleted": deleting, "substituted": False, "font": "Malgun Gothic", "size": size or item["size"]}
                selected = found
            if abs(selected.direction[0] - 1) > 0.01 or abs(selected.direction[1]) > 0.01:
                raise EditError("회전·세로쓰기 본문 수정은 지원하지 않습니다. 텍스트 추가를 이용해 주세요.")
            if any(a.type[0] == fitz.PDF_ANNOT_REDACT for a in (page.annots() or [])):
                raise EditError("처리되지 않은 먹칠 표시가 있는 페이지는 본문을 수정할 수 없습니다.")
            box = fitz.Rect(selected.bbox)
            if any(kind == "ignore-text" and box.intersects(fitz.Rect(bounds)) for kind, bounds in page.get_bboxlog()):
                raise EditError("스캔본의 숨은 OCR 글자는 수정할 수 없습니다. 텍스트 추가를 이용해 주세요.")
            cut = fitz.Rect(box.x0 + .1, box.y0 + .1, box.x1 - .1, box.y1 - .1)
            if any(cut.intersects(link["from"]) for link in page.get_links()):
                raise EditError("링크가 포함된 글자는 링크 보존을 위해 수정할 수 없습니다.")
            for other in current:
                if other.index != selected.index and (cut & fitz.Rect(other.bbox)).get_area() > .1:
                    raise EditError("다른 글자와 겹친 영역입니다. 이 본문은 안전하게 수정할 수 없습니다.")
            if not deleting:
                available = float(width or box.width)
                if available <= 0 or selected.origin[0] + available > page.cropbox.width + .1:
                    raise EditError("텍스트 영역이 페이지 밖으로 나갑니다.")
                font, substituted = self._font(doc, page, selected, text)
                wanted = float(size or selected.size)
                length = font.text_length(text, fontsize=wanted)
                actual = min(wanted, wanted * available / max(length, .01))
                if actual < max(5, wanted * .65):
                    raise EditError("문장이 영역보다 너무 깁니다. 영역 너비를 늘리거나 문장을 줄여 주세요.")
                newbox = fitz.Rect(selected.origin[0], selected.origin[1] - font.ascender * actual,
                                   selected.origin[0] + font.text_length(text, fontsize=actual),
                                   selected.origin[1] - font.descender * actual)
                self._check_rect(page, newbox)
                for other in current:
                    if other.index != selected.index and (newbox & fitz.Rect(other.bbox)).get_area() > .5:
                        raise EditError("바꾼 글자가 옆의 본문과 겹칩니다. 크기나 영역 너비를 줄여 주세요.")
            positions = _character_positions(page, selected.index)
            page.add_redact_annot(cut, fill=False, cross_out=False)
            page.apply_redactions(images=0, graphics=0, text=0)
            page = doc.reload_page(page)
            remaining = Counter(s.text for s in spans(page))
            expected = Counter(s.text for s in current if s.index != selected.index)
            if remaining != expected:
                raise EditError("주변 글자가 영향을 받아 수정을 취소했습니다.")
            after_positions = _character_positions(page)
            if len(positions) != len(after_positions) or any(
                old[0] != new[0] or any(abs(a - b) > .02 for a, b in zip(old[1] + old[2], new[1] + new[2]))
                for old, new in zip(positions, after_positions)
            ):
                raise EditError("주변 글자의 위치·간격이 달라져 수정을 취소했습니다. 이 페이지는 텍스트 추가를 이용해 주세요.")
            if deleting:
                for item in managed:
                    placed.insert(page, item, system_font() if item["kind"] == "text" else None)
                return {"deleted": True, "substituted": False, "font": selected.font, "size": selected.size}
            resource = "PLFont" + str(doc.xref_length())
            page.insert_font(fontname=resource, fontbuffer=font.buffer)
            page.insert_text(selected.origin, text, fontsize=actual, fontname=resource,
                             color=rgb(selected.color) if color is None else color)
            if text not in doc.reload_page(page).get_text():
                raise EditError("새 글자의 문자 매핑을 검증하지 못해 수정을 취소했습니다.")
            page = doc[number]
            for item in managed:
                placed.insert(page, item, system_font() if item["kind"] == "text" else None)
            return {"substituted": substituted, "font": font.name, "size": actual}

        return self._edit(operation)

    def add_text(self, number, rect, text, size=14, color=(.12, .16, .21)):
        if not text.strip():
            raise EditError("추가할 내용을 입력해 주세요.")

        def operation(doc):
            page = doc[number]
            box = fitz.Rect(rect)
            self._check_rect(page, box)
            font, _ = self._font(doc, page, None, text)
            return placed.insert(page, dict(kind="text", rect=list(box), text=text, size=size, color=color), font)

        return self._edit(operation)

    def add_signature(self, number, rect, image: bytes):
        def operation(doc):
            page = doc[number]
            box = fitz.Rect(rect)
            self._check_rect(page, box)
            return placed.insert(page, dict(kind="signature", rect=list(box), image=base64.b64encode(image).decode("ascii")))
        return self._edit(operation)

    def preview_text(self, number, rect, text, size, color, scale, selected=None):
        """현재 페이지만 복제해 실제 저장과 같은 편집 경로로 렌더링한다."""
        preview = PdfDocument()
        preview.doc = fitz.open()
        preview.editable = self.editable
        try:
            preview.doc.insert_pdf(self.doc, from_page=number, to_page=number)
            if selected is not None:
                result = preview.replace_text(0, selected, text, size, color, rect.width)
            else:
                preview.add_text(0, rect, text, size, color)
                result = None
            pix = preview.doc[0].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            return pix, result
        finally:
            preview.doc.close()

    @staticmethod
    def _check_rect(page, box):
        bounds = fitz.Rect(0, 0, page.cropbox.width, page.cropbox.height)
        if box.is_empty or box.is_infinite or not all(math.isfinite(v) for v in box) or not bounds.contains(box):
            raise EditError("영역을 페이지 안에 지정해 주세요.")

    def save(self, destination):
        if not self.doc:
            raise EditError("먼저 PDF를 열어 주세요.")
        target = Path(destination)
        # 암호를 임의로 제거하지 않는다. 복호화된 편집본 저장은 별도 정책이 필요하다.
        if self.encrypted or self.signed:
            raise EditError("암호화·전자서명 필드가 있는 PDF의 저장은 현재 지원하지 않습니다.")
        fd, temporary = tempfile.mkstemp(prefix=".paperlight-", suffix=".pdf", dir=target.parent)
        os.close(fd)
        try:
            self.doc.save(temporary, garbage=4, deflate=True, encryption=fitz.PDF_ENCRYPT_NONE)
            with fitz.open(temporary) as check:
                if check.page_count != self.doc.page_count:
                    raise EditError("저장한 PDF의 페이지 수가 일치하지 않습니다.")
                for i in range(check.page_count):
                    if check[i].get_text() != self.doc[i].get_text():
                        raise EditError("저장한 PDF의 텍스트 검증에 실패했습니다.")
            with open(temporary, "r+b") as stream:
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        self.path = target
        self.saved_revision = self.revision
