from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pymupdf as fitz
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTCollection, TTFont

from paperlight import fonts
from paperlight.document import PdfDocument, EditError


def make_font(path, fs_type=0, family="Folio Test"):
    """테스트 소유의 간단한 윤곽과 한글 문자 매핑. 외부 글꼴을 복제하지 않는다."""
    builder = FontBuilder(1000, isTTF=True)
    mapping = {32: "space", 65: "A", 66: "B", 0xD55C: "uniD55C", 0xAE00: "uniAE00"}
    order = [".notdef"] + list(mapping.values())
    builder.setupGlyphOrder(order)
    builder.setupCharacterMap(mapping)
    glyphs = {}
    for name in order:
        pen = TTGlyphPen(None)
        if name != "space":
            pen.moveTo((60, 0))
            pen.lineTo((540, 0))
            pen.lineTo((540, 700))
            pen.lineTo((60, 700))
            pen.closePath()
        glyphs[name] = pen.glyph()
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics({name: (600, 0) for name in order})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable(dict(familyName=family, styleName="Regular",
                               uniqueFontIdentifier=family.replace(" ", "") + "-Regular", fullName=family + " Regular",
                               psName=family.replace(" ", "") + "-Regular"))
    builder.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200, fsType=fs_type)
    builder.setupPost()
    builder.setupMaxp()
    builder.save(path)


class FontTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.font_path = self.root / "editable.ttf"
        make_font(self.font_path, 0x0108)
        fonts.installed_fonts.cache_clear()
        self.paths = patch.object(fonts, "_font_paths", return_value=[self.font_path])
        self.paths.start()
        self.key = fonts.font_key(self.font_path)
        source = self.root / "source.pdf"
        with fitz.open() as doc:
            page = doc.new_page()
            page.insert_text((60, 60), "Original", fontname="helv")
            doc.save(source)
        self.model = PdfDocument()
        self.model.open(source)

    def tearDown(self):
        self.model.doc.close()
        self.paths.stop()
        fonts.installed_fonts.cache_clear()
        self.temp.cleanup()

    def test_embedding_policy_fails_closed(self):
        for value in (0, 8, 0x0100, 0x0108):
            self.assertTrue(fonts.embedding_allowed(value), hex(value))
        for value in (1, 2, 4, 6, 12, 0x0102, 0x0200, 0x0208, 0x8000):
            self.assertFalse(fonts.embedding_allowed(value), hex(value))

    def test_inventory_excludes_restricted_preview_bitmap_and_missing_os2(self):
        candidates = []
        for value in (0, 2, 4, 8, 0x0100, 0x0200):
            path = self.root / f"font-{value}.ttf"
            make_font(path, value)
            candidates.append(path)
        missing = self.root / "missing-os2.ttf"
        make_font(missing)
        with TTFont(missing) as font:
            del font["OS/2"]
            font.save(missing)
        broken = self.root / "broken.ttf"
        broken.write_bytes(b"not a font")
        with patch.object(fonts, "_font_paths", return_value=candidates + [missing, broken]):
            actual = {choice.path for choice in fonts.installed_fonts()}
        self.assertEqual(actual, {candidates[0], candidates[3], candidates[4]})

    def test_permissions_are_rechecked_after_inventory(self):
        self.assertEqual(len(fonts.installed_fonts()), 1)
        make_font(self.font_path, 2)
        with self.assertRaisesRegex(ValueError, "내장"):
            fonts.font_bytes(self.key)
        with self.assertRaises(EditError):
            self.model.add_text(0, (60, 100, 300, 150), "AB", font_id=self.key)
        self.assertFalse(self.model.dirty)

    def test_collection_faces_are_filtered_and_extracted(self):
        restricted = self.root / "restricted.ttf"
        make_font(restricted, 2)
        collection = TTCollection()
        collection.fonts = [TTFont(restricted), TTFont(self.font_path)]
        path = self.root / "collection.ttc"
        try:
            collection.save(path)
        finally:
            collection.close()
        with patch.object(fonts, "_font_paths", return_value=[path]):
            choices = fonts.installed_fonts()
            self.assertEqual([choice.index for choice in choices], [1])
            raw = fonts.font_bytes(choices[0].key)
        self.assertNotEqual(raw[:4], b"ttcf")
        with TTFont(BytesIO(raw)) as font:
            self.assertEqual(font["OS/2"].fsType, 0x0108)
            self.assertEqual(len(font.getGlyphOrder()), 6)

    def test_chosen_font_is_embedded_full_and_survives_reopen_and_reedit(self):
        oid = self.model.add_text(0, (60, 100, 350, 170), "한글 AB", font_id=self.key)
        target = self.root / "result.pdf"
        self.model.save(target)
        self.model.open(target)
        item = self.model.page_objects(0)[0]
        self.assertIn("Folio", item["font_name"])
        resource = next(f for f in self.model.doc[0].get_fonts() if f[4] == item["resource"][1])
        with TTFont(BytesIO(self.model.doc.extract_font(resource[0])[3])) as embedded:
            self.assertEqual(embedded["OS/2"].fsType, 0x0108)
            self.assertEqual(len(embedded.getGlyphOrder()), 6)
        self.font_path.unlink()
        self.model.update_object(0, oid, (60, 120, 350, 190), text="한글 BA")
        self.assertIn("Folio", self.model.page_objects(0)[0]["font_name"])
        self.assertIn("한글 BA", self.model.doc[0].get_text())
        self.model.undo()
        self.assertIn("한글 AB", self.model.doc[0].get_text())

    def test_body_edit_preserves_placed_font_and_explicit_replacement_embeds_choice(self):
        self.model.add_text(0, (60, 100, 350, 170), "한글 AB", font_id=self.key)
        span = next(s for s in self.model.page_spans(0) if s.text == "Original")
        self.model.replace_text(0, span, "Changed", width=200)
        self.assertIn("Folio", self.model.page_objects(0)[0]["font_name"])
        span = next(s for s in self.model.page_spans(0) if s.text == "Changed")
        result = self.model.replace_text(0, span, "AB", width=200, font_id=self.key)
        self.assertIn("Folio", result["font"])
        self.assertFalse(result["substituted"])
        self.assertIn("한글 AB", self.model.doc[0].get_text())

    def test_object_font_change_uses_same_preview_path_and_can_be_undone(self):
        other = self.root / "other.ttf"
        make_font(other, family="Folio Second")
        with patch.object(fonts, "_font_paths", return_value=[self.font_path, other]):
            oid = self.model.add_text(0, (60, 100, 350, 170), "한글 AB", font_id=self.key)
            revision = self.model.revision
            with self.assertRaises(EditError):
                self.model.update_object(0, oid, (60, 100, 350, 170), font_id="")
            self.assertEqual(self.model.revision, revision)
            key = fonts.font_key(other)
            self.model.preview_object(0, oid, (60, 100, 350, 170), "한글 BA", 14, (0, 0, 0), 1, key)
            self.assertEqual(self.model.revision, revision)
            self.assertIn("Folio Test", self.model.page_objects(0)[0]["font_name"])
            self.model.update_object(0, oid, (60, 100, 350, 170), text="한글 BA", font_id=key)
            self.assertIn("Folio Second", self.model.page_objects(0)[0]["font_name"])
            self.model.undo()
            self.assertIn("Folio Test", self.model.page_objects(0)[0]["font_name"])

    def test_missing_glyph_and_roundtrip_failure_leave_document_and_undo_unchanged(self):
        before = (self.model.doc[0].get_text(), self.model.doc[0].get_pixmap().samples, self.model.revision)
        with self.assertRaisesRegex(EditError, "문자"):
            self.model.add_text(0, (60, 100, 350, 170), "없는 글자", font_id=self.key)
        with patch("paperlight.document._font_roundtrips", return_value=False):
            with self.assertRaisesRegex(EditError, "매핑"):
                self.model.add_text(0, (60, 100, 350, 170), "한글", font_id=self.key)
        self.assertEqual((self.model.doc[0].get_text(), self.model.doc[0].get_pixmap().samples, self.model.revision), before)
        self.assertFalse(self.model.can_undo)

    def test_malformed_font_label_in_object_metadata_is_not_trusted(self):
        self.model.add_text(0, (60, 100, 350, 170), "한글 AB", font_id=self.key)
        item = self.model.page_objects(0)[0]
        kind, value = self.model.doc.xref_get_key(item["xref"], "PaperlightObject")
        self.assertEqual(kind, "string")
        data = json.loads(value)
        data["font_name"] = ["잘못된 형식"]
        self.model.doc.xref_set_key(item["xref"], "PaperlightObject", fitz.get_pdf_str(json.dumps(data)))
        self.assertEqual(self.model.page_objects(0), [])
