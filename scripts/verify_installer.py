"""기존 설치를 보호하며 별도 경로에서 실제 Windows 설치·실행·제거를 확인한다."""
import argparse
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
from paperlight.windows_integration import registration_values

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


def registry_value(path, name):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            return winreg.QueryValueEx(key, name)[0]
    except FileNotFoundError:
        return None


def settings_snapshot():
    values = {}
    def visit(path):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
                subkeys, count, _ = winreg.QueryInfoKey(key)
                for i in range(count):
                    name, value, kind = winreg.EnumValue(key, i)
                    values[(path, name)] = (value, kind)
                for i in range(subkeys):
                    visit(path + "\\" + winreg.EnumKey(key, i))
        except FileNotFoundError:
            pass
    visit(r"Software\Paperlight\Paperlight")
    return values


def run(command, timeout=90):
    return subprocess.run(command, timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW).returncode


def main():
    if tuple(map(int, __version__.split("."))) >= (0, 11, 0):
        from scripts.verify_velopack_installer import main as verify
        return verify()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upgrade-from", type=Path, help="이전 Paperlight 설치판에서 업데이트 검증")
    args = parser.parse_args()
    # 실제 설치가 있으면 등록 정보·시작 메뉴를 일시적으로라도 덮지 않는다.
    shortcut_dir = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Folio"
    legacy_shortcut = shortcut_dir.with_name("Paperlight")
    if registration() or registration(winreg.KEY_WOW64_64KEY) or shortcut_dir.exists() or legacy_shortcut.exists():
        raise SystemExit("기존 Folio/Paperlight 설치/시작 메뉴가 있어 중단합니다. 깨끗한 Windows 계정에서 검증하세요.")
    if any(registry_value(r"Software\RegisteredApplications", name) is not None for name in ("Paperlight", "Folio")):
        raise SystemExit("Folio/Paperlight 기본 앱 후보 등록이 이미 있습니다. 이를 보존하기 위해 검증을 중단합니다.")
    choice_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.pdf\UserChoice"
    user_choice = (registry_value(choice_path, "ProgId"), registry_value(choice_path, "Hash"))
    output = ROOT / "evidence" / ("installer-" + uuid.uuid4().hex[:8])
    output.mkdir(parents=True)
    target = (ROOT / "build" / "installer-qa" / output.name / "한글 경로 Paperlight").resolve()
    assert target.is_relative_to((ROOT / "build" / "installer-qa").resolve()) and not target.exists()
    setup = ROOT / "release" / __version__ / f"Folio-{__version__}-Setup.exe"
    payload = ROOT / "build" / "distribution" / "Folio"
    profile = Path(os.environ["LOCALAPPDATA"]) / "Paperlight/Paperlight"
    settings_before = settings_snapshot()
    before = {str(p.relative_to(profile)): digest(p) for p in profile.rglob("*") if p.is_file()}
    result = {"passed": False, "version": __version__, "install_path": str(target)}
    child = None
    installed = False
    uninstaller_copy = output / "uninstall-check.exe"
    try:
        legacy_copy = None
        if args.upgrade_from:
            old_setup = args.upgrade_from.resolve(strict=True)
            assert run(f'"{old_setup}" /S /D={target}') == 0, "이전 설치 실패"
            installed = True
            assert (target / "Paperlight.exe").is_file() and (legacy_shortcut / "Paperlight.lnk").exists()
            assert registration()["InstallLocation"] == str(target)
            legacy_copy = output / "legacy-app"
            shutil.copytree(target, legacy_copy)
            (target / "업데이트-보존.txt").write_text("업데이트 전 사용자 파일", encoding="utf-8")
            # 이전 실행 파일이 사용 중일 때도 새 설치는 파일 변경 전에 차단한다.
            old_busy = output / "legacy-busy"
            old_busy.mkdir()
            shutil.copy2(target / "시작하기.pdf", old_busy / "복구실험원본.pdf")
            child = subprocess.Popen([str(target / "Paperlight.exe"), "--verify-recovery-worker", str(old_busy)], creationflags=subprocess.CREATE_NO_WINDOW)
            deadline = time.monotonic() + 30
            while not (old_busy / "worker-ready.json").exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(.05)
            assert (old_busy / "worker-ready.json").exists()
            old_hash = digest(target / "Paperlight.exe")
            assert run(f'"{setup}" /S /D={target}') != 0
            assert digest(target / "Paperlight.exe") == old_hash
            child.kill()
            child.wait(timeout=10)
            child = None
            result["running_legacy_update_blocked"] = True
        # 업데이트는 /D 없이 이전 등록 위치를 자동 선택하는 것도 확인한다.
        install_command = f'"{setup}" /S' if args.upgrade_from else f'"{setup}" /S /D={target}'
        assert run(install_command) == 0, "설치 실패"
        installed = True
        executable = target / "Folio.exe"
        assert registration() == dict(InstallLocation=str(target), DisplayVersion=__version__)
        assert (shortcut_dir / "Folio.lnk").is_file()
        assert (shortcut_dir / "Folio 제거.lnk").is_file()
        expected = {str(p.relative_to(payload)): digest(p) for p in payload.rglob("*") if p.is_file()}
        assert all((target / rel).is_file() and digest(target / rel) == h for rel, h in expected.items())
        result.update(installed_files_match=True, registered_version=True, start_menu=True)
        assert registry_value(r"Software\Paperlight\Capabilities", "ApplicationName") == "Folio"
        assert registry_value(r"Software\RegisteredApplications", "Paperlight") is None
        if legacy_copy:
            assert not (target / "Paperlight.exe").exists() and not legacy_shortcut.exists()
            assert (target / "업데이트-보존.txt").read_text(encoding="utf-8") == "업데이트 전 사용자 파일"
            assert run([str(executable), "--verify-recovery-from", str(legacy_copy / "Paperlight.exe"), str(output / "legacy-recovery")], timeout=120) == 0
            recovery = json.loads((output / "legacy-recovery/recovery-check.json").read_text(encoding="utf-8"))
            assert recovery["passed"] and recovery["legacy_worker"]
            result.update(legacy_install_upgraded=True, legacy_draft_signature_and_pdf_objects_restored=True,
                          legacy_progid_preserved=True, legacy_shortcuts_replaced=True)
        for path, name, value in registration_values(executable):
            assert registry_value(path, name) == value, path
        assert user_choice == (registry_value(choice_path, "ProgId"), registry_value(choice_path, "Hash"))
        result["default_app_candidate_registered_without_changing_default"] = True
        # 실제 사용자 문서·복구 공간과 분리된 합성 문서 시험.
        for flag, folder, report in (("--verify-build", "app", "package-check.json"),
                                     ("--verify-recovery", "recovery", "recovery-check.json"),
                                     ("--verify-workspace", "workspace", "workspace-check.json")):
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
        assert digest(executable) == expected["Folio.exe"]
        result["reinstall_preserves_user_file"] = True
        shutil.copy2(target / "Uninstall.exe", uninstaller_copy)
        assert run(f'"{uninstaller_copy}" /S _?={target}') == 0, "제거 실패"
        installed = False
        assert not registration() and not shortcut_dir.exists()
        for path, name, value in registration_values(executable):
            assert registry_value(path, name) is None, path
        assert user_choice == (registry_value(choice_path, "ProgId"), registry_value(choice_path, "Hash"))
        result["default_app_registration_removed_and_user_choice_preserved"] = True
        assert not (target / "Uninstall.exe").exists()
        assert not any((target / rel).exists() for rel in expected), "프로그램 파일이 남았습니다"
        assert all(p.read_text(encoding="utf-8") == "keep user data" for p in (root_sentinel, nested_sentinel))
        after = {str(p.relative_to(profile)): digest(p) for p in profile.rglob("*") if p.is_file()}
        assert settings_before == settings_snapshot(), "사용자 설정 변경"
        result["user_settings_unchanged"] = True
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
