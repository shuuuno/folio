"""기존 설치를 보호하며 별도 경로에서 실제 Windows 설치·실행·제거를 확인한다."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
import winreg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from paperlight import __version__

KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Paperlight"
VIEW = winreg.KEY_WOW64_32KEY


def registration(view=VIEW):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_READ | view) as key:
            return {name: winreg.QueryValueEx(key, name)[0] for name in ("InstallLocation", "DisplayVersion")}
    except FileNotFoundError:
        return None


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, timeout=90):
    return subprocess.run(command, timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW).returncode


def main():
    # 실제 설치가 있으면 등록 정보·시작 메뉴를 일시적으로라도 덮지 않는다.
    shortcut_dir = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Paperlight"
    if registration() or registration(winreg.KEY_WOW64_64KEY) or shortcut_dir.exists():
        raise SystemExit("기존 Paperlight 설치/시작 메뉴가 있어 중단합니다. 깨끗한 Windows 계정에서 검증하세요.")
    output = ROOT / "evidence" / ("installer-" + uuid.uuid4().hex[:8])
    output.mkdir(parents=True)
    target = (ROOT / "build" / "installer-qa" / output.name / "한글 경로 Paperlight").resolve()
    assert target.is_relative_to((ROOT / "build" / "installer-qa").resolve()) and not target.exists()
    setup = ROOT / "release" / __version__ / f"Paperlight-{__version__}-Setup.exe"
    payload = ROOT / "build" / "distribution" / "Paperlight"
    profile = Path(os.environ["LOCALAPPDATA"]) / "Paperlight/Paperlight"
    before = {str(p.relative_to(profile)): digest(p) for p in profile.rglob("*") if p.is_file()}
    result = {"passed": False, "version": __version__, "install_path": str(target)}
    child = None
    installed = False
    uninstaller_copy = output / "uninstall-check.exe"
    try:
        assert run(f'"{setup}" /S /D={target}') == 0, "설치 실패"
        installed = True
        executable = target / "Paperlight.exe"
        assert registration() == dict(InstallLocation=str(target), DisplayVersion=__version__)
        assert (shortcut_dir / "Paperlight.lnk").is_file()
        assert (shortcut_dir / "Paperlight 제거.lnk").is_file()
        expected = {str(p.relative_to(payload)): digest(p) for p in payload.rglob("*") if p.is_file()}
        assert all((target / rel).is_file() and digest(target / rel) == h for rel, h in expected.items())
        result.update(installed_files_match=True, registered_version=True, start_menu=True)
        # 실제 사용자 문서·복구 공간과 분리된 합성 문서 시험.
        for flag, folder, report in (("--verify-build", "app", "package-check.json"),
                                     ("--verify-recovery", "recovery", "recovery-check.json")):
            assert run([str(executable), flag, str(output / folder)], timeout=120) == 0, flag
            data = json.loads((output / folder / report).read_text(encoding="utf-8"))
            assert data["passed"] and data["frozen"], report
        result["installed_app_and_recovery"] = True
        # 사용 중인 설치/제거는 파일을 바꾸기 전에 거부해야 한다.
        busy = output / "busy"
        busy.mkdir()
        shutil.copy2(target / "시작하기.pdf", busy / "복구실험원본.pdf")
        child = subprocess.Popen([str(executable), "--verify-recovery-worker", str(busy)],
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        deadline = time.monotonic() + 30
        while not (busy / "worker-ready.json").exists() and child.poll() is None and time.monotonic() < deadline:
            time.sleep(.05)
        assert (busy / "worker-ready.json").exists(), "검증용 앱 시작 실패"
        shutil.copy2(target / "Uninstall.exe", uninstaller_copy)
        assert run(f'"{setup}" /S /D={target}') != 0, "실행 중 설치 차단 실패"
        assert run(f'"{uninstaller_copy}" /S _?={target}') != 0, "실행 중 제거 차단 실패"
        assert all(digest(target / rel) == h for rel, h in expected.items())
        child.kill()  # 이 함수가 만든 격리된 검증 전용 프로세스만 종료한다.
        child.wait(timeout=10)
        child = None
        result["in_use_install_and_uninstall_blocked"] = True
        root_sentinel = target / "사용자문서-보존.txt"
        nested_sentinel = target / "_internal" / "사용자파일-보존.txt"
        for sentinel in (root_sentinel, nested_sentinel):
            sentinel.write_text("keep user data", encoding="utf-8")
        assert run(f'"{setup}" /S /D={target}') == 0, "재설치 실패"
        assert root_sentinel.read_text(encoding="utf-8") == "keep user data"
        assert digest(executable) == expected["Paperlight.exe"]
        result["reinstall_preserves_user_file"] = True
        shutil.copy2(target / "Uninstall.exe", uninstaller_copy)
        assert run(f'"{uninstaller_copy}" /S _?={target}') == 0, "제거 실패"
        installed = False
        assert not registration() and not shortcut_dir.exists()
        assert not (target / "Uninstall.exe").exists()
        assert not any((target / rel).exists() for rel in expected), "프로그램 파일이 남았습니다"
        assert all(p.read_text(encoding="utf-8") == "keep user data" for p in (root_sentinel, nested_sentinel))
        after = {str(p.relative_to(profile)): digest(p) for p in profile.rglob("*") if p.is_file()}
        assert before == after, "사용자 데이터가 변경되었습니다. 실행 중 사용자 작업 여부를 확인하세요."
        result.update(uninstalled_owned_files=True, user_files_preserved=True,
                      user_profile_unchanged=True, passed=True)
    finally:
        if child and child.poll() is None:
            child.kill()
            child.wait(timeout=10)
        if installed and (target / "Uninstall.exe").exists():
            shutil.copy2(target / "Uninstall.exe", uninstaller_copy)
            result["failure_cleanup_exit"] = run(f'"{uninstaller_copy}" /S _?={target}')
        (output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"검증 기록: {output}")


if __name__ == "__main__":
    main()
