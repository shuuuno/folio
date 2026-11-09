import tempfile
import unittest
from pathlib import Path

import pymupdf as fitz
from PySide6.QtWidgets import QApplication
from PySide6.QtPrintSupport import QPrinter

from paperlight.window import print_pages

app = QApplication.instance() or QApplication([])


class PrintPagesTest(unittest.TestCase):
    def test_prints_each_page_with_matching_orientation(self):
        source = fitz.open()
        source.new_page(width=595, height=842).insert_text((72, 100), "Portrait", fontsize=30)
        source.new_page(width=842, height=595).insert_text((72, 100), "Landscape", fontsize=30)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "printed.pdf"
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(str(output))
            print_pages(source, printer, range(2), dpi=100)
            with fitz.open(output) as printed:
                self.assertEqual(printed.page_count, 2)
                self.assertLess(printed[0].rect.width, printed[0].rect.height)
                self.assertGreater(printed[1].rect.width, printed[1].rect.height)
                for page in printed:
                    samples = page.get_pixmap(dpi=30).samples
                    self.assertTrue(any(samples[i] < 128 for i in range(0, len(samples), 3)))


if __name__ == "__main__":
    unittest.main()
