# PDF 글꼴 선택

소유자의 2026-11-06 13:52 KST 승인에 따라 `design-polish`에서 구현했다. [텍스트 도구 화면](font-picker.png)은 실제 Windows Qt 창의 175% 배율 캡처이며 선택 글꼴과 한글 미리보기를 함께 보여 준다. 기존 bolder2 비교 화면은 보존했다.

## 사용

텍스트 추가·본문 수정·추가 텍스트의 배치 편집 패널에서 **글꼴**을 선택한다. Windows 시스템·사용자 글꼴 폴더와 Fonts 레지스트리를 읽어 TTF·OTF·TTC·OTC의 서체를 나열한다. 앱 실행 중 한 번 목록을 읽으며 새로 설치한 글꼴은 앱을 다시 열면 반영된다.

새 텍스트의 초기 기본은 **맑은 고딕**이다. 선택한 마지막 서체는 앱 데이터 폴더의 `preferences.ini`에 기억하며 다음 텍스트 추가에 적용한다. 저장된 서체가 사라졌다면 맑은 고딕으로 돌아간다. 본문 선택은 **원본 글꼴 유지**, 추가 항목 선택은 **내장 글꼴 유지**가 기본이므로 기존 문서를 열었다고 글꼴을 바꾸지 않는다. 다른 글꼴을 직접 고르면 그 서체로 재삽입한다.

선택 글꼴에 입력 문자가 없거나 임시 PDF의 문자 매핑 검증을 통과하지 못하면 적용하지 않는다. 특히 모든 설치 글꼴이 한글을 지원하는 것은 아니다. 미리보기의 안내를 보고 다른 서체를 선택하면 된다. 글꼴만 바꿔도 미적용 변경으로 보호하며 복구본에 선택을 포함한다. 선택 글꼴이 사라지거나 내장 금지로 바뀐 복구 입력은 현재 문서를 교체하기 전에 복구를 중단하고 복구본을 유지한다.

## 임베딩 범위

[Microsoft OpenType OS/2 fsType 규격](https://learn.microsoft.com/en-us/typography/opentype/spec/os2#fstype)을 기준으로 편집용 임베딩 권한을 검사한다.

| fsType | 처리 |
|---|---|
| 0, 설치 가능 | 허용, 전체 글꼴 내장 |
| 0x0008, 편집 가능 | 허용, 전체 글꼴 내장 |
| 0x0002, 제한됨 | 목록과 적용에서 제외 |
| 0x0004, 보기/인쇄 전용 | 편집용 출력이므로 제외 |
| 0x0100, 서브셋 금지 | 위의 허용 권한과 함께 설정된 경우 전체 글꼴을 내장해 준수 |
| 0x0200, 비트맵만 허용 | 윤곽 글꼴 내장이 필요하므로 제외 |
| 권한 정보 없음·미상 비트·잘못된 조합 | 확인 불가로 제외 |

선택 후 파일이 바뀌었을 수 있으므로 **적용 직전에도 권한을 재검사**한다. TTC/OTC는 서체별로 검사하고 선택한 서체 전체를 추출한다. 글리프 검사와 기존 roundtrip probe를 모두 거친다. 선택 글꼴은 PDF 리소스에 실제로 내장하며, 흰 사각형이나 UI 글꼴 설정으로 대체하지 않는다. 전체 내장이므로 파일 크기는 커질 수 있다.

추가 항목은 저장·재개방·이동·내용 수정 및 주변 본문 수정 후에도 내장 서체를 재사용한다. PDF에 로컬 글꼴 파일 경로를 기록하지 않는다. 원본 글꼴 유지의 기존 CFF 매핑 검증과 맑은 고딕 대체 동작은 유지한다. UI의 Pretendard와 PDF 글꼴은 서로 별개다.

## 검증

- 전체 unittest **99개 통과**. 글꼴 관련 9개는 임베딩 권한, 변경 직전 재검사, TTC 개별 서체, 서브셋 금지 전체 내장, 한글 저장·재개방·재편집, 글꼴 변경 미리보기·실행 취소, 글리프/roundtrip 실패 롤백, 잘못된 메타데이터를 검사한다. UI 테스트는 마지막 선택 기억·글꼴만 바꾼 입력 보호를, 복구 테스트는 선택 서체 복원을 확인한다.
- Windows 네이티브 및 검증용 실행 파일에서 기본 맑은 고딕, 선택 서체 실제 내장, 한글 추출, 재개방 후 서체 유지, 마지막 선택 기억, 960×640의 선택기·적용 버튼 접근을 확인했다. 이 PC의 허용 서체 항목은 529개다.
- 기존 네이티브 통합, 100%·125%·175%의 8개 상태 배치, 대비 17쌍, 기존 비교 PNG 무결성, `git diff --check`를 재검증했다. Hallmark 웹 도구는 Qt 미지원 오류로 종료하며 자동 통과로 취급하지 않는다.
- 검증 빌드는 `build/font-picker-distribution/Folio`에 격리했다. 기존 `dist/` 실행 파일과 설치판을 덮어쓰지 않았으며 배포·병합·푸시는 하지 않았다. 실제 수동 IME·스크린리더 전 경로·설치/제거 QA는 이번 검증에 포함하지 않았다.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m paperlight --verify-font-picker-native evidence\font-picker\native
.\.venv\Scripts\python.exe -m paperlight --verify-workspace-native evidence\font-picker\workspace-native
.\.venv\Scripts\python.exe scripts\build.py --dist-dir build\font-picker-distribution
```

이 기능을 위해 `fonttools==4.68.0`을 프로젝트 가상환경에 추가했다. 라이선스는 MIT이며 빌드에 고지 파일과 동적 글꼴 테이블 모듈을 포함한다. 상세 실행 로그는 `evidence/font-picker/`, 주요 결과는 [font-picker-checks.json](font-picker-checks.json)에 있다. [Grok Bot 보고 기록](font-picker-grokbot.md)도 함께 보관한다.
