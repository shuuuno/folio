from pathlib import Path
import pymupdf as fitz

FONT = "C:/Windows/Fonts/malgun.ttf"


def make_pdf(path, subset=False):
    doc = fitz.open()
    p = doc.new_page(width=595, height=842)
    p.draw_rect(fitz.Rect(0, 0, 595, 115), fill=(.92, .96, .95), color=None)
    p.insert_font(fontname="Korean", fontfile=FONT)
    p.insert_text((44, 45), "PAPERLIGHT  /  DOCUMENT STUDIO", fontsize=10, color=(.12, .40, .36))
    p.insert_text((44, 84), "새로운 문서 작업의 시작", fontname="Korean", fontsize=25, color=(.09, .23, .26))
    p.insert_text((44, 156), "프로젝트 검토서", fontname="Korean", fontsize=18)
    p.insert_text((44, 194), "검토 상태: 확인 대기", fontname="Korean", fontsize=13)
    p.insert_text((44, 222), "담당자: 김하늘", fontname="Korean", fontsize=13)
    p.insert_text((44, 267), "Project status: Draft", fontsize=14, color=(.2, .3, .4))
    p.draw_line((44, 290), (551, 290), color=(.8, .85, .87))
    p.insert_text((44, 326), "01   문서를 읽고 필요한 부분만 수정하세요.", fontname="Korean", fontsize=13)
    p.insert_text((44, 356), "02   추가할 내용은 빈 곳에 직접 넣으세요.", fontname="Korean", fontsize=13)
    p.insert_text((44, 386), "03   서명을 넣고 새 PDF로 저장하세요.", fontname="Korean", fontsize=13)
    p.draw_rect(fitz.Rect(44, 435, 551, 595), fill=(.97, .98, .985), color=(.87, .91, .93))
    p.insert_text((62, 463), "메모", fontname="Korean", fontsize=12, color=(.4, .5, .55))
    p.insert_text((44, 658), "확인 서명", fontname="Korean", fontsize=12)
    p.draw_line((160, 705), (390, 705), color=(.7, .77, .8))
    p.insert_text((44, 792), "개인용 예제 문서 · 실제 개인정보가 포함되어 있지 않습니다.", fontname="Korean", fontsize=9, color=(.5, .56, .6))
    p = doc.new_page(width=595, height=842)
    p.insert_font(fontname="Korean", fontfile=FONT)
    p.insert_text((44, 70), "두 번째 페이지", fontname="Korean", fontsize=24)
    p.insert_text((44, 120), "본문 수정과 페이지 이동을 확인하는 예제입니다.", fontname="Korean", fontsize=13)
    if subset:
        doc.subset_fonts()
    doc.save(str(path), garbage=4, deflate=True)
    doc.close()


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    (root / "assets").mkdir(exist_ok=True)
    make_pdf(root / "assets" / "시작하기.pdf", subset=True)
