import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pymupdf as fitz

from paperlight.document import PdfDocument, EditError
from fixtures import make_pdf


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "원본.pdf"
        make_pdf(self.source, subset=True)
        self.original = self.source.read_bytes()
        self.model = PdfDocument()
        self.model.open(self.source)

    def tearDown(self):
        if self.model.doc:
            self.model.doc.close()
        self.temp.cleanup()

    def find(self, text):
        return next(s for s in self.model.page_spans(0) if s.text == text)

    def test_korean_replacement_is_real_and_preserves_neighbors(self):
        original = "담당자: 김하늘"
        span = self.find(original)
        before_drawings = self.model.doc[0].get_drawings()
        result = self.model.replace_text(0, span, "담당자: 이서준", width=180)
        self.assertTrue(result["substituted"])
        target = self.root / "결과.pdf"
        self.model.save(target)
        with fitz.open(target) as saved:
            self.assertIn("담당자: 이서준", saved[0].get_text())
            self.assertNotIn(original, saved[0].get_text())
            self.assertIn("검토 상태: 확인 대기", saved[0].get_text())
            self.assertEqual(len(saved[0].get_drawings()), len(before_drawings))
            self.assertEqual(saved.page_count, 2)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertFalse(self.model.dirty)

    def test_english_font_preserved_and_undo_redo(self):
        s = self.find("Project status: Draft")
        result = self.model.replace_text(0, s, "Project status: Final", width=220)
        self.assertFalse(result["substituted"])
        self.assertTrue(self.model.dirty)
        self.model.undo()
        self.assertIn("Project status: Draft", self.model.doc[0].get_text())
        self.assertFalse(self.model.dirty)
        self.model.redo()
        self.assertIn("Project status: Final", self.model.doc[0].get_text())
        self.assertTrue(self.model.dirty)

    def test_oversize_edit_rolls_back(self):
        text = self.model.doc[0].get_text()
        with self.assertRaises(EditError):
            self.model.replace_text(0, self.find("Project status: Draft"), "Very long " * 50)
        self.assertEqual(text, self.model.doc[0].get_text())
        self.assertFalse(self.model.dirty)

    def test_neighbor_position_change_rolls_back_even_when_text_matches(self):
        before = self.model.doc[0].get_pixmap().samples
        original = fitz.Page.apply_redactions

        def move_neighbor(page, *args, **kwargs):
            result = original(page, *args, **kwargs)
            # Simulate a PDF rewrite moving retained text without changing its value.
            for xref in page.get_contents():
                page.parent.update_stream(xref, b"q 1 0 0 1 2 0 cm\n" + page.parent.xref_stream(xref) + b"\nQ")
            return result

        with patch.object(fitz.Page, "apply_redactions", move_neighbor):
            with self.assertRaisesRegex(EditError, "위치·간격"):
                self.model.replace_text(0, self.find("Project status: Draft"), "Final")
        self.assertEqual(self.model.doc[0].get_pixmap().samples, before)
        self.assertFalse(self.model.dirty)
        self.assertFalse(self.model.can_undo)

    def test_add_korean_multiline_and_failed_box(self):
        self.model.add_text(0, (64, 480, 500, 560), "추가 메모입니다.\n검토 완료.", size=14)
        self.assertIn("추가 메모입니다.", self.model.doc[0].get_text())
        rev = self.model.revision
        with self.assertRaises(EditError):
            self.model.add_text(0, (64, 480, 70, 482), "들어가지 않는 문장", size=14)
        self.assertEqual(self.model.revision, rev)

    def test_signature_and_image_survive_text_edit(self):
        pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 40), False)
        pix.clear_with(80)
        self.model.add_signature(0, (160, 660, 350, 700), pix.tobytes("png"))
        images = len(self.model.doc[0].get_images())
        self.model.replace_text(0, self.find("Project status: Draft"), "Project status: Final", width=220)
        self.assertEqual(len(self.model.doc[0].get_images()), images)
        path = self.root / "서명.pdf"
        self.model.save(path)
        with fitz.open(path) as saved:
            self.assertEqual(len(saved[0].get_images()), images)

    def test_repeat_edits_different_fonts(self):
        self.model.replace_text(0, self.find("Project status: Draft"), "Project status: Final", width=220)
        self.model.replace_text(0, self.find("담당자: 김하늘"), "담당자: 이서준", width=180)
        self.model.replace_text(0, self.find("Project status: Final"), "Project status: Ready", width=220)
        self.assertIn("Project status: Ready", self.model.doc[0].get_text())
        self.assertIn("담당자: 이서준", self.model.doc[0].get_text())

    def test_atomic_save_failure_keeps_destination(self):
        target = self.root / "existing.pdf"
        target.write_bytes(b"keep me")
        with patch("paperlight.document.os.replace", side_effect=PermissionError("locked")):
            with self.assertRaises(PermissionError):
                self.model.save(target)
        self.assertEqual(target.read_bytes(), b"keep me")
        self.assertEqual(list(self.root.glob(".paperlight-*")), [])

    def test_existing_redaction_is_not_applied(self):
        page = self.model.doc[0]
        page.add_redact_annot(fitz.Rect(40, 135, 300, 165))
        with self.assertRaises(EditError):
            self.model.replace_text(0, self.find("Project status: Draft"), "Final", width=220)
        self.assertIn("프로젝트 검토서", self.model.doc[0].get_text())

    def test_link_is_preserved_by_rejection(self):
        s = self.find("Project status: Draft")
        self.model.doc[0].insert_link({"kind": fitz.LINK_URI, "from": fitz.Rect(s.bbox), "uri": "https://example.com"})
        self.model.doc = fitz.open(stream=self.model._bytes(), filetype="pdf")
        with self.assertRaises(EditError):
            self.model.replace_text(0, self.find("Project status: Draft"), "Final", width=220)
        self.assertEqual(len(self.model.doc[0].get_links()), 1)

    def test_encrypted_document_is_read_only(self):
        path = self.root / "암호.pdf"
        self.model.doc.save(path, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="reader")
        with self.assertRaises(EditError):
            self.model.open(path)
        self.model.open(path, "reader")
        with self.assertRaises(EditError):
            self.model.add_text(0, (60, 480, 400, 550), "수정")
        with self.assertRaises(EditError):
            self.model.save(self.root / "unlocked.pdf")

    def test_rotated_page_edit_uses_unrotated_coordinates(self):
        self.model.doc[0].set_rotation(90)
        self.model.replace_text(0, self.find("Project status: Draft"), "Project status: Final", width=220)
        self.assertEqual(self.model.doc[0].rotation, 90)
        self.model.add_text(0, (60, 480, 400, 550), "회전 페이지 메모")
        path = self.root / "회전.pdf"
        self.model.save(path)
        with fitz.open(path) as saved:
            self.assertIn("회전 페이지 메모", saved[0].get_text())

    def test_invalid_pdf_does_not_replace_current_document(self):
        bad = self.root / "broken.pdf"
        bad.write_bytes(b"not a pdf")
        with self.assertRaises(Exception):
            self.model.open(bad)
        self.assertEqual(self.model.doc.page_count, 2)

    def test_invisible_ocr_text_is_not_editable(self):
        self.model.doc[0].insert_text((70, 590), "Hidden OCR", render_mode=3)
        with self.assertRaisesRegex(EditError, "OCR"):
            self.model.replace_text(0, self.find("Hidden OCR"), "Visible", width=150)

    def test_delete_text_preserves_neighbors_and_can_be_undone(self):
        original = "담당자: 김하늘"
        result = self.model.replace_text(0, self.find(original), "")
        self.assertTrue(result["deleted"])
        self.assertNotIn(original, self.model.doc[0].get_text())
        self.assertIn("검토 상태: 확인 대기", self.model.doc[0].get_text())
        path = self.root / "deleted.pdf"
        self.model.save(path)
        with fitz.open(path) as saved:
            self.assertNotIn(original, saved[0].get_text())
        self.model.undo()
        self.assertIn(original, self.model.doc[0].get_text())
        self.assertTrue(self.model.dirty)
        self.model.redo()
        self.assertNotIn(original, self.model.doc[0].get_text())
        self.assertFalse(self.model.dirty)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_scan_can_receive_text_without_changing_image(self):
        pix = self.model.doc[0].get_pixmap(matrix=fitz.Matrix(1, 1))
        scan = fitz.open()
        page = scan.new_page(width=595, height=842)
        page.insert_image(page.rect, stream=pix.tobytes("png"))
        path = self.root / "scan.pdf"
        scan.save(path)
        scan.close()
        self.model.open(path)
        self.assertEqual(self.model.page_spans(0), [])
        before = self.model.doc.extract_image(self.model.doc[0].get_images()[0][0])["image"]
        self.model.add_text(0, (64, 480, 500, 550), "스캔본 위 메모")
        self.model.save(self.root / "scan-edited.pdf")
        after = self.model.doc.extract_image(self.model.doc[0].get_images()[0][0])["image"]
        self.assertEqual(before, after)
        self.assertIn("스캔본 위 메모", self.model.doc[0].get_text())


if __name__ == "__main__":
    unittest.main()
