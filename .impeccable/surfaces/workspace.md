# 문서 작업 공간

Mode: Operate. Platform: Windows native Qt Widgets. Build path: code-led.

## Direction contract

THESIS: 읽는 문서에 시선을 모으는 밝고 미니멀한 편집 도구. 사용자가 직접 선택한 얇은 아이콘과 넓은 문서 영역이 기준이다.

OWN-WORLD: 흰 헤더·패널, 밝은 회청색 캔버스, 파란 선택·저장 상태. Pretendard Variable와 24px 기준의 일관된 선 아이콘. 색상은 theme.py, 위젯 상태는 style.py가 정의한다.

STORY: 파일을 열고 탭으로 이동하며 상단 리본에서 도구를 선택한다. 왼쪽은 페이지 탐색, 오른쪽은 내용 조정이다. 적용한 뒤 상단에서 파일을 저장한다. 기존 로컬 처리·복구·변환 동작은 보존한다.

FIRST VIEWPORT: 1400×960과 최소 960×640. Windows 제목줄과 탭은 높이 40px의 한 줄이며 Folio 이름은 한 번만 표시한다. 그 아래 파일·열기·변환은 왼쪽, 변경 상태·저장은 오른쪽이다. 세로 도구열을 없애고 높이 88px 가로 리본에 72×68px 도구 버튼 5개, 실행 취소·다시 실행, 검색, 확대·페이지 목록 그룹을 놓는다. 푸른 페이지 패널은 192~224px, 흰 속성 패널은 288~340px이며 중앙 문서가 나머지 폭을 쓴다. 속성 제목은 26px, 페이지 제목은 20px, 변환·서명 제목은 28px이다. 입력만 스크롤하고 적용·취소는 연한 선택색 하단에 고정한다. 캔버스의 명도와 36단위 여백으로 실제 PDF 경계를 드러낸다. 빈 상태는 흰 작업 면의 44px 제목과 실제 열기·복구 동작을 제공한다. FreeType·탭 상태 보존·OS 창 이동과 크기 조절은 유지한다. 장식 애니메이션은 없다.

FORM: 사용자 선택이 밝기와 미니멀 구성을 확정했다. 목록식·어두운 콘솔식·강한 표지판식 대안은 작업 맥락과 선택에 맞지 않아 제외했다. seed:5339022b0cd35148. 별도 이미지 시안은 사용하지 않았다.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

두 번째 bolder·polish: 소유자가 1차 변경보다 더 큰 배치·위계 변화를 요청해 리본과 패널 구조를 바꿨다. 공통 모서리 4px, 진한 파란 도구·페이지 선택, 기본 14px 글꼴을 유지한다. 파일이 없을 때 탐색·저장은 비활성이다. 변환의 실제 옵션과 안내를 유지한다. 960×640에서 리본과 적용 버튼이 계속 보인다. 최신 근거는 docs/design-polish/bolder2/다.
