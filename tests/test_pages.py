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


if __name__ == "__main__":
    unittest.main()
