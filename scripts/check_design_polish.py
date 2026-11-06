"""Hallmark의 네이티브 수동 검토를 보조하는 대비·캡처 무결성 검사."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from paperlight.theme import COLORS
from paperlight.style import STYLE


def luminance(color):
    values = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return sum(weight * (value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4)
               for weight, value in zip((.2126, .7152, .0722), values))


def main():
    pairs = [("ink", "surface", 4.5), ("muted", "surface", 4.5),
             ("muted", "chrome", 4.5), ("muted", "canvas", 4.5), ("muted", "rail", 4.5),
             ("surface", "accent", 4.5), ("surface", "accent_hover", 4.5),
             ("surface", "accent_pressed", 4.5), ("accent", "selected", 4.5),
             ("danger", "surface", 4.5), ("selection_ink", "selection_text", 4.5),
             ("focus", "surface", 3), ("focus", "chrome", 3),
             ("control_border", "surface", 3)]
    contrasts = []
    for foreground, background, minimum in pairs:
        high, low = sorted((luminance(COLORS[foreground]), luminance(COLORS[background])), reverse=True)
        ratio = (high + .05) / (low + .05)
        assert ratio >= minimum, (foreground, background, ratio)
        contrasts.append(dict(foreground=foreground, background=background,
                              ratio=round(ratio, 3), minimum=minimum))
    assert "@" not in STYLE, "치환하지 않은 스타일 토큰"
    output = ROOT / "docs/design-polish"
    screenshots = []
    for prefix in ("01-empty", "02-reading", "03-edit", "04-text", "05-compact",
                   "06-conversion", "07-signature", "08-placement"):
        for phase in ("before", "after"):
            path = output / f"{prefix}-{phase}.png"
            raw = path.read_bytes()
            assert raw.startswith(b"\x89PNG\r\n\x1a\n")
            screenshots.append(dict(file=path.name, sha256=hashlib.sha256(raw).hexdigest(),
                                    pixels=[int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big")]))
    result = dict(passed=True, method="Qt 네이티브 검토 보조. 웹 DOM 검사가 아님",
                  contrast_pairs=contrasts, screenshots=screenshots)
    (output / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"대비 {len(contrasts)}쌍, 전후 PNG {len(screenshots)}개 검사 통과")


if __name__ == "__main__":
    main()
