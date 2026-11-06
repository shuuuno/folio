# Folio 디자인 다듬기

이 문서는 1차 작업 기록이다. 소유자의 추가 요청을 반영한 최신 결과는 [bolder2/README.md](bolder2/README.md)를 따른다. 아래 전후 이미지는 1차 상태로 보존했다.

2026-11-06, 로컬 `design-polish` 브랜치에서 진행했다. 변경 전 기준은 `69b91e5`다. 현재 세션과 현재 모델로 작업했으며 별도 에이전트를 사용하지 않았다. 병합·푸시·배포·게시를 하지 않았다.

## 눈에 보이는 변경

- 세로 아이콘 아래의 작은 글자를 **아이콘 옆의 13px 한국어 도구명**으로 바꿨다. 도구 영역은 68px에서 112px로 넓히고 선택 행은 진한 파란 바탕과 흰 글자·아이콘으로 표시한다.
- **파일·열기·변환을 왼쪽에 모으고**, 변경 상태·저장·설정은 오른쪽에 둔다. 옅은 도구줄, 페이지 목록, 조금 더 짙은 문서 캔버스를 구분한다.
- 기본 글자는 13→14px, 속성 제목은 17→22px, 변환·서명 제목은 17→26px로 키웠다. Pretendard와 기존 FreeType 렌더러를 유지한다.
- 속성 입력을 내용·서식·좌표로 구분하고, **적용·취소·삭제는 흰 하단 영역에 고정**했다. 960×640에서 입력을 스크롤해도 적용 버튼은 움직이지 않는다.
- 기존 ‘PDF 열기’ 빈 상태의 글자를 왼쪽 정렬하고 Ctrl+O를 표시했다. 새 소개 화면은 추가하지 않았다.
- UI 색상·글자 크기를 `theme.py`의 토큰으로 공유하고 편집 입력·도구·변환 옵션의 접근성 이름과 입력 라벨 연결을 보완했다.

밝은 네이티브 문서 작업 공간, 기존 메뉴·도구·탭·검색·편집·서명·변환·복구·저장·트레이 기능을 유지했다. PDF 엔진과 문서 내용·글꼴·색상은 바꾸지 않았다. 화면 안의 `PAPERLIGHT / DOCUMENT STUDIO`는 기존 예제 PDF 내용이다.

## 전후 화면

실제 Windows Qt 위젯을 `grab()`으로 캡처했다. HTML 시안이나 합성 제품 화면이 아니다. 예제 PDF 복사본과 별도 QSettings·복구 경로를 `evidence/design-polish/` 아래 사용했다.

주 비교 화면은 같은 **175% 배율**, 기본 1400×960 논리 픽셀이다. 작은 창은 960×640이다. 변환 창은 700×620→720×660, 서명 창은 커진 제목에 맞춰 실제 크기가 달라진다. PNG는 원래 물리 픽셀을 보존한다.

| 화면 | 변경 전 | 변경 후 |
|---|---|---|
| 빈 문서 | [01-empty-before.png](01-empty-before.png) | [01-empty-after.png](01-empty-after.png) |
| 읽기 | [02-reading-before.png](02-reading-before.png) | [02-reading-after.png](02-reading-after.png) |
| 본문 수정 | [03-edit-before.png](03-edit-before.png) | [03-edit-after.png](03-edit-after.png) |
| 텍스트 추가 | [04-text-before.png](04-text-before.png) | [04-text-after.png](04-text-after.png) |
| 960×640 | [05-compact-before.png](05-compact-before.png) | [05-compact-after.png](05-compact-after.png) |
| 변환 | [06-conversion-before.png](06-conversion-before.png) | [06-conversion-after.png](06-conversion-after.png) |
| 서명 | [07-signature-before.png](07-signature-before.png) | [07-signature-after.png](07-signature-after.png) |
| 배치 편집 | [08-placement-before.png](08-placement-before.png) | [08-placement-after.png](08-placement-after.png) |

## 점검과 결과

[Impeccable audit·critique](audit-critique.md)에서 우선순위를 정하고 bolder·polish 지침에 따라 수정했다. 사전 critique 스냅샷은 `.impeccable/critique/2026-11-06T04-12-36Z__paperlight-window-py.md`에 보관했으며 수정 완료 후 닫았다. 첫 기록이므로 과거 추세는 없다.

[Hallmark 최종 검토](hallmark-check.md)는 소스·실제 화면·대비·창 크기 검증으로 수행했다. **Hallmark의 웹 자동검사는 Qt를 지원하지 않아 실행 불가**였다. 이를 자동검사 통과로 보고하지 않는다. 적용 가능한 기준에서 발견한 보조 글자·입력 테두리 대비와 작은 창의 적용 버튼 배치를 고쳤다.

| 검증 | 결과 |
|---|---|
| 전체 unittest | **86개 통과**, 약 72초 |
| 최종 포커스 보완 후 작업 공간 회귀 | **14개 재검증 통과**, 약 12초 |
| Windows 네이티브 통합 | 통과. 실제 변환 프로세스·두 번째 실행 파일 전달·탭 독립성·트레이 숨김/복귀·창 최대화/최소화/복원 포함 |
| 최소 960×640 | 통과. 가로 넘침 없음, 하단 적용·취소 표시, 스크롤 중 입력 보존과 실제 PDF 적용 확인 |
| 추가 배율 | 실제 DPR **1.0·1.25·1.75**에서 8개 상태씩 캡처·배치 검사 |
| 대비 | **14쌍 통과**. 보조 글자/캔버스 4.92:1, 흰 글자/주요 버튼 6.65:1, 입력 테두리/흰 바탕 3.12:1 |
| 전후 PNG 무결성 | 16개 PNG 확인, 크기·SHA-256을 [verification.json](verification.json)에 기록 |
| 소스 차이 | `git diff --check` 통과 |

실행 명령은 프로젝트 루트 기준이다.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m paperlight --verify-workspace-native evidence\design-polish\workspace-native
.\.venv\Scripts\python.exe scripts\capture_design_polish.py after
.\.venv\Scripts\python.exe scripts\check_design_polish.py
```

추가 배율은 기본 Windows 175% 환경에서 `capture_design_polish.py after --scale 0.571428571` 및 `--scale 0.714285714`로 실제 DPR 1.0·1.25를 확인했다. 다른 환경에서는 배율 곱셈이 달라지므로 `captures.json`의 실제 DPR을 기준으로 읽어야 한다. `before` 명령은 현재 코드로 기존 before 파일을 덮어쓰므로 원본 비교 자료를 보존하려면 변경 전 코드에서만 실행한다.

상세 실행 기록은 `evidence/design-polish/unittest.txt`, `workspace-native/workspace-check.json`, 각 배율 폴더의 `captures.json`에 있다. `evidence/`는 Git 제외 대상이다. 실제 Windows IME 입력, 스크린리더 전체 탐색, 새 설치판 설치는 이번 검증에 포함하지 않았다. 테스트의 Qt 이벤트 시험을 수동 IME 시험으로 간주하지 않는다.

## 도구 설치와 범위

[Impeccable](https://github.com/pbakaus/impeccable) 4.8.0 / 엔진 0.1.18과 [Hallmark](https://github.com/Nutlope/hallmark) 2.0.0을 **이 프로젝트의 `.agents/skills/`에만** 설치했다. 전역 스킬을 설치·수정하지 않았다. 설치 패키지·실행 바이너리·캐시는 Git에서 제외하며 Hallmark 출처와 내용 해시는 `skills-lock.json`에 있다. 다른 앱의 코드·리소스와 Taste Skill은 사용하지 않았다.

```powershell
npx impeccable install --providers=codex --scope=project
npx skills add nutlope/hallmark --agent codex --skill hallmark --yes
```

로컬 설치가 없는 다른 체크아웃에서는 위 명령으로 설치할 수 있다. `.codex/hooks.json`은 설치 도구가 생성한 프로젝트 훅이며, 이번 Qt 검토를 웹 자동검사로 바꾸지는 않는다.

## 선택한 절충

큰 도구명과 입력으로 인해 최소 창에서 좌표 입력을 보려면 세로 스크롤이 필요하다. 대신 적용·취소는 항상 보이며, 문서 공간이 더 필요하면 기존 페이지 목록 접기와 읽기 모드를 사용할 수 있다. 작은 글자와 좁은 도구막대였던 변경 전 화면은 그만큼 문서 폭이 조금 더 넓었다. 배포 파일은 생성하지 않았다.

Grok Bot 보고 내용과 접수 상태는 [grokbot-report.md](grokbot-report.md)에 기록한다.
