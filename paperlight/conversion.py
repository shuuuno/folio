"""오프라인 파일 변환. 결과 전체를 만든 다음 새 경로로만 게시한다."""
from io import BytesIO
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import pymupdf as fitz


class ConversionError(Exception):
    pass


class Cancelled(Exception):
    pass


def check_cancel(cancel_file):
    if cancel_file and Path(cancel_file).exists():
        raise Cancelled()


def open_pdf(path):
    doc = fitz.open(path)
    if doc.needs_pass or doc.is_encrypted or (doc.metadata or {}).get("encryption") or not (doc.permissions & fitz.PDF_PERM_COPY):
        doc.close()
        raise ConversionError("암호화 또는 복사 제한 PDF는 변환하지 않습니다.")
    if not doc.page_count:
        doc.close()
        raise ConversionError("변환할 페이지가 없습니다.")
    return doc


def render(page, dpi):
    if page.rect.width * page.rect.height * (dpi / 72) ** 2 > 40_000_000:
        raise ConversionError("페이지가 너무 큽니다. 이미지 해상도를 낮춰 주세요.")
    return page.get_pixmap(dpi=dpi, alpha=False)


def image_to_pdf(source, target):
    from PIL import Image, ImageOps
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        image.load()
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA" if "transparency" in image.info else "RGB")
        content = BytesIO()
        image.save(content, format="PNG")
        width, height = image.size
    scale = min(.75, 14400 / max(width, height))
    with fitz.open() as doc:
        page = doc.new_page(width=max(3, width * scale), height=max(3, height * scale))
        page.insert_image(page.rect, stream=content.getvalue())
        doc.save(target, garbage=4, deflate=True)


def libreoffice_path():
    for path in (shutil.which("soffice"),
                 r"C:\Program Files\LibreOffice\program\soffice.exe",
                 r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"):
        if path and Path(path).is_file():
            return Path(path)
    return None


def office_to_pdf(source, target):
    libre = libreoffice_path()
    if libre:
        with tempfile.TemporaryDirectory(prefix="paperlight-office-") as name:
            base = Path(name)
            profile = base / "profile"
            profile.mkdir()
            # 다른 LibreOffice 창과 분리하고 문서 매크로를 실행하지 않는다.
            (profile / "user").mkdir()
            (profile / "user/registrymodifications.xcu").write_text(
                '<?xml version="1.0" encoding="UTF-8"?><oor:items xmlns:oor="http://openoffice.org/2001/registry">'
                '<item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop></item></oor:items>', encoding="utf-8")
            subprocess.run([str(libre), f"-env:UserInstallation={profile.as_uri()}", "--headless",
                            "--convert-to", "pdf", "--outdir", str(base), str(source)],
                           check=True, timeout=180, capture_output=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            output = base / (source.stem + ".pdf")
            if not output.is_file():
                raise ConversionError("LibreOffice가 PDF를 만들지 못했습니다. 암호·손상·지원 형식을 확인하세요.")
            shutil.copy2(output, target)
        return
    import pythoncom
    from win32com.client import DispatchEx, GetActiveObject
    pythoncom.CoInitialize()
    app = document = None
    shared = False
    old_security = old_alerts = None
    try:
        if source.suffix.lower() in (".doc", ".docx"):
            app = DispatchEx("Word.Application")
            app.Visible = False
            app.DisplayAlerts = 0
            app.AutomationSecurity = 3
            app.Options.UpdateLinksAtOpen = False
            document = app.Documents.Open(str(source), ConfirmConversions=False, ReadOnly=True,
                                          AddToRecentFiles=False, Visible=False, NoEncodingDialog=True,
                                          PasswordDocument="Paperlight-do-not-prompt",
                                          WritePasswordDocument="Paperlight-do-not-prompt")
            document.ExportAsFixedFormat(str(target), 17, OpenAfterExport=False)
        else:
            try:
                app = GetActiveObject("PowerPoint.Application")
                shared = True
            except pythoncom.com_error:
                app = DispatchEx("PowerPoint.Application")
            old_security, old_alerts = app.AutomationSecurity, app.DisplayAlerts
            app.AutomationSecurity = 3
            app.DisplayAlerts = 1
            document = app.Presentations.Open(str(source), ReadOnly=True, Untitled=False, WithWindow=False)
            document.SaveAs(str(target), 32)
    except Exception as exc:
        raise ConversionError("Word/PPT → PDF에는 Microsoft Office 또는 LibreOffice가 필요합니다. "
                              "앱 설치·활성화와 문서 암호/손상 여부를 확인하세요.\n" + str(exc)) from exc
    finally:
        try:
            if document is not None:
                document.Close(False) if source.suffix.lower() in (".doc", ".docx") else document.Close()
        finally:
            if app is not None:
                if old_security is not None:
                    app.AutomationSecurity, app.DisplayAlerts = old_security, old_alerts
                if not shared:
                    count = app.Documents.Count if source.suffix.lower() in (".doc", ".docx") else app.Presentations.Count
                    if count == 0:
                        app.Quit()
            pythoncom.CoUninitialize()


def pdf_to_docx(doc, target, mode, dpi, cancel_file):
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.section import WD_SECTION_START
    from docx.oxml.ns import qn
    result = Document()
    normal = result.styles["Normal"]
    normal.font.name = "맑은 고딕"
    normal._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "맑은 고딕")
    normal.paragraph_format.space_after = Pt(0)
    for index, page in enumerate(doc):
        check_cancel(cancel_file)
        section = result.sections[0] if index == 0 else result.add_section(WD_SECTION_START.NEW_PAGE)
        section.page_width, section.page_height = Pt(page.rect.width), Pt(page.rect.height)
        margin = 12 if mode == "appearance" else 28
        section.left_margin = section.right_margin = section.top_margin = section.bottom_margin = Pt(margin)
        if mode == "appearance" or not page.get_text().strip():
            # 페이지 이미지 모드는 글자가 편집 가능하다고 표시하지 않는다.
            pix = render(page, dpi)
            scale = min((page.rect.width - margin * 2) / page.rect.width,
                        (page.rect.height - margin * 2 - 16) / page.rect.height)
            result.add_picture(BytesIO(pix.tobytes("png")), width=Pt(page.rect.width * scale), height=Pt(page.rect.height * scale))
            continue
        for block in page.get_text("dict", sort=True)["blocks"]:
            if block["type"] == 1:
                picture = fitz.Pixmap(block["image"])
                if picture.colorspace and picture.colorspace.n > 3:
                    picture = fitz.Pixmap(fitz.csRGB, picture)
                width = min(block["bbox"][2] - block["bbox"][0], page.rect.width - margin * 2)
                result.add_picture(BytesIO(picture.tobytes("png")), width=Pt(max(1, width)))
                continue
            paragraph = result.add_paragraph()
            for line_index, line in enumerate(block.get("lines", [])):
                if line_index:
                    paragraph.add_run().add_break()
                for span in line["spans"]:
                    run = paragraph.add_run(span["text"])
                    run.font.size = Pt(max(1, min(96, span["size"])))
                    run.bold = bool(span["flags"] & 16)
                    run.italic = bool(span["flags"] & 2)
                    run.font.color.rgb = RGBColor.from_string(f'{span["color"]:06X}')
    result.save(target)


def pdf_to_pptx(doc, target, mode, dpi, cancel_file):
    from pptx import Presentation
    from pptx.util import Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import MSO_AUTO_SIZE
    result = Presentation()
    first = doc[0].rect
    # PowerPoint 한 파일의 슬라이드 크기는 공통이며 페이지 비율 차이는 여백으로 보존한다.
    scale = min(1, 4000 / max(first.width, first.height))
    slide_width, slide_height = max(72, first.width * scale), max(72, first.height * scale)
    result.slide_width, result.slide_height = Pt(slide_width), Pt(slide_height)
    for index, page in enumerate(doc):
        check_cancel(cancel_file)
        slide = result.slides.add_slide(result.slide_layouts[6])
        scale = min(slide_width / page.rect.width, slide_height / page.rect.height)
        offset_x, offset_y = (slide_width - page.rect.width * scale) / 2, (slide_height - page.rect.height * scale) / 2
        blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES)["blocks"]
        # 가로 본문만 편집 가능하게 분리. 회전/세로 글자는 배경 그림에 보존한다.
        all_lines = [line for block in blocks for line in block.get("lines", [])]
        lines = all_lines if page.rotation == 0 and all(tuple(line["dir"]) == (1.0, 0.0) for line in all_lines) else []
        background = fitz.open() if mode == "editable" and lines else None
        try:
            if background is not None:
                background.insert_pdf(doc, from_page=index, to_page=index)
                back = background[0]
                for line in lines:
                    back.add_redact_annot(line["bbox"], fill=False)
                back.apply_redactions(images=0, graphics=0, text=0)
                pix = render(back, dpi)
            else:
                pix = render(page, dpi)
            slide.shapes.add_picture(BytesIO(pix.tobytes("png")), Pt(offset_x), Pt(offset_y),
                                     Pt(page.rect.width * scale), Pt(page.rect.height * scale))
        finally:
            if background is not None:
                background.close()
        if mode != "editable":
            continue
        for line in lines:
            x0, y0, x1, y1 = line["bbox"]
            box = slide.shapes.add_textbox(Pt(offset_x + x0 * scale), Pt(offset_y + y0 * scale),
                                          Pt(max(1, (x1 - x0) * scale + 3)), Pt(max(1, (y1 - y0) * scale + 3)))
            text = box.text_frame
            text.margin_left = text.margin_right = text.margin_top = text.margin_bottom = 0
            text.word_wrap = False
            text.auto_size = MSO_AUTO_SIZE.NONE
            paragraph = text.paragraphs[0]
            paragraph.space_before = paragraph.space_after = Pt(0)
            for span in line["spans"]:
                run = paragraph.add_run()
                run.text = span["text"]
                run.font.name = "맑은 고딕"
                run.font.size = Pt(max(1, span["size"] * scale))
                run.font.bold = bool(span["flags"] & 16)
                run.font.italic = bool(span["flags"] & 2)
                run.font.color.rgb = RGBColor.from_string(f'{span["color"]:06X}')
    result.save(target)


def convert(request):
    sources = [Path(p).resolve(strict=True) for p in request["sources"]]
    destination = Path(request["destination"]).resolve(strict=True)
    format = request["format"]
    mode = request.get("mode", "editable")
    dpi = int(request.get("dpi", 150))
    cancel_file = request.get("cancel_file")
    if not sources or format not in ("pdf", "png", "jpg", "docx", "pptx") or mode not in ("editable", "appearance") or dpi not in (96, 150, 300):
        raise ConversionError("변환 설정이 올바르지 않습니다.")
    if not destination.is_dir():
        raise ConversionError("결과를 저장할 폴더를 선택하세요.")
    published = []
    reserved = set()
    with tempfile.TemporaryDirectory(prefix=".paperlight-convert-", dir=destination) as name:
        staging = Path(name)
        outputs = []
        for source in sources:
            check_cancel(cancel_file)
            suffix = source.suffix.lower()
            if (format == "pdf" and suffix not in (".jpg", ".jpeg", ".png", ".doc", ".docx", ".ppt", ".pptx")) or (format != "pdf" and suffix != ".pdf"):
                raise ConversionError(f"지원하지 않는 변환입니다: {source.name} → {format}")
            basename = source.stem + (f"_{format}" if format in ("png", "jpg") else f"_변환.{format}")
            candidate = destination / basename
            number = 2
            while candidate.exists() or str(candidate).casefold() in reserved:
                candidate = destination / (f"{source.stem}_{format}_{number}" if format in ("png", "jpg") else f"{source.stem}_변환_{number}.{format}")
                number += 1
            reserved.add(str(candidate).casefold())
            target = staging / candidate.name
            if format == "pdf":
                if suffix in (".png", ".jpg", ".jpeg"):
                    image_to_pdf(source, target)
                else:
                    office_to_pdf(source, target)
                with fitz.open(target) as check:
                    if check.page_count < 1:
                        raise ConversionError("결과 PDF에 페이지가 없습니다.")
            else:
                with open_pdf(source) as doc:
                    if format in ("png", "jpg"):
                        target.mkdir()
                        for i, page in enumerate(doc):
                            check_cancel(cancel_file)
                            render(page, dpi).save(target / f"{i + 1:04d}.{format}")
                    elif format == "docx":
                        pdf_to_docx(doc, target, mode, dpi, cancel_file)
                    else:
                        pdf_to_pptx(doc, target, mode, dpi, cancel_file)
            outputs.append((target, candidate))
        check_cancel(cancel_file)
        try:
            for temporary, final in outputs:
                # Windows rename은 기존 파일/폴더를 덮어쓰지 않는다.
                if final.exists():
                    raise ConversionError("변환 중 같은 이름의 결과가 생겼습니다. 다시 실행하세요.")
                temporary.rename(final)
                published.append(final)
        except Exception:
            for path in published:
                assert path.resolve().parent == destination, "결과 폴더 밖의 파일은 정리하지 않습니다."
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            raise
    return [str(p) for p in published]


def worker(request_path, result_path):
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
        result = dict(status="ok", outputs=convert(request))
    except Cancelled:
        result = dict(status="cancelled", outputs=[])
    except Exception as exc:
        result = dict(status="error", error=str(exc), outputs=[])
    result_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return 0 if result["status"] in ("ok", "cancelled") else 1
