"""Windows 설치 글꼴 목록과 편집 가능한 전체 글꼴 임베딩."""
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
import os
from pathlib import Path
import struct
import sys

from fontTools.ttLib import TTFont, TTLibError


@dataclass(frozen=True)
class InstalledFont:
    key: str
    path: Path
    index: int
    label: str


def embedding_allowed(fs_type):
    # 편집 가능 또는 설치 가능 권한만 사용한다. 0x0100은 전체 내장으로 준수한다.
    # restricted(0x0002), preview/print(0x0004), bitmap-only(0x0200), 미상 비트는 제외한다.
    return (fs_type & ~0x0100) in (0, 0x0008)


def font_key(path, index=0):
    return f"{str(Path(path).resolve()).casefold()}#{index}"


def default_font_id(bold=False):
    return font_key(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" /
                    ("malgunbd.ttf" if bold else "malgun.ttf"))


def _font_paths():
    system = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    user = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "Microsoft/Windows/Fonts"
    paths = set()
    for directory in (system, user):
        if directory.is_dir():
            paths.update(p.resolve() for p in directory.iterdir() if p.suffix.lower() in (".ttf", ".otf", ".ttc", ".otc"))
    if sys.platform == "win32":
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(hive, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts") as key:
                    for i in range(winreg.QueryInfoKey(key)[1]):
                        _, value, kind = winreg.EnumValue(key, i)
                        if kind not in (winreg.REG_SZ, winreg.REG_EXPAND_SZ):
                            continue
                        path = Path(os.path.expandvars(value))
                        if not path.is_absolute():
                            path = system / path
                        if path.is_file() and path.suffix.lower() in (".ttf", ".otf", ".ttc", ".otc"):
                            paths.add(path.resolve())
            except OSError:
                continue
    return sorted(paths, key=lambda p: str(p).casefold())


def _family(font):
    names = font["name"]
    for name_id in (16, 1):
        for record in names.names:
            if record.nameID == name_id and record.platformID == 3 and record.langID == 0x0412:
                return record.toUnicode()
    return names.getBestFamilyName() or "이름 없는 글꼴"


@lru_cache(maxsize=1)
def installed_fonts():
    result = []
    for path in _font_paths():
        try:
            with path.open("rb") as stream:
                header = stream.read(12)
            count = struct.unpack(">I", header[8:12])[0] if header[:4] == b"ttcf" else 1
            if not 0 < count <= 512:
                continue
            for index in range(count):
                try:
                    with path.open("rb") as stream, TTFont(stream, fontNumber=index, lazy=True, recalcTimestamp=False) as font:
                        if "OS/2" not in font or not embedding_allowed(font["OS/2"].fsType):
                            continue
                        family = _family(font)
                        style = font["name"].getBestSubFamilyName() or "Regular"
                        label = family if style.lower() in ("regular", "normal", "보통") else f"{family} ({style})"
                        result.append(InstalledFont(font_key(path, index), path, index, label))
                except (OSError, TTLibError, ValueError, KeyError, IndexError, UnicodeError, struct.error):
                    continue
        except (OSError, struct.error):
            continue
    return tuple(sorted(result, key=lambda f: (f.key != default_font_id(), f.label.casefold(), f.key)))


def font_bytes(key):
    choice = next((font for font in installed_fonts() if font.key == key), None)
    if choice is None:
        raise ValueError("설치된 편집용 글꼴을 찾지 못했습니다. 글꼴을 다시 선택해 주세요.")
    try:
        # 선택 이후 파일이 교체되었을 수도 있으므로 저장 직전 권한을 재검사한다.
        data = choice.path.read_bytes()
        with TTFont(BytesIO(data), fontNumber=choice.index, recalcTimestamp=False) as font:
            if "OS/2" not in font or not embedding_allowed(font["OS/2"].fsType):
                raise ValueError("이 글꼴은 편집용 PDF에 내장할 수 없습니다.")
            if data[:4] != b"ttcf":
                return data
            buffer = BytesIO()
            font.save(buffer)
            return buffer.getvalue()
    except (OSError, TTLibError) as exc:
        raise ValueError("선택한 글꼴 파일을 읽지 못했습니다. 다시 선택해 주세요.") from exc
