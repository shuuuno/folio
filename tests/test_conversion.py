from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pymupdf as fitz
from PIL import Image
from docx import Document
from pptx import Presentation
from paperlight.conversion import convert, Cancelled, ConversionError
from fixtures import make_pdf


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "문서.pdf"
        make_pdf(self.source, subset=True)
        self.original = self.source.read_bytes()

    def tearDown(self):
        self.assertEqual(self.source.read_bytes(), self.original)
        self.temp.cleanup()

    def request(self, format, **kwargs):
        return dict(sources=[str(self.source)], destination=str(self.root), format=format, **kwargs)

    def test_pdf_png_jpg_pages_and_existing_output_preserved(self):
        for format in ("png", "jpg"):
            result = Path(convert(self.request(format, dpi=96))[0])
            self.assertEqual(len(list(result.iterdir())), 2)
            with Image.open(result / f"0001.{format}") as image:
                self.assertGreater(image.width, 700)
            (result / "keep.txt").write_text("keep")
            second = Path(convert(self.request(format, dpi=96))[0])
            self.assertNotEqual(result, second)
            self.assertEqual((result / "keep.txt").read_text(), "keep")

    def test_images_to_pdf(self):
        for format in ("png", "jpg"):
            source = self.root / ("그림." + format)
            Image.new("RGB", (320, 180), "#cc3311").save(source)
            result = convert(dict(sources=[str(source)], destination=str(self.root), format="pdf"))
            with fitz.open(result[0]) as doc:
                self.assertEqual(doc.page_count, 1)
                self.assertAlmostEqual(doc[0].rect.width / doc[0].rect.height, 320/180)
                self.assertTrue(doc[0].get_images())

    def test_editable_word_and_pptx_contain_real_korean_text(self):
        word = convert(self.request("docx"))[0]
        text = "\n".join(p.text for p in Document(word).paragraphs)
        self.assertIn("담당자: 김하늘", text)
        slides = Presentation(convert(self.request("pptx", dpi=96))[0])
        self.assertEqual(len(slides.slides), 2)
        self.assertIn("담당자: 김하늘", "\n".join(s.text for s in slides.slides[0].shapes if s.has_text_frame))
        self.assertTrue(any(s.shape_type == 13 for s in slides.slides[0].shapes))

    def test_appearance_outputs_are_images_and_rotated_page_is_preserved(self):
        word = Document(convert(self.request("docx", mode="appearance", dpi=96))[0])
        self.assertEqual(len(word.inline_shapes), 2)
        slides = Presentation(convert(self.request("pptx", mode="appearance", dpi=96))[0])
        self.assertTrue(all(len(slide.shapes) == 1 for slide in slides.slides))
        rotated = self.root / "회전.pdf"
        with fitz.open(self.source) as doc:
            doc[0].set_rotation(90)
            doc.save(rotated)
        result = convert(dict(sources=[str(rotated)], destination=str(self.root), format="pptx", dpi=96))
        self.assertEqual(len(Presentation(result[0]).slides[0].shapes), 1)

    def test_failed_batch_and_cancellation_publish_nothing(self):
        bad = self.root / "손상.pdf"
        bad.write_bytes(b"invalid")
        with self.assertRaises(Exception):
            convert(dict(sources=[str(self.source), str(bad)], destination=str(self.root), format="docx"))
        self.assertFalse(list(self.root.glob("*.docx")))
        cancel = self.root / "cancel"
        cancel.touch()
        with self.assertRaises(Cancelled):
            convert(self.request("png", cancel_file=str(cancel)))
        self.assertFalse(list(self.root.glob(".paperlight-convert-*")))

    def test_restricted_pdf_is_rejected(self):
        locked = self.root / "복사제한.pdf"
        with fitz.open(self.source) as doc:
            doc.save(locked, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="", permissions=fitz.PDF_PERM_PRINT)
        with self.assertRaises(ConversionError):
            convert(dict(sources=[str(locked)], destination=str(self.root), format="docx"))

    def test_owner_encrypted_pdf_without_open_password_is_rejected(self):
        locked = self.root / "암호없이열리는암호화.pdf"
        with fitz.open(self.source) as doc:
            doc.save(locked, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="", permissions=fitz.PDF_PERM_COPY)
        with self.assertRaises(ConversionError):
            convert(dict(sources=[str(locked)], destination=str(self.root), format="png"))


if __name__ == "__main__":
    unittest.main()
