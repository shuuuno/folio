"""기존 설치가 없는 Windows 계정에서 Velopack 설치·실행·제거를 검사한다."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import winreg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from paperlight import __version__
from paperlight.windows_integration import registration_values
from scripts.verify_installer import digest, registry_value, settings_snapshot, registration

KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Folio"


def run(command, timeout=180):
    subprocess.run([str(c) for c in command], check=True, timeout=timeout,
                   creationflags=subprocess.CREATE_NO_WINDOW)


def preflight():
    menu = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs"
    if (registration() or registration(winreg.KEY_WOW64_64KEY)
            or registry_value(KEY, "DisplayVersion") is not None
            or any((menu / p).exists() for p in ("Folio.lnk", "Folio", "Paperlight"))
            or any(registry_value(r"Software\RegisteredApplications", name) is not None
                   for name in ("Folio", "Paperlight"))):
        raise SystemExit("기존 Folio/Paperlight 설치·바로가기·후보 등록이 있어 중단합니다. 깨끗한 Windows 계정에서 검증하세요.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup", type=Path, default=ROOT / "release" / __version__ / "Folio-win-Setup.exe")
    args = parser.parse_args()
    preflight()
    setup = args.setup.resolve(strict=True)
    output = ROOT / "evidence" / ("installer-" + uuid.uuid4().hex[:8])
    output.mkdir(parents=True)
    target = (ROOT / "build" / "installer-qa" / output.name / "한글 경로 Folio").resolve()
    assert target.is_relative_to((ROOT / "build" / "installer-qa").resolve()) and not target.exists()
    profile = Path(os.environ["LOCALAPPDATA"]) / "Paperlight/Paperlight"
    before = {str(p.relative_to(profile)): digest(p) for p in profile.rglob("*") if p.is_file()}
    settings = settings_snapshot()
    choice = r"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.pdf\UserChoice"
    user_choice = (registry_value(choice, "ProgId"), registry_value(choice, "Hash"))
    result = dict(passed=False, version=__version__, install_path=str(target))
    try:
        run([setup, "--silent", "--installto", target, "--log", output / "setup.log"])
        executable = target / "current" / "Folio.exe"
        assert executable.is_file() and (target / "Update.exe").is_file()
        assert registry_value(KEY, "DisplayVersion") == __version__
        shortcut = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Folio.lnk"
        assert shortcut.is_file()
        for path, name, value in registration_values(executable):
            assert registry_value(path, name) == value, path
        assert user_choice == (registry_value(choice, "ProgId"), registry_value(choice, "Hash"))
        result.update(installed=True, version_registered=True, pdf_candidate_registered=True, start_menu=True)
        for flag, folder, report in (("--verify-build", "app", "package-check.json"),
                                     ("--verify-recovery", "recovery", "recovery-check.json"),
                                     ("--verify-workspace", "workspace", "workspace-check.json")):
            run([executable, flag, output / folder])
            data = json.loads((output / folder / report).read_text(encoding="utf-8"))
            assert data["passed"] and data["frozen"], report
        result["installed_app_and_recovery"] = True
        run([target / "Update.exe", "--silent", "--rootDir", target, "uninstall"])
        assert not executable.exists() and not shortcut.exists()
        assert registry_value(KEY, "DisplayVersion") is None
        for path, name, _ in registration_values(executable):
            assert registry_value(path, name) is None, path
        assert user_choice == (registry_value(choice, "ProgId"), registry_value(choice, "Hash"))
        after = {str(p.relative_to(profile)): digest(p) for p in profile.rglob("*") if p.is_file()}
        assert settings == settings_snapshot(), "사용자 설정 변경"
        assert before == after, "사용자 프로필 변경"
        result.update(uninstalled=True, user_profile_unchanged=True, user_choice_unchanged=True, passed=True)
    finally:
        # 이 검증이 만든 경로의 제거기만 사용한다. 사용자 설치는 사전 검사로 보호한다.
        if (target / "current/Folio.exe").exists() and (target / "Update.exe").exists():
            cleanup = subprocess.run([str(target / "Update.exe"), "--silent", "--rootDir", str(target), "uninstall"],
                                     timeout=90, creationflags=subprocess.CREATE_NO_WINDOW)
            result["cleanup_exit"] = cleanup.returncode
        (output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
