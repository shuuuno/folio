import tempfile
import unittest
from pathlib import Path
import pymupdf as fitz

from fixtures import make_pdf
from paperlight.document import PdfDocument, EditError


class ObjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root / "원본.pdf"
        make_pdf(self.path)
        self.model = PdfDocument()
        self.model.open(self.path)
        self.original = self.model.doc[0].get_pixmap().samples
        with fitz.open() as ink:
            page = ink.new_page(width=100, height=40)
            page.draw_line((5, 30), (90, 10), color=(.1, .2, .3), width=2)
            self.image = page.get_pixmap(alpha=True).tobytes("png")

    def tearDown(self):
        self.model.doc.close()
        self.temp.cleanup()

    def test_text_move_resize_content_reopen_undo_delete(self):
        m = self.model
        oid = m.add_text(0, (64, 480, 400, 540), "첫 줄\n둘째 줄", 14)
        target = self.root / "편집.pdf"
        m.save(target)
        m.open(target)
        self.assertEqual(m.page_objects(0)[0]["id"], oid)
        m.update_object(0, oid, (120, 520, 480, 600), text="옮긴 내용\n다음 줄", size=18)
        self.assertNotIn("첫 줄", m.doc[0].get_text())
        self.assertIn("옮긴 내용", m.doc[0].get_text())
        self.assertEqual(m.page_objects(0)[0]["rect"], [120, 520, 480, 600])
        m.undo()
        self.assertIn("첫 줄", m.doc[0].get_text())
        m.redo()
        m.save(target)
        m.open(target)
        m.delete_object(0, oid)
        self.assertEqual(m.page_objects(0), [])
        self.assertEqual(m.doc[0].get_pixmap().samples, self.original)
        m.save(target)
        with fitz.open(target) as doc:
            self.assertNotIn("옮긴 내용", doc[0].get_text())

    def test_overlapping_signatures_independent_and_no_image_resources_left(self):
        m = self.model
        baseline_images = len(m.doc[0].get_images())
        first = m.add_signature(0, (64, 200, 264, 280), self.image)
        second = m.add_signature(0, (64, 200, 264, 280), self.image)
        m.delete_object(0, first)
        self.assertEqual([o["id"] for o in m.page_objects(0)], [second])
        self.assertNotEqual(m.doc[0].get_pixmap().samples, self.original)
        m.update_object(0, second, (160, 500, 460, 620))
        m.delete_object(0, second)
        self.assertEqual(m.doc[0].get_pixmap().samples, self.original)
        m.save(self.root / "삭제.pdf")
        with fitz.open(self.root / "삭제.pdf") as doc:
            self.assertEqual(len(doc[0].get_images()), baseline_images)

    def test_original_body_edit_preserves_objects_and_reeditability(self):
        m = self.model
        text_id = m.add_text(0, (64, 480, 400, 540), "추가 내용", 14)
        sign_id = m.add_signature(0, (160, 660, 360, 700), self.image)
        selected = next(s for s in m.page_spans(0) if s.text == "담당자: 김하늘")
        m.replace_text(0, selected, "담당자: 이서준", width=200)
        self.assertEqual({o["id"] for o in m.page_objects(0)}, {text_id, sign_id})
        m.update_object(0, text_id, (64, 510, 400, 570))
        m.delete_object(0, sign_id)
        self.assertIn("담당자: 이서준", m.doc[0].get_text())
        self.assertIn("추가 내용", m.doc[0].get_text())

    def test_preview_isolated_and_matches_update(self):
        m = self.model
        oid = m.add_text(0, (64, 480, 400, 540), "추가 내용", 14)
        revision = m.revision
        preview = m.preview_object(0, oid, (100, 500, 450, 560), "미리보기", 16, (0, 0, 0), 1)
        self.assertEqual(m.revision, revision)
        self.assertNotIn("미리보기", m.doc[0].get_text())
        m.update_object(0, oid, (100, 500, 450, 560), "미리보기", 16, (0, 0, 0))
        self.assertEqual(preview.samples, m.doc[0].get_pixmap().samples)

    def test_failed_resize_and_stale_id_keep_object(self):
        m = self.model
        oid = m.add_text(0, (64, 480, 400, 540), "추가 내용", 14)
        before = m.doc[0].get_pixmap().samples
        revision = m.revision
        for rect, key in [((10, 10, 12, 12), oid), ((-10, 10, 100, 100), oid), ((10, 10, 400, 100), "missing")]:
            with self.assertRaises(EditError):
                m.update_object(0, key, rect)
            self.assertEqual(m.revision, revision)
            self.assertEqual(m.doc[0].get_pixmap().samples, before)

    def test_rotated_crop_page_and_stacking_order(self):
        m = self.model
        m.doc[0].set_cropbox(fitz.Rect(20, 20, 575, 800))
        m.doc[0].set_rotation(90)
        first = m.add_text(0, (60, 460, 400, 520), "겹친 글자", 14)
        second = m.add_signature(0, (60, 460, 400, 520), self.image)
        with fitz.open(stream=m._bytes(), filetype="pdf") as baseline:
            before = baseline[0].get_pixmap().samples
        m.update_object(0, first, (60, 460, 400, 520))
        self.assertEqual([o["id"] for o in m.page_objects(0)], [first, second])
        self.assertEqual(m.doc[0].get_pixmap().samples, before)

    def test_deleting_shared_page_copy_keeps_other_page(self):
        m = self.model
        oid = m.add_signature(0, (64, 480, 264, 560), self.image)
        m.doc.fullcopy_page(0)
        last = m.doc.page_count - 1
        kind, resources = m.doc.xref_get_key(m.doc[0].xref, "Resources")
        self.assertEqual(kind, "xref")
        m.doc.xref_set_key(m.doc[last].xref, "Resources", resources)
        other_objects = [o["id"] for o in m.page_objects(last)]
        other_images = len(m.doc[last].get_images())
        with fitz.open(stream=m._bytes(), filetype="pdf") as baseline:
            before = baseline[last].get_pixmap().samples
        m.delete_object(0, oid)
        self.assertEqual(m.doc[last].get_pixmap().samples, before)
        self.assertEqual([o["id"] for o in m.page_objects(last)], other_objects)
        self.assertEqual(len(m.doc[last].get_images()), other_images)
        self.assertEqual(m.page_objects(0), [])


if __name__ == "__main__":
    unittest.main()
