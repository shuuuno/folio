"""지원되는 Windows 등록 방식만 사용한다. UserChoice는 변경하지 않는다."""
import ctypes
from pathlib import Path
import sys
import winreg


def registration_values(executable):
    exe = str(Path(executable).resolve())
    if '"' in exe:
        raise ValueError("실행 파일 경로에 따옴표가 포함되어 있습니다.")
    return [
        (r"Software\Classes\Paperlight.PDF", "", "Folio PDF 문서"),
        (r"Software\Classes\Paperlight.PDF\DefaultIcon", "", f'"{exe}",0'),
        (r"Software\Classes\Paperlight.PDF\shell\open\command", "", f'"{exe}" "%1"'),
        (r"Software\Classes\.pdf\OpenWithProgids", "Paperlight.PDF", ""),
        (r"Software\Paperlight\Capabilities", "ApplicationName", "Folio"),
        (r"Software\Paperlight\Capabilities", "ApplicationDescription", "오프라인 PDF 뷰어·편집기"),
        (r"Software\Paperlight\Capabilities\FileAssociations", ".pdf", "Paperlight.PDF"),
        (r"Software\RegisteredApplications", "Folio", r"Software\Paperlight\Capabilities"),
    ]


def register_pdf_app():
    if not getattr(sys, "frozen", False):
        raise RuntimeError("설치판 또는 포터블 Folio.exe에서 기본 앱을 등록할 수 있습니다.")
    for path, name, value in registration_values(sys.executable):
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    # 예전 후보 이름만 정리한다. ProgID와 UserChoice는 그대로 유지한다.
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\RegisteredApplications", 0,
                        winreg.KEY_READ | winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY) as key:
        try:
            if winreg.QueryValueEx(key, "Paperlight")[0] == r"Software\Paperlight\Capabilities":
                winreg.DeleteValue(key, "Paperlight")
        except FileNotFoundError:
            pass
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)


def unregister_pdf_app():
    """현재 제거 중인 실행 파일이 소유한 후보 등록만 정리한다."""
    expected = dict(((path, name), value) for path, name, value in registration_values(sys.executable))
    command_key = r"Software\Classes\Paperlight.PDF\shell\open\command"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, command_key, 0,
                            winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            if winreg.QueryValueEx(key, "")[0] != expected[(command_key, "")]:
                return
    except FileNotFoundError:
        return
    # 하위 키를 역순으로 지운다. UserChoice에는 접근하지 않는다.
    paths = [r"Software\Classes\Paperlight.PDF\shell\open\command",
             r"Software\Classes\Paperlight.PDF\shell\open",
             r"Software\Classes\Paperlight.PDF\shell",
             r"Software\Classes\Paperlight.PDF\DefaultIcon",
             r"Software\Classes\Paperlight.PDF",
             r"Software\Paperlight\Capabilities\FileAssociations",
             r"Software\Paperlight\Capabilities"]
    for path in paths:
        try:
            winreg.DeleteKeyEx(winreg.HKEY_CURRENT_USER, path, winreg.KEY_WOW64_64KEY)
        except FileNotFoundError:
            pass
    for path, name in ((r"Software\Classes\.pdf\OpenWithProgids", "Paperlight.PDF"),
                       (r"Software\RegisteredApplications", "Folio")):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0,
                                winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY) as key:
                winreg.DeleteValue(key, name)
        except FileNotFoundError:
            pass
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
