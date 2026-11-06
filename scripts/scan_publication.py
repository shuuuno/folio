"""전체 Git 이력의 비밀값과 이메일·전화번호·주민번호 후보를 검사한다."""
import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone": re.compile(r"(?<!\d)(?:\+82[- .]?|0)1[016789][- .]?\d{3,4}[- .]?\d{4}(?!\d)"),
    "resident_number": re.compile(r"(?<![A-Za-z0-9])\d{6}[- ]?[1-4]\d{6}(?![A-Za-z0-9])"),
}


def privacy_hits(text):
    hits = {}
    for kind, pattern in PATTERNS.items():
        matches = pattern.findall(text)
        if kind == "email":
            # RFC 예제 주소와 GitHub의 비공개 커밋 주소는 개인정보가 아니다.
            matches = [m for m in matches if not m.lower().endswith(
                ("@example.com", "@example.org", "@example.net", "@users.noreply.github.com"))]
        if matches:
            hits[kind] = len(matches)
    return hits


def scan(output, gitleaks):
    output.mkdir(parents=True, exist_ok=True)
    with (output / "gitleaks.log").open("w", encoding="utf-8") as log:
        result = subprocess.run([str(gitleaks), "git", str(ROOT), "--log-opts=--all --full-history",
            "--redact=100", "--report-format", "json", "--report-path", str(output / "gitleaks.json")],
            stdout=log, stderr=subprocess.STDOUT)
    if result.returncode not in (0, 1):
        raise SystemExit("Gitleaks 검사 실패. 공개하지 않습니다.")
    objects = subprocess.check_output(["git", "rev-list", "--objects", "--all"], cwd=ROOT).splitlines()
    findings = []
    count = 0
    for record in objects:
        oid, _, name = record.partition(b" ")
        kind = subprocess.check_output(["git", "cat-file", "-t", oid], cwd=ROOT).strip()
        if kind not in (b"blob", b"commit", b"tag"):
            continue
        raw = subprocess.check_output(["git", "cat-file", "-p", oid], cwd=ROOT)
        count += 1
        text = raw.decode("utf-8", errors="replace")
        # 배포 예제 PDF의 보이는 글자도 검사한다. 파싱 실패는 검사 누락으로 처리한다.
        if name.lower().endswith(b".pdf"):
            import fitz
            with fitz.open(stream=raw, filetype="pdf") as doc:
                text += "\n".join(page.get_text() for page in doc)
        hits = privacy_hits(text)
        if hits:
            findings.append(dict(object=oid.decode(), path=name.decode("utf-8", errors="replace")
                                 or f"<{kind.decode()}>", candidates=hits))
    report = dict(commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  refs=subprocess.check_output(["git", "show-ref"], cwd=ROOT, text=True).splitlines(),
                  objects_scanned=count, secret_scan_exit=result.returncode,
                  privacy_findings=findings, clean=result.returncode == 0 and not findings)
    (output / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(dict(objects_scanned=count, secret_scan_exit=result.returncode,
                         privacy_candidate_objects=len(findings), clean=report["clean"]), ensure_ascii=False))
    return 0 if report["clean"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gitleaks", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "evidence" / "publication-scan")
    args = parser.parse_args()
    raise SystemExit(scan(args.output.resolve(), args.gitleaks.resolve()))
