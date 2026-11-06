# 문서 작업 공간

Mode: Operate. Platform: Windows native Qt Widgets. Build path: code-led.

## Direction contract

THESIS: 읽는 문서에 시선을 모으는 밝고 미니멀한 편집 도구. 사용자가 직접 선택한 얇은 아이콘과 넓은 문서 영역이 기준이다.

OWN-WORLD: 흰 헤더·패널, 밝은 회청색 캔버스, 파란 선택·저장 상태. Pretendard Variable와 24px 기준의 일관된 선 아이콘. 색상은 theme.py, 위젯 상태는 style.py가 정의한다.

STORY: 파일을 열고 탭으로 이동하며 왼쪽에서 도구를 선택한다. 오른쪽에서 내용을 조정하고 적용한 뒤 상단에서 저장한다. 기존 로컬 처리·복구·변환 동작은 보존한다.

FIRST VIEWPORT: 1400×960과 최소 960×640. Windows 제목줄과 탭은 높이 40px의 한 줄이다. 왼쪽 Folio 워드마크(70px 영역, 21px/600)·문서 탭·파일 추가, 오른쪽 최소화·최대화·닫기. 이름은 통합 바에 한 번만 둔다. Windows UI는 FreeType과 세로 힌팅으로 Pretendard를 렌더링한다. 바로 아래 파일·열기·변환을 왼쪽, 변경 상태·저장을 오른쪽에 모으고 그 아래 문서 도구줄을 구분한다. 왼쪽 112px 도구 목록에는 100×44px 가로형 버튼과 13px 라벨, 진한 파란 선택 상태를 쓴다. 접을 수 있는 페이지 목록, 중앙 PDF, 편집할 때만 나타나는 속성 패널을 유지한다. 속성 제목은 22px, 변환·서명 제목은 26px이다. 입력만 스크롤하고 적용·취소 영역은 흰 하단에 고정한다. 탭 전환 시 편집 상태를 보존하고, 상단 빈 곳은 OS 창 이동, 가장자리는 OS 크기 조절에 연결한다. 장식 애니메이션은 없다.

FORM: 사용자 선택이 밝기와 미니멀 구성을 확정했다. 목록식·어두운 콘솔식·강한 표지판식 대안은 작업 맥락과 선택에 맞지 않아 제외했다. seed:5339022b0cd35148. 별도 이미지 시안은 사용하지 않았다.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

디자인 다듬기: 공통 모서리 4px, 진한 파란 도구 선택, 기본 14px 글꼴과 더 분명한 캔버스·패널 명도 차이를 쓴다. 파일이 없을 때 탐색·저장은 비활성이다. 변환은 라벨이 있는 옵션과 형식별 설명을 유지한다. 속성 입력은 세로 스크롤만 허용하고 960×640에서 적용 버튼이 계속 보인다. 전후 근거는 docs/design-polish/다.
