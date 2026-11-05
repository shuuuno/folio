"""Offline checks against public PDFs listed in research/corpus-sources.json.

Run from the repository root. Source PDFs are never modified or bundled.
"""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter
import argparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pymupdf as fitz
from paperlight.document import PdfDocument, EditError, spans

parser = argparse.ArgumentParser()
parser.add_argument("--output", default="evidence/compatibility")
OUT = ROOT / parser.parse_args().output
OUT.mkdir(parents=True, exist_ok=True)


def digest(data):
    return sha256(data).hexdigest()


def render(page, scale=.5):
    return page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)


def image_hashes(doc, page):
    return sorted(digest(doc.extract_image(item[0])["image"]) for item in page.get_images())


def outside_equal(a, b, area):
    """Exact RGB comparison outside the edit rectangle at 1 PDF point / pixel."""
    assert (a.width, a.height, a.n) == (b.width, b.height, b.n)
    box = fitz.Rect(area) + (-3, -3, 3, 3)
    x0, y0, x1, y1 = box.irect
    x0, x1 = max(0, x0), min(a.width, x1)
    aa, bb = a.samples, b.samples
    for y in range(a.height):
        row = y * a.stride
        end = row + a.width * a.n
        if y < y0 or y >= y1:
            assert aa[row:end] == bb[row:end], f"Unexpected pixel change at row {y}"
        else:
            assert aa[row:row+x0*a.n] == bb[row:row+x0*a.n], f"Left pixels changed at {y}"
            assert aa[row+x1*a.n:end] == bb[row+x1*a.n:end], f"Right pixels changed at {y}"


def roundtrip(source):
    path = ROOT / "research/corpus" / source["file"]
    original = path.read_bytes()
    assert digest(original) == source["sha256"], f"Corpus changed: {path.name}"
    model = PdfDocument()
    start = perf_counter()
    model.open(path)
    opened = perf_counter() - start
    start = perf_counter()
    fingerprints = [digest(render(p).samples) for p in model.doc]
    rendered = perf_counter() - start
    toc = model.doc.get_toc()
    links = [p.get_links() for p in model.doc]
    target = OUT / (path.stem + "-roundtrip.pdf")
    start = perf_counter()
    model.save(target)
    saved = perf_counter() - start
    with fitz.open(target) as check:
        assert len(check) == source["pages"]
        assert [digest(render(p).samples) for p in check] == fingerprints
        assert check.get_toc() == toc
        # Garbage collection can renumber xrefs, but link behavior must persist.
        clean = lambda values: [[{k: v for k, v in link.items() if k != "xref"} for link in page] for page in values]
        assert clean([p.get_links() for p in check]) == clean(links)
    assert path.read_bytes() == original
    model.doc.close()
    return dict(file=path.name, pages=source["pages"], all_page_pixels_equal=True,
                text_equal=True, bookmarks_equal=True, links_equal=True, source_unchanged=True,
                seconds=dict(open=round(opened, 3), render_all_half_scale=round(rendered, 3), save=round(saved, 3)))


def replace_case(name, filename, page_number, span_index, replacement):
    path = ROOT / "research/corpus" / filename
    model = PdfDocument()
    model.open(path)
    page = model.doc[page_number]
    before = render(page, 1)
    selected = spans(page)[span_index]
    neighbors = Counter(s.text for s in spans(page) if s.index != span_index)
    images = image_hashes(model.doc, page)
    drawings = len(page.get_drawings())
    before.save(OUT / (name + "-before.png"))
    preview, _ = model.preview_text(page_number, fitz.Rect(selected.bbox), replacement,
                                   selected.size, None, 1, selected)
    assert not model.dirty
    result = model.replace_text(page_number, selected, replacement)
    changed = model.doc[page_number]
    after = render(changed, 1)
    assert preview.samples == after.samples
    current = spans(changed)
    new_span = next(s for s in current if s.text == replacement)
    assert Counter(s.text for s in current if s != new_span) == neighbors
    assert len(changed.get_drawings()) == drawings
    assert image_hashes(model.doc, changed) == images
    outside_equal(before, after, fitz.Rect(selected.bbox) | fitz.Rect(new_span.bbox))
    after.save(OUT / (name + "-after.png"))
    model.save(OUT / (name + "-edited.pdf"))
    with fitz.open(OUT / (name + "-edited.pdf")) as saved:
        assert render(saved[page_number], 1).samples == after.samples
        assert replacement in saved[page_number].get_text()
    model.undo()
    assert render(model.doc[page_number], 1).samples == before.samples
    model.redo()
    assert render(model.doc[page_number], 1).samples == after.samples
    model.doc.close()
    return dict(case=name, file=filename, page=page_number+1, original_font=selected.font,
                result=result, preview_matches=True, neighbors_preserved=True, outside_pixels_equal=True,
                images_preserved=True, drawing_count=drawings, save_reopen=True, undo_redo=True)


def overlay_case(name, filename, page_number, rect):
    model = PdfDocument()
    model.open(ROOT / "research/corpus" / filename)
    page = model.doc[page_number]
    before = render(page, 1)
    old_text = Counter(s.text for s in spans(page))
    images = image_hashes(model.doc, page)
    original_image_count = len(images)
    drawing_count = len(page.get_drawings())
    before.save(OUT / (name + "-before.png"))
    text_id = model.add_text(page_number, rect, "호환성 검증용 메모", size=10)
    # A transparent test signature, generated locally with PDF drawing primitives.
    with fitz.open() as ink:
        sheet = ink.new_page(width=120, height=30)
        shape = sheet.new_shape()
        shape.draw_polyline([(3, 20), (20, 3), (28, 24), (50, 6), (70, 18), (113, 8)])
        shape.finish(color=(.08, .2, .3), width=2)
        shape.commit()
        signature = sheet.get_pixmap(alpha=True).tobytes("png")
    signature_box = fitz.Rect(rect.x0, rect.y1+2, rect.x0+100, rect.y1+27)
    signature_id = model.add_signature(page_number, signature_box, signature)
    rect += (10, 5, 10, 5)
    signature_box += (10, 5, 10, 5)
    model.update_object(page_number, text_id, rect)
    model.update_object(page_number, signature_id, signature_box)
    after = render(model.doc[page_number], 1)
    assert not (Counter(images) - Counter(image_hashes(model.doc, model.doc[page_number])))
    assert not (old_text - Counter(s.text for s in spans(model.doc[page_number])))
    assert len(model.doc[page_number].get_drawings()) == drawing_count
    outside_equal(before, after, rect | signature_box)
    after.save(OUT / (name + "-after.png"))
    model.save(OUT / (name + "-edited.pdf"))
    with fitz.open(OUT / (name + "-edited.pdf")) as saved:
        assert render(saved[page_number], 1).samples == after.samples
        assert "호환성 검증용 메모" in saved[page_number].get_text()
    model.open(OUT / (name + "-edited.pdf"))
    assert {o["id"] for o in model.page_objects(page_number)} == {text_id, signature_id}
    model.delete_object(page_number, text_id)
    model.delete_object(page_number, signature_id)
    assert render(model.doc[page_number], 1).samples == before.samples
    model.undo()
    model.undo()
    assert render(model.doc[page_number], 1).samples == after.samples
    model.doc.close()
    return dict(case=name, file=filename, page=page_number+1, original_text_spans=sum(old_text.values()),
                original_images=original_image_count, source_images_preserved=True, original_text_preserved=True,
                outside_pixels_equal=True, save_reopen=True, text_added=True, signature_added=True,
                objects_moved=True, objects_reopened=True, deletion_restores_original=True, undo_restores_objects=True)


def unsafe_table_case():
    model = PdfDocument()
    model.open(ROOT / "research/corpus/korean-curriculum.pdf")
    before = render(model.doc[33], 1)
    selected = model.page_spans(33)[5]
    for preview in (True, False):
        try:
            if preview:
                model.preview_text(33, fitz.Rect(selected.bbox), "확인", selected.size, None, 1, selected)
            else:
                model.replace_text(33, selected, "확인")
        except EditError as exc:
            assert "위치·간격" in str(exc)
        else:
            raise AssertionError("Unsafe table edit should have been rejected")
        assert not model.dirty and not model.can_undo
        assert render(model.doc[33], 1).samples == before.samples
    model.doc.close()
    return dict(case="korean-table", file="korean-curriculum.pdf", page=34,
                outcome="rejected_safely", reason="neighbor character positions changed in PDF engine",
                preview_rejected=True, edit_rejected=True, original_pixels_unchanged=True, history_unchanged=True)


def main():
    sources = json.loads((ROOT / "research/corpus-sources.json").read_text(encoding="utf-8"))
    report = dict(passed=False, roundtrips=[], edits=[])
    try:
        for source in sources:
            report["roundtrips"].append(roundtrip(source))
            print(source["file"], "roundtrip passed", flush=True)
        for args in [
            ("korean-prose", "korean-curriculum.pdf", 4, 10, "검토했습니다."),
            ("bilingual-heading", "hog-manual-bilingual.pdf", 96, 6, "Compatibility Test Template"),
        ]:
            report["edits"].append(replace_case(*args))
            print(args[0], "replacement passed", flush=True)
        report["edits"].append(unsafe_table_case())
        report["edits"].append(overlay_case("contract-overlay", "hog-manual-bilingual.pdf", 96,
                                          fitz.Rect(130, 663, 350, 681)))
        report["edits"].append(overlay_case("scan-overlay", "archives-declaration.pdf", 0,
                                          fitz.Rect(35, 35, 250, 62)))
        report["passed"] = True
    finally:
        (OUT / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("All compatibility checks passed.")


if __name__ == "__main__":
    main()
