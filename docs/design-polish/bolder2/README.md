# Folio 두 번째 bolder·polish

2026-11-06, `design-polish`에서 1차 커밋 `3d16bc2`를 기준으로 더 강한 변화를 적용했다. 현재 세션에서 단독 진행했으며 병합·푸시·배포는 하지 않았다.

세로 도구열을 **가로 리본**으로 옮겨 편집·실행 취소·검색·확대를 그룹으로 나눴다. **푸른 페이지 패널과 진한 선택 면**, 흰 속성 패널과 고정 적용 영역을 구분했다. 제목은 속성 26px·페이지 20px·빈 상태 44px로 키웠고, 문서 캔버스는 더 짙은 회청색과 36단위 여백·부드러운 그림자로 실제 PDF를 드러낸다. 기존 빈 화면의 열기·복구 동작을 전면에 놓았다. 밝은 네이티브 느낌과 기존 기능·단축키를 유지하며 새 소개 페이지·그라데이션·유리 효과는 추가하지 않았다.

Impeccable bolder 후 polish에서 리본 그룹 폭, 페이지 번호 여백, 입력 대비를 보완했다. 가로 리본은 세로 공간을 더 쓰지만 세로 도구열을 없애 문서 폭을 늘린다. 최소 창에서는 속성 입력만 스크롤하며 적용·취소는 항상 보인다.

## 같은 8개 상태 비교

실제 Windows Qt 캡처다. 주 화면 1400×960, 작은 창 960×640 논리 픽셀, 저장 PNG의 배율은 175%다. 사용자 문서 대신 예제 복사본과 격리된 설정·복구 경로를 썼다. 1차 전후 PNG는 변경하지 않았다.

| 상태 | 1차 after | 이번 after |
|---|---|---|
| 빈 문서 | [이전](../01-empty-after.png) | [01-empty-after.png](01-empty-after.png) |
| 읽기 | [이전](../02-reading-after.png) | [02-reading-after.png](02-reading-after.png) |
| 본문 수정 | [이전](../03-edit-after.png) | [03-edit-after.png](03-edit-after.png) |
| 텍스트 추가 | [이전](../04-text-after.png) | [04-text-after.png](04-text-after.png) |
| 960×640 | [이전](../05-compact-after.png) | [05-compact-after.png](05-compact-after.png) |
| 변환 | [이전](../06-conversion-after.png) | [06-conversion-after.png](06-conversion-after.png) |
| 서명 | [이전](../07-signature-after.png) | [07-signature-after.png](07-signature-after.png) |
| 배치 편집 | [이전](../08-placement-after.png) | [08-placement-after.png](08-placement-after.png) |

## 재검증

- 전체 unittest **87개 통과**. 기존 86개에 리본 배치와 Ctrl+F/F3 동작 회귀를 추가했다.
- Windows 네이티브 통합 통과: 변환 자식 프로세스, 두 번째 실행의 파일 전달, 탭 상태, 트레이 복귀, 창 조작, 최소 창 배치.
- 실제 DPR **1.0·1.25·1.75**에서 각각 8개 상태 캡처·배치 검사. 최소 창에서 모든 모드·검색·실행 취소·페이지 목록 버튼과 적용 영역이 잘리지 않는다.
- 대비 **17쌍 통과**. 보조 글자/캔버스 4.99:1, 주요 버튼 글자 6.65:1, 입력 경계/옅은 입력 바탕 3.19:1. 새 8개·이전 8개 PNG의 크기·해시는 [verification.json](verification.json)에 기록했다.
- Hallmark 재검토에서 장식·가짜 콘텐츠·글자 잘림을 점검했다. `sloplint`도 재실행했으나 Qt 소스를 지원하지 않아 검사할 파일이 없다는 오류로 종료했다. **웹 자동검사 통과로 계산하지 않는다.**
- `git diff --check` 통과. 실제 Windows IME·스크린리더 전 경로·설치판 재빌드는 이번 범위에 포함하지 않았다.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m paperlight --verify-workspace-native evidence\design-polish\bolder2\workspace-native
.\.venv\Scripts\python.exe scripts\capture_design_polish.py after --variant bolder2
.\.venv\Scripts\python.exe scripts\check_design_polish.py --variant bolder2
```

상세 실행 결과는 [checks.json](checks.json), 로그·추가 배율 캡처는 `evidence/design-polish/bolder2/`에 있다. 기본 Windows 175% 환경에서 추가 배율 인수는 `--scale 0.571428571`과 `--scale 0.714285714`였으며 실제 DPR은 각 `captures.json`으로 확인했다. Grok Bot 접수 결과는 [보고 기록](grokbot-report.md)에 남겼다.
