"""검토한 Git 소스에서 Velopack 설치판·업데이트 피드·포터블·소스를 만든다."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from paperlight import __version__

VELOPACK_VERSION = "1.2.161"
REPOSITORY = "shuuuno/folio"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bump_version(version):
    if not re.fullmatch(r"\d+\.\d+\.\d+", version) or tuple(map(int, version.split("."))) <= tuple(map(int, __version__.split("."))):
        raise SystemExit("현재보다 높은 major.minor.patch 버전을 지정하세요.")
    path = ROOT / "paperlight" / "__init__.py"
    source = path.read_text(encoding="utf-8")
    path.write_text(source.replace(f'__version__ = "{__version__}"', f'__version__ = "{version}"'), encoding="utf-8")
    print(f"버전 변경: {__version__} → {version}. 검토·커밋한 뒤 release.py를 다시 실행하세요.")


def vpk_command(path=None):
    command = ["dotnet", str(path.resolve())] if path and path.suffix.lower() == ".dll" else [str(path or "vpk")]
    help_text = subprocess.check_output(command + ["--help"], text=True, encoding="utf-8")
    if f"Velopack CLI {VELOPACK_VERSION}," not in help_text:
        raise SystemExit(f"앱과 같은 vpk {VELOPACK_VERSION}이 필요합니다.")
    return command


def publish(release, commit):
    """명시적 --publish에서만 호출한다. 기존 태그·Release는 덮어쓰지 않는다."""
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
        raise SystemExit("게시 전에 작업 트리를 정리하세요.")
    info = json.loads((release / "release-info.json").read_text(encoding="utf-8"))
    if info["commit"] != commit or info["version"] != __version__:
        raise SystemExit("현재 커밋·버전으로 만든 배포물이 아닙니다.")
    for name, digest in info["sha256"].items():
        if Path(name).name != name or sha256(release / name) != digest:
            raise SystemExit("배포물 해시 불일치")
    visibility = subprocess.check_output(["gh", "repo", "view", REPOSITORY, "--json", "visibility",
                                          "--jq", ".visibility"], text=True).strip()
    if visibility != "PUBLIC":
        raise SystemExit("공개 저장소의 피드만 지원합니다. 공개 전환 검사를 먼저 완료하세요.")
    remote = subprocess.check_output(["git", "ls-remote", f"https://github.com/{REPOSITORY}.git", "refs/heads/main"], text=True)
    if not remote or remote.split()[0] != commit:
        raise SystemExit("승인 후 해당 커밋을 원격 main에 반영한 다음 게시하세요.")
    tag = f"v{__version__}"
    exists = subprocess.run(["gh", "release", "view", tag, "--repo", REPOSITORY], capture_output=True)
    if exists.returncode == 0:
        raise SystemExit("같은 버전의 Release가 이미 있습니다. 새 버전을 사용하세요.")
    tag_ref = subprocess.check_output(["git", "ls-remote", f"https://github.com/{REPOSITORY}.git", f"refs/tags/{tag}"], text=True)
    if tag_ref:
        raise SystemExit("같은 태그가 이미 있습니다. 태그를 덮어쓰지 않습니다.")
    artifacts = [str(release / n) for n in sorted(info["sha256"])]
    subprocess.run(["gh", "release", "create", tag, "--repo", REPOSITORY, "--target", commit,
                    "--title", f"Folio {__version__}", "--generate-notes", "--draft",
                    *artifacts, str(release / "release-info.json")], check=True)
    # 자산이 모두 올라간 뒤 공개한다. 다운로드 실패 시 draft가 남는다.
    subprocess.run(["gh", "release", "edit", tag, "--repo", REPOSITORY, "--draft=false", "--latest"], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bump", metavar="VERSION", help="버전만 올리고 종료; 이후 검토·커밋 필요")
    parser.add_argument("--vpk", type=Path, help="고정 버전 vpk 실행 파일 또는 vpk.dll")
    parser.add_argument("--publish", action="store_true", help="사용자 승인 후 기존 배포물만 GitHub Release에 게시")
    args = parser.parse_args()
    if args.bump:
        if args.publish:
            parser.error("--bump와 --publish는 함께 사용할 수 없습니다.")
        bump_version(args.bump)
        return
    status = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=normal"], cwd=ROOT, text=True)
    if status.strip():
        raise SystemExit("배포 전에 검토한 소스를 커밋하세요. 작업 트리가 변경되어 있습니다.")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    release = ROOT / "release" / __version__
    if args.publish:
        publish(release, commit)
        return
    vpk = vpk_command(args.vpk)
    if release.exists() and any(release.iterdir()):
        raise SystemExit("같은 버전 배포 폴더가 이미 있습니다. 검토 후 보관하거나 새 버전을 사용하세요.")
    payload = ROOT / "build" / "distribution" / "Folio"
    subprocess.run([sys.executable, "scripts/build.py", "--dist-dir", str(payload.parent)], cwd=ROOT, check=True)
    if not (payload / "Folio.exe").is_file():
        raise SystemExit("포터블 빌드가 없습니다.")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip() or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != commit:
        raise SystemExit("빌드 중 소스가 변경되었습니다. 새 커밋에서 다시 빌드하세요.")
    (payload / "build-info.json").write_text(json.dumps(dict(version=__version__, commit=commit,
        python=sys.version, velopack=VELOPACK_VERSION), indent=2), encoding="utf-8")
    release.mkdir(parents=True, exist_ok=True)
    subprocess.run(vpk + ["pack", "--packId", "Folio", "--packVersion", __version__,
                         "--packDir", str(payload), "--mainExe", "Folio.exe",
                         "--packTitle", "Folio", "--channel", "win", "--runtime", "win-x64",
                         "--icon", str(ROOT / "assets" / "paperlight.ico"),
                         "--shortcuts", "StartMenuRoot", "--delta", "None",
                         "--outputDir", str(release), "--skip-updates", "--yes"], cwd=ROOT, check=True)
    # vpk가 만든 포터블은 업데이트 가능한 구조다. 기존 포터블 계약에 맞게
    # 설치 정보가 없는 원래 폴더 ZIP을 배포하고 vpk 포터블은 제외한다.
    (release / "Folio-win-Portable.zip").unlink(missing_ok=True)
    portable_name = f"Folio-{__version__}-Portable"
    shutil.make_archive(str(release / portable_name), "zip", payload.parent, payload.name)
    catalog_path = release / "assets.win.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    for asset in catalog:
        if asset["Type"] == "Portable":
            asset["RelativeFileName"] = portable_name + ".zip"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    source = release / f"Folio-{__version__}-Source.zip"
    subprocess.run(["git", "archive", "--format=zip", f"--prefix=Folio-{__version__}/",
                    "-o", str(source), commit], cwd=ROOT, check=True)
    artifacts = sorted(p for p in release.iterdir() if p.is_file())
    digests = {p.name: sha256(p) for p in artifacts}
    (release / "SHA256SUMS.txt").write_text("".join(f"{digest}  {name}\n" for name, digest in digests.items()), encoding="utf-8")
    digests["SHA256SUMS.txt"] = sha256(release / "SHA256SUMS.txt")
    (release / "release-info.json").write_text(json.dumps(dict(version=__version__, commit=commit,
        velopack=VELOPACK_VERSION, sha256=digests), indent=2), encoding="utf-8")
    print(f"배포 파일: {release}\n소스 커밋: {commit}")


if __name__ == "__main__":
    main()
