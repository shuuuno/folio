"""앱이 추가한 독립 콘텐츠 스트림과 재편집 정보. 외부 파일은 필요 없다."""
import base64
from hashlib import sha256
import json
import re
import math
from uuid import uuid4

import pymupdf as fitz

KEY = "PaperlightObject"


def objects(page):
    result = []
    for xref in page.get_contents():
        kind, value = page.parent.xref_get_key(xref, KEY)
        if kind != "string":
            continue
        try:
            item = json.loads(value)
            if (item["version"] != 1 or item["kind"] not in ("text", "signature")
                    or not re.fullmatch(r"[a-f0-9]{32}", item["id"])
                    or item["digest"] != sha256(page.parent.xref_stream(xref)).hexdigest()):
                continue
            rect = fitz.Rect(item["rect"])
            if rect.is_empty or rect.is_infinite or not all(math.isfinite(v) for v in rect):
                continue
            if (not isinstance(item["resource"], list) or len(item["resource"]) != 2
                    or item["resource"][0] not in ("Font", "XObject")
                    or not re.fullmatch(r"[A-Za-z0-9]+", item["resource"][1])):
                continue
            if item["kind"] == "text" and (not isinstance(item["text"], str)
                    or not 0 < item["size"] <= 1000 or len(item["color"]) != 3
                    or not all(0 <= v <= 1 for v in item["color"])):
                continue
            if item["kind"] == "signature" and not isinstance(item["image"], str):
                continue
            item["xref"] = xref
            result.append(item)
        except (ValueError, KeyError, TypeError):
            continue
    return result


def set_contents(page, contents):
    page.parent.xref_set_key(page.xref, "Contents", "[" + " ".join(f"{x} 0 R" for x in contents) + "]")


def remove(page, items):
    removed = {item["xref"] for item in items}
    set_contents(page, [x for x in page.get_contents() if x not in removed])
    # Resources may be shared between pages. Clone dictionaries before dropping
    # an unused name, and never remove a name still referenced by another stream.
    doc = page.parent
    remaining = b"\n".join(doc.xref_stream(x) for x in page.get_contents())
    for item in items:
        category, name = item["resource"]
        if category not in ("Font", "XObject") or not re.fullmatch(r"[A-Za-z0-9]+", name):
            continue
        if re.search(rb"/" + name.encode("ascii") + rb"(?![A-Za-z0-9])", remaining):
            continue
        kind, value = doc.xref_get_key(page.xref, "Resources")
        if kind == "xref":
            value = doc.xref_object(int(value.split()[0]), compressed=True)
        if not value.startswith("<<"):
            continue
        resources = doc.get_new_xref()
        doc.update_object(resources, value)
        doc.xref_set_key(page.xref, "Resources", f"{resources} 0 R")
        kind, value = doc.xref_get_key(resources, category)
        if kind == "xref":
            doc.xref_set_key(resources, category, doc.xref_object(int(value.split()[0]), compressed=True))
        doc.xref_set_key(resources, category + "/" + name, "null")
    return doc.reload_page(page)


def insert(page, spec, font=None):
    item = {key: value for key, value in spec.items() if key not in ("xref", "digest", "resource")}
    item.setdefault("id", uuid4().hex)
    item["version"] = 1
    item["rect"] = list(item["rect"])
    before = set(page.get_contents())
    if item["kind"] == "text":
        name = "PLObj" + item["id"]
        page.insert_font(fontname=name, fontbuffer=font.buffer)
        available = page.insert_textbox(item["rect"], item["text"], fontsize=item["size"],
                                        color=item["color"], fontname=name)
        if available < 0:
            raise ValueError("내용이 영역에 들어가지 않습니다. 영역을 넓히거나 글자 크기를 줄여 주세요.")
        item["resource"] = ["Font", name]
    else:
        page.insert_image(item["rect"], stream=base64.b64decode(item["image"], validate=True), keep_proportion=True)
    added = [x for x in page.get_contents() if x not in before]
    # PyMuPDF can add wrapping streams around existing unbalanced content.
    painted = [x for x in added if (b"BT" in page.parent.xref_stream(x) if item["kind"] == "text"
                                   else b" Do" in page.parent.xref_stream(x))]
    if len(painted) != 1:
        raise ValueError("추가 항목을 독립적으로 저장하지 못해 작업을 취소했습니다.")
    xref = painted[0]
    stream = page.parent.xref_stream(xref)
    if item["kind"] == "signature":
        names = re.findall(rb"/([A-Za-z0-9]+)\s+Do", stream)
        if len(names) != 1:
            raise ValueError("서명 리소스를 확인하지 못했습니다.")
        item["resource"] = ["XObject", names[0].decode("ascii")]
    item["digest"] = sha256(stream).hexdigest()
    page.parent.xref_set_key(xref, KEY, fitz.get_pdf_str(json.dumps(item, ensure_ascii=True)))
    return item["id"]
