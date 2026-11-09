import tempfile
import unittest
from pathlib import Path

import pymupdf as fitz
from PySide6.QtWidgets import QApplication

from paperlight.document import PdfDocument, EditError, parse_page_range, extract_pages, merge_pdfs

app = QApplication.instance() or QApplication([])


def make_pdf(*labels):
    doc = fitz.open()
    for label in labels:
        doc.new_page().insert_text((72, 72), label)
    data = doc.tobytes()
    doc.close()
    return data


def texts(path_or_doc):
    doc = fitz.open(path_or_doc) if isinstance(path_or_doc, (str, Path)) else path_or_doc
    return [page.get_text().strip() for page in doc]


class PageRangeTest(unittest.TestCase):
    def test_ranges_keep_order_and_drop_duplicates(self):
        self.assertEqual(parse_page_range("3, 1-2, 2, 5-", 6), [2, 0, 1, 4, 5])
        self.assertEqual(parse_page_range("-2", 6), [0, 1])

    def test_rejects_bad_input(self):
        for text in ("", "0", "7", "2-1", "a"):
            with self.assertRaises(EditError):
                parse_page_range(text, 6)


class ExtractMergeTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.dir = Path(self.folder.name)

    def tearDown(self):
        self.folder.cleanup()

    def test_extract_writes_selected_pages_in_order(self):
        out = self.dir / "out.pdf"
        self.assertEqual(extract_pages(make_pdf("A", "B", "C"), "src.pdf", [2, 0], out), 2)
        self.assertEqual(texts(out), ["C", "A"])

    def test_merge_concatenates_in_order(self):
        out = self.dir / "merged.pdf"
        written = merge_pdfs([("one", make_pdf("A", "B")), ("two", make_pdf("C"))], out)
        self.assertEqual(written, 3)
        self.assertEqual(texts(out), ["A", "B", "C"])

    def test_merge_refuses_encrypted_source(self):
        doc = fitz.open(stream=make_pdf("X"), filetype="pdf")
        locked = doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="o", user_pw="u")
        with self.assertRaises(EditError):
            merge_pdfs([("a", make_pdf("A")), ("locked", locked)], self.dir / "m.pdf")
        self.assertFalse((self.dir / "m.pdf").exists())


class MovePageTest(unittest.TestCase):
    def test_move_and_undo(self):
        model = PdfDocument()
        model.open_bytes(make_pdf("A", "B", "C", "D"), "x.pdf")
        model.move_page(0, 2)
        self.assertEqual(texts(model.doc), ["B", "C", "A", "D"])
        model.move_page(3, 0)
        self.assertEqual(texts(model.doc), ["D", "B", "C", "A"])
        model.undo()
        self.assertEqual(texts(model.doc), ["B", "C", "A", "D"])
        model.undo()
        self.assertEqual(texts(model.doc), ["A", "B", "C", "D"])

    def test_window_drop_signal_moves_page(self):
        from paperlight.window import MainWindow
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "doc.pdf"
            path.write_bytes(make_pdf("A", "B", "C"))
            window = MainWindow()
            window.open_file(str(path))
            window.thumbnails.move_requested.emit(2, 0)
            self.assertEqual(texts(window.model.doc), ["C", "A", "B"])
            self.assertEqual(window.page_number, 0)
            self.assertTrue(window.model.dirty)
            window.model.saved_revision = window.model.revision
            window.close()


class DeleteRotateTest(unittest.TestCase):
    def test_delete_rotate_and_undo(self):
        model = PdfDocument()
        model.open_bytes(make_pdf("A", "B", "C"), "x.pdf")
        model.rotate_pages([0, 2], 90)
        model.rotate_pages([0], -90)
        self.assertEqual([p.rotation for p in model.doc], [0, 0, 90])
        model.delete_pages([1])
        self.assertEqual(texts(model.doc), ["A", "C"])
        with self.assertRaises(EditError):
            model.delete_pages([0, 1])
        model.undo()
        self.assertEqual(texts(model.doc), ["A", "B", "C"])

    def test_window_delete_last_page_then_undo(self):
        from paperlight.window import MainWindow
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "doc.pdf"
            path.write_bytes(make_pdf("A", "B", "C"))
            window = MainWindow()
            window.open_file(str(path))
            window.go_page(2)
            self.assertTrue(window.delete_pages([2]))
            self.assertEqual((window.thumbnails.count(), window.page_number, window.page_input.maximum()), (2, 1, 2))
            window.undo()
            self.assertEqual((window.thumbnails.count(), window.page_number), (3, 1))
            self.assertEqual(texts(window.model.doc), ["A", "B", "C"])
            self.assertTrue(window.rotate_pages([1], 180))
            self.assertEqual(window.model.doc[1].rotation, 180)
            window.model.saved_revision = window.model.revision
            window.close()


class DuplicateTest(unittest.TestCase):
    def test_duplicate_inserts_copies_after_each_page(self):
        model = PdfDocument()
        model.open_bytes(make_pdf("A", "B", "C"), "x.pdf")
        model.duplicate_pages([2, 0])
        self.assertEqual(texts(model.doc), ["A", "A", "B", "C", "C"])
        model.undo()
        self.assertEqual(texts(model.doc), ["A", "B", "C"])

    def test_copy_keeps_rotation(self):
        model = PdfDocument()
        model.open_bytes(make_pdf("A", "B"), "x.pdf")
        model.rotate_pages([1], 90)
        model.duplicate_pages([1])
        self.assertEqual([p.rotation for p in model.doc], [0, 90, 90])

    def test_placed_objects_stay_independent_and_editable(self):
        model = PdfDocument()
        model.open_bytes(make_pdf("Base"), "x.pdf")
        model.add_text(0, (72, 200, 300, 240), "Hello")
        [original] = model.page_objects(0)
        model.duplicate_pages([0])
        [copy] = model.page_objects(1)
        self.assertEqual(copy["id"], original["id"])
        self.assertEqual(copy["text"], "Hello")
        model.update_object(0, original["id"], original["rect"], text="Changed")
        self.assertEqual(model.page_objects(0)[0]["text"], "Changed")
        self.assertEqual(model.page_objects(1)[0]["text"], "Hello")
        self.assertIn("Hello", model.doc[1].get_text())
        model.delete_object(1, copy["id"])
        self.assertEqual(model.page_objects(1), [])
        self.assertEqual(model.page_objects(0)[0]["text"], "Changed")
        self.assertIn("Changed", model.doc[0].get_text())
        self.assertNotIn("Hello", model.doc[1].get_text())

    def test_saved_copy_reopens_with_editable_objects(self):
        model = PdfDocument()
        model.open_bytes(make_pdf("Base"), "x.pdf")
        model.add_text(0, (72, 200, 300, 240), "Hello")
        model.duplicate_pages([0])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "saved.pdf"
            model.save(path)
            reopened = PdfDocument()
            reopened.open(path)
            self.assertEqual(reopened.doc.page_count, 2)
            self.assertEqual([len(reopened.page_objects(n)) for n in range(2)], [1, 1])
            reopened.doc.close()
            model.doc.close()

    def test_window_duplicate_moves_to_copy(self):
        from paperlight.window import MainWindow
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "doc.pdf"
            path.write_bytes(make_pdf("A", "B"))
            window = MainWindow()
            window.open_file(str(path))
            self.assertTrue(window.duplicate_pages([0]))
            self.assertEqual(texts(window.model.doc), ["A", "A", "B"])
            self.assertEqual((window.thumbnails.count(), window.page_number, window.page_input.maximum()), (3, 1, 3))
            window.undo()
            self.assertEqual((window.thumbnails.count(), window.page_number), (2, 1))
            window.model.saved_revision = window.model.revision
            window.close()


if __name__ == "__main__":
    unittest.main()
