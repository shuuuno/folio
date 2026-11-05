"""검토한 Git 소스에서 포터블 ZIP, 설치 EXE, 소스 ZIP, SHA256을 만든다."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from paperlight import __version__

NSIS_URL = "https://downloads.sourceforge.net/project/nsis/NSIS%203/3.12/nsis-3.12.zip"
# 공식 HTTPS 배포본을 최초 수령해 기록한 해시. 별도 서명 검증을 뜻하지 않는다.
NSIS_SHA256 = "56581f90db321581c5381193d796fffcf2d24b2f8fed2160a6c6a3baa67f2c4f"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nsis_compiler():
    base = ROOT / "build" / "tools"
    base.mkdir(parents=True, exist_ok=True)
    archive = base / "nsis-3.12.zip"
    if not archive.exists():
        with urllib.request.urlopen(NSIS_URL, timeout=90) as response:
            archive.write_bytes(response.read())
    if sha256(archive) != NSIS_SHA256:
        raise RuntimeError("NSIS 다운로드 해시 불일치. 파일을 사용하지 않습니다.")
    with zipfile.ZipFile(archive) as z:
        if not all((base / n).resolve().is_relative_to(base.resolve()) for n in z.namelist()):
            raise RuntimeError("NSIS ZIP 경로 오류")
        z.extractall(base)
    return base / "nsis-3.12" / "makensis.exe"


def nsis_quote(value):
    return str(value).replace("$", "$$").replace('"', '$\\"')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    status = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=normal"], cwd=ROOT, text=True)
    if status.strip():
        raise SystemExit("배포 전에 검토한 소스를 커밋하세요. 작업 트리가 변경되어 있습니다.")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    compiler = nsis_compiler()
    payload = ROOT / "build" / "distribution" / "Paperlight"
    subprocess.run([sys.executable, "scripts/build.py", "--dist-dir", str(payload.parent)], cwd=ROOT, check=True)
    if not (payload / "Paperlight.exe").is_file():
        raise SystemExit("포터블 빌드가 없습니다.")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip() or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != commit:
        raise SystemExit("빌드 중 소스가 변경되었습니다. 새 커밋에서 다시 빌드하세요.")
    shutil.copy2(compiler.parent / "COPYING", payload / "licenses" / "NSIS-COPYING.txt")
    (payload / "build-info.json").write_text(json.dumps(dict(version=__version__, commit=commit,
        python=sys.version, nsis="3.12", nsis_sha256=NSIS_SHA256), indent=2), encoding="utf-8")
    # 삭제 대상을 빌드 파일 목록으로 제한한다. 사용자가 둔 PDF·설정은 지우지 않는다.
    files = sorted(p.relative_to(payload) for p in payload.rglob("*") if p.is_file())
    directories = sorted((p.relative_to(payload) for p in payload.rglob("*") if p.is_dir()),
                         key=lambda p: (len(p.parts), str(p)), reverse=True)
    owned = ROOT / "build" / "uninstall-files.nsh"
    owned.write_text("\n".join(
        [f'Delete "$INSTDIR\\{nsis_quote(p)}"' for p in files]
        + [f'RMDir "$INSTDIR\\{nsis_quote(p)}"' for p in directories]), encoding="utf-8-sig")
    release = ROOT / "release" / __version__
    release.mkdir(parents=True, exist_ok=True)
    setup = release / f"Paperlight-{__version__}-Setup.exe"
    subprocess.run([str(compiler), "/V2", "/INPUTCHARSET", "UTF8", f"/DAPP_VERSION={__version__}",
                    f"/DPAYLOAD={payload}", f"/DOWNED_FILES={owned}", f"/DOUTPUT={setup}",
                    str(ROOT / "packaging" / "paperlight.nsi")], check=True)
    portable = Path(shutil.make_archive(str(release / f"Paperlight-{__version__}-Portable"), "zip", payload.parent, payload.name))
    source = release / f"Paperlight-{__version__}-Source.zip"
    subprocess.run(["git", "archive", "--format=zip", f"--prefix=Paperlight-{__version__}/",
                    "-o", str(source), commit], cwd=ROOT, check=True)
    (release / "SHA256SUMS.txt").write_text("".join(f"{sha256(p)}  {p.name}\n" for p in (setup, portable, source)), encoding="utf-8")
    print(f"배포 파일: {release}\n소스 커밋: {commit}")


if __name__ == "__main__":
    main()
