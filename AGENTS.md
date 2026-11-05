# Paperlight

Windows 개인용 오프라인 PDF 뷰어·편집기. 한국어 UI. 문서 외부 전송 없음.

- Python 3.13, PySide6 Widgets, PyMuPDF. 엔진은 `paperlight/document.py`, UI는 `paperlight/window.py`.
- 개발: `.venv\Scripts\python.exe -m paperlight`
- 검증: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 배포: `.venv\Scripts\python.exe scripts/build.py`
- 팀 배포: 깨끗한 Git 커밋에서 `scripts/release.py`, 설치/제거 QA는 `scripts/verify_installer.py`. 빌드 출력은 `build/distribution`, 배포물은 `release/<버전>`. 실행 중인 `dist/Paperlight`를 덮어쓰지 않는다.
- `assets/`는 배포 예제/아이콘이다. `evidence/`, 타사 바이너리·조사 원본은 Git에 넣지 않는다. NSIS는 현재 사용자 설치이며 제거 시 생성 목록의 파일만 지우고 서명/복구본은 유지한다.
- `workspace.py`는 탭별 MainWindow를 보관한다. 전역 종료는 모든 탭 확인 후 복구본을 정리한다. `instance.py`는 사용자별 QLockFile/로컬 파이프로 탐색기 열기를 전달하며 외부 통신을 하지 않는다.
- `chrome.py`는 탭 바와 문서 스택의 순서를 동기화하고 통합 창 조작부를 제공한다. Windows 가장자리 판정은 물리 픽셀, Qt 배치는 논리 픽셀이다. 창 닫기 버튼도 기존 closeEvent의 트레이/미저장 보호를 거친다.
- `conversion.py`는 별도 프로세스에서 변환하고 전체 성공 후 새 결과만 게시한다. Office 자동화는 직접 연 문서만 닫고 기존 사용자 Office 인스턴스를 종료하지 않는다. 변환 취소는 파일 처리 경계에서 적용한다.
- PDF 연결은 HKCU의 ProgID/Capabilities 후보 등록만 한다. UserChoice/Hash를 직접 바꾸지 않는다. 트레이 숨김은 문서와 복구 타이머를 유지하며 명시적 종료는 미저장 확인을 거친다.
- 기존 본문 수정은 원본 텍스트 제거 후 실제 PDF 텍스트를 재삽입한다. 흰 사각형으로 가리는 구현 금지.
- 모든 편집은 실패 시 되돌린다. 원본은 기본적으로 다른 이름으로 저장하고, PDF 재개방 검증 후 원자적으로 교체한다.
- OCR, 문서 전체 reflow, 인증서 전자서명은 범위 밖. 지원하지 못하는 글꼴·회전 텍스트는 명시한다.
- UI에서 문서 좌표와 화면 좌표, 페이지 회전을 구분한다. 테스트에는 한글, 이미지/도형 보존, 저장/재개방을 포함한다.
- 미적용 입력은 저장에 포함하고 페이지·도구 전환 시 적용/버리기/취소로 보호한다. 미리보기는 현재 페이지만 복제하며 본문·실행 취소 이력을 바꾸지 않는다.
- 읽기 선택은 `selection.py`의 PDF 문자 좌표를 사용하며 문서를 바꾸지 않는다. 복사는 PDF_PERM_COPY를 확인하고 테스트는 실제 사용자 클립보드를 덮어쓰지 않는다.
- 본문 제거 후 주변 문자 좌표도 비교한다. 일부 CFF 내장 글꼴은 glyph 존재만으로 재사용할 수 없으므로 임시 PDF에서 문자 매핑을 확인한다.
- 공개 문서 회귀: `.venv\Scripts\python.exe scripts/check_compatibility.py` (별도 `research/corpus/` 필요, 출처·해시는 `research/corpus-sources.json`). Qt 합성 이벤트 시험을 실제 Windows IME·탐색기 조작으로 보고하지 않는다.
- `objects.py`는 추가 항목을 독립 PDF 콘텐츠 스트림과 검증된 식별 정보로 저장한다. 항목 삭제 시 공유 Resources 사전을 복제하며 다른 페이지를 변경하지 않는다. 본문 제거 작업은 관리 항목을 분리한 뒤 복원해 재편집 정보를 보존한다.
- 배치 편집은 0.5부터 생성한 항목만 지원한다. 저장·재개방, 겹친 항목, 회전/CropBox, 원래 본문·이미지 보존, 실패 시 롤백을 함께 검증한다.
- `recovery.py`는 창별 QLockFile(stale time 0), PDF+입력 상태 단일 복구본, fsync·검증 후 원자 교체를 사용한다. 약 5초마다 변경 시에만 저장하며 읽기 전용 문서는 제외한다. 저장 성공·명시적 버리기에서만 해당 창의 복구본을 정리한다.
- 복구/네이티브 QA는 반드시 `window.data_dir`를 증거 폴더 아래로 격리한다. `.venv\Scripts\python.exe -m paperlight --verify-recovery-native evidence\recovery-check`는 자체 검증용 자식만 강제 종료하고 Windows 복구 창을 표시한다. 사용자 프로세스를 종료하지 않는다.
