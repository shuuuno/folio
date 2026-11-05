"""PDF 좌표의 문자 선택. 저장되는 주석이나 문서 변경은 만들지 않는다."""
from dataclasses import dataclass
import pymupdf as fitz


@dataclass(frozen=True)
class Character:
    text: str
    box: tuple
    line: int
    direction: tuple


class TextSelection:
    def __init__(self, page):
        self.characters = []
        self.start = self.end = 0
        line_number = 0
        data = page.get_text("rawdict", sort=True, flags=fitz.TEXTFLAGS_RAWDICT & ~fitz.TEXT_PRESERVE_IMAGES)
        for block in data["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    for char in span["chars"]:
                        self.characters.append(Character(char["c"], tuple(char["bbox"]), line_number, tuple(line["dir"])))
                line_number += 1

    def boundary(self, point, require_hit=False):
        if not self.characters:
            return None
        def distance(char):
            x0, y0, x1, y1 = char.box
            dx, dy = max(x0 - point.x, 0, point.x - x1), max(y0 - point.y, 0, point.y - y1)
            return dx * dx + dy * dy
        index = min(range(len(self.characters)), key=lambda i: distance(self.characters[i]))
        char = self.characters[index]
        if require_hit and distance(char) > 0:
            return None
        x0, y0, x1, y1 = char.box
        dx, dy = char.direction
        after = (point.x - (x0 + x1) / 2) * dx + (point.y - (y0 + y1) / 2) * dy >= 0
        return index + int(after)

    def select(self, start, end):
        low, high = sorted((start, end))
        self.start = max(0, min(len(self.characters), low))
        self.end = max(0, min(len(self.characters), high))

    @property
    def text(self):
        result, previous = [], None
        for char in self.characters[self.start:self.end]:
            if previous is not None and char.line != previous:
                result.append("\n")
            result.append(char.text)
            previous = char.line
        return "".join(result)

    def rectangles(self):
        lines = {}
        for char in self.characters[self.start:self.end]:
            box = fitz.Rect(char.box)
            lines[char.line] = lines[char.line] | box if char.line in lines else box
        return list(lines.values())
