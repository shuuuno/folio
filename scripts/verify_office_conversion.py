"""Office 또는 LibreOffice가 설치된 PC에서 합성 문서의 양방향 변환을 검증한다."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pymupdf as fitz
from docx import Document
from pptx import Presentation
from pptx.util import Inches
from paperlight.conversion import convert

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=ROOT / "evidence" / "office-conversion")
args = parser.parse_args()
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
word = Document()
word.add_heading("Paperlight Word conversion", 0)
word.add_paragraph("한글 문서 변환 검증")
word.save(output / "word.docx")
slides = Presentation()
slide = slides.slides.add_slide(slides.slide_layouts[6])
slide.shapes.add_textbox(Inches(1), Inches(1), Inches(7), Inches(2)).text = "한글 슬라이드 변환 검증"
slides.save(output / "slides.pptx")
checks = []
for name in ("word.docx", "slides.pptx"):
    source = output / name
    original = source.read_bytes()
    target = convert(dict(sources=[str(source)], destination=str(output), format="pdf"))[0]
    with fitz.open(target) as doc:
        assert "변환검증" in "".join("".join(page.get_text() for page in doc).split())
        doc[0].get_pixmap(dpi=96).save(output / (source.stem + ".png"))
        checks.append(dict(source=name, pages=doc.page_count, korean_text=True))
    assert source.read_bytes() == original
(output / "result.json").write_text(json.dumps(dict(passed=True, checks=checks), indent=2), encoding="utf-8")
print(f"Office 변환 검증 완료: {output}")
