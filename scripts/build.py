"""Python 설치가 필요 없는 Windows 포터블 폴더를 만든다."""
import argparse
from pathlib import Path
import importlib.metadata
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from paperlight import __version__
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--dist-dir", type=Path, default=ROOT / "dist")
args = parser.parse_args()
os.chdir(ROOT)
target = args.dist_dir.resolve() / "Paperlight"
(ROOT / "build").mkdir(exist_ok=True)
version_tuple = tuple(map(int, __version__.split("."))) + (0,)
version_file = ROOT / "build" / "version.txt"
version_file.write_text(f'''VSVersionInfo(
  ffi=FixedFileInfo(filevers={version_tuple}, prodvers={version_tuple},
    mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0,0)),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('FileDescription', 'Paperlight PDF Editor'),
    StringStruct('FileVersion', '{__version__}'),
    StringStruct('ProductName', 'Paperlight'),
    StringStruct('ProductVersion', '{__version__}'),
    StringStruct('OriginalFilename', 'Paperlight.exe')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])])
''', encoding="utf-8")
command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
           "--name", "Paperlight", "--distpath", str(target.parent),
           "--icon", "assets/paperlight.ico", "--version-file", str(version_file),
           "--add-data", "assets/paperlight.ico;assets", "--add-data", "assets/fonts;assets/fonts",
           "--add-data", "assets/ui;assets/ui",
           "--exclude-module", "PySide6.QtTest",
           "--exclude-module", "tkinter", "launcher.py"]
subprocess.run(command, check=True)
shutil.copy2(ROOT / "README.md", target / "사용안내.md")
shutil.copy2(ROOT / "assets" / "시작하기.pdf", target / "시작하기.pdf")
shutil.copytree(ROOT / "docs", target / "docs", dirs_exist_ok=True)
shutil.copy2(ROOT / "THIRD_PARTY_NOTICES.md", target / "THIRD_PARTY_NOTICES.md")
licenses = target / "licenses"
licenses.mkdir(exist_ok=True)
for package in ("PyMuPDF", "PySide6-Essentials", "shiboken6", "PyInstaller", "python-docx", "python-pptx", "Pillow", "lxml", "pywin32", "typing_extensions", "XlsxWriter"):
    dist = importlib.metadata.distribution(package)
    for item in dist.files or []:
        if any(word in str(item).lower() for word in ("license", "copying", "notice")) and Path(dist.locate_file(item)).is_file():
            dest = licenses / package / str(item).replace("/", "_").replace("\\", "_")
            dest.parent.mkdir(exist_ok=True)
            shutil.copy2(dist.locate_file(item), dest)
shutil.copy2(Path(sys.base_prefix) / "LICENSE.txt", licenses / "Python-LICENSE.txt")
print(f"완료: {target / 'Paperlight.exe'}")
