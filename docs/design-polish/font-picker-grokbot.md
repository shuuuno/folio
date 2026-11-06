# Grok Bot 보고

Folio 글꼴 선택기 구현 완료. 소유자의 2026-11-06 13:52 KST 승인 범위이며 D:\project_dy\paperlight의 design-polish 로컬 브랜치에서 현재 세션으로 진행했다. Windows 설치 글꼴을 나열하고 OS/2 fsType 제한·보기/인쇄 전용·비트맵 전용·권한 확인 불가 서체는 제외한다. 적용 직전에도 권한을 재검사하며 서브셋 금지 서체는 전체 내장한다.

새 텍스트 기본 맑은 고딕, 마지막 선택 기억, 본문 원본 글꼴 유지와 추가 항목 내장 글꼴 유지를 제공한다. 선택한 글꼴은 실제 PDF에 내장하며 한글 글리프와 roundtrip probe를 통과해야 적용한다. 저장·재개방·배치 재편집·주변 본문 수정에서도 서체를 보존하고, 글꼴만 바꾼 입력과 복구에도 선택을 반영했다.

전체 테스트 99개, 글꼴 경계값 테스트 9개, Windows 네이티브 통합과 격리된 검증 실행 파일, 960×640, 100%·125%·175% 배치, 대비 17쌍과 기존 PNG 무결성 검사를 수행했다. Hallmark 웹 도구는 Qt 미지원으로 자동 통과가 아니며 실제 IME·스크린리더 전체 경로·설치/제거 QA는 미수행이다.

화면은 docs\design-polish\font-picker.png, 설명은 font-picker.md, 주요 결과는 font-picker-checks.json이다. 검증 빌드는 build\font-picker-distribution\Folio에 격리했으며 기존 dist를 덮어쓰지 않았다. design-polish에만 커밋하며 병합·푸시·배포는 하지 않는다.

## 접수 상태

- 메시지: `msg_2b5b8ca1e437`
- `--source codex --timeout 60`, 종료 코드 0: 회신 수신.
- 회신: “Folio 글꼴 선택기 완료 보고 잘 받았습니다.” 로컬 브랜치만 사용하고 병합·푸시·배포가 없다는 범위도 확인했다.
