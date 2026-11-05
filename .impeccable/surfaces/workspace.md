# 문서 작업 공간

Mode: Operate. Platform: Windows native Qt Widgets. Build path: code-led.

## Direction contract

THESIS: 읽는 문서에 시선을 모으는 밝고 미니멀한 편집 도구. 사용자가 직접 선택한 얇은 아이콘과 넓은 문서 영역이 기준이다.

OWN-WORLD: 흰 헤더·패널, 밝은 회청색 캔버스, 파란 선택·저장 상태. Pretendard Variable와 24px 기준의 일관된 선 아이콘. 색상은 theme.py, 위젯 상태는 style.py가 정의한다.

STORY: 파일을 열고 탭으로 이동하며 왼쪽에서 도구를 선택한다. 오른쪽에서 내용을 조정하고 적용한 뒤 상단에서 저장한다. 기존 로컬 처리·복구·변환 동작은 보존한다.

FIRST VIEWPORT: 1400×960과 최소 1050×760. 상단 단일 헤더 오른쪽 열기·변환·저장, 아래 문서 탭. 왼쪽 76px 도구막대, 접을 수 있는 페이지 목록, 중앙 PDF, 편집할 때만 오른쪽 속성 패널. 문서 전환 시 편집 상태를 보존하는 기존 탭 동작이 핵심 상호작용이다. 장식 애니메이션 없이 즉시 반응한다.

FORM: 사용자 선택이 밝기와 미니멀 구성을 확정했다. 목록식·어두운 콘솔식·강한 표지판식 대안은 작업 맥락과 선택에 맞지 않아 제외했다. seed:5339022b0cd35148. 별도 이미지 시안은 사용하지 않았다.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
