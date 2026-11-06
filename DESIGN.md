---
name: Folio
description: 문서에 시선을 모으는 밝고 미니멀한 Windows PDF 작업 공간
colors:
  ink: "#202A3B"
  muted: "#526078"
  accent: "#3451C8"
  accent-hover: "#2B44AE"
  accent-pressed: "#243A96"
  selected: "#E8EDFC"
  border: "#D7DFEA"
  control-border: "#8593A8"
  canvas: "#DCE3ED"
  surface: "#FFFFFF"
  chrome: "#F3F6FA"
  rail: "#EBF0F7"
  hover: "#E9EEF6"
  pressed: "#DCE4F0"
  focus-button: "#3451C8"
  focus-input: "#3451C8"
  disabled: "#929DAF"
  disabled-primary-bg: "#E0E6F2"
  disabled-primary-ink: "#7785A2"
  danger: "#A13644"
  danger-hover: "#FCECEF"
  selection-text: "#DCE5FF"
  selection-ink: "#24314C"
  window-bar: "#E8EDF5"
  document-tab-hover: "#DCE4F0"
  window-close-hover: "#FBDDE0"
typography:
  wordmark:
    fontFamily: "Pretendard Variable, Malgun Gothic"
    fontSize: "21px"
    fontWeight: 600
  headline:
    fontFamily: "Pretendard Variable, Malgun Gothic"
    fontSize: "32px"
    fontWeight: 600
  title:
    fontFamily: "Pretendard Variable, Malgun Gothic"
    fontSize: "22px"
    fontWeight: 600
  introduction:
    fontFamily: "Pretendard Variable, Malgun Gothic"
    fontSize: "16px"
  body:
    fontFamily: "Pretendard Variable, Malgun Gothic"
    fontSize: "14px"
  label:
    fontFamily: "Pretendard Variable, Malgun Gothic"
    fontSize: "13px"
  compact:
    fontFamily: "Pretendard Variable, Malgun Gothic"
    fontSize: "12px"
  dialog:
    fontFamily: "Pretendard Variable, Malgun Gothic"
    fontSize: "26px"
    fontWeight: 600
  editor:
    fontFamily: "Pretendard Variable, Malgun Gothic"
    fontSize: "15px"
rounded:
  compact: "4px"
  item: "5px"
  control: "4px"
  list: "4px"
spacing:
  control: "8px"
  header-gap: "8px"
  inspector: "16px"
components:
  wordmark:
    textColor: "{colors.ink}"
    typography: "{typography.wordmark}"
    width: "70px"
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "9px 18px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-primary-active:
    backgroundColor: "{colors.accent-pressed}"
  button-primary-disabled:
    backgroundColor: "{colors.disabled-primary-bg}"
    textColor: "{colors.disabled-primary-ink}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "6px 10px"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "6px 10px"
  button-danger:
    backgroundColor: "transparent"
    textColor: "{colors.danger}"
    rounded: "{rounded.control}"
    padding: "6px 10px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "7px"
  search:
    backgroundColor: "{colors.chrome}"
    rounded: "{rounded.control}"
    padding: "7px 8px"
    minWidth: "140px"
    maxWidth: "220px"
  tool-selected:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "8px 6px"
    width: "100px"
    height: "44px"
  document-tab:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "4px 4px 0 0"
    padding: "6px 12px"
  document-tab-selected:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.selection-ink}"
  window-bar:
    backgroundColor: "{colors.window-bar}"
    height: "40px"
  window-control:
    backgroundColor: "transparent"
    rounded: "0px"
    padding: "0px"
    width: "46px"
    height: "40px"
---

# Design System: Folio

## Overview

**Creative North Star: "문서에 시선을 모으는 밝은 작업 공간"**

사용자가 선택한 밝고 미니멀한 화면, 얇은 선 아이콘, 넓은 문서 영역을 유지한다. 흰 도구 영역과 회청색 캔버스를 구분하고 파란색으로 선택과 주요 실행을 표시한다. 한국어를 읽기 편하게 배치하며 장식보다 문서와 편집 상태가 먼저 보이게 한다.

**Key Characteristics:**

- 흰 패널과 밝은 회청색 문서 바탕.
- 한 계열 글꼴과 얇은 기하학 선 아이콘.
- 선택·저장·적용을 구분하는 파란 상태색.
- 즉시 반응하는 Windows 네이티브 위젯.

표시 제품명은 Folio이며 창 제목·트레이·실행 파일·설치·시작 메뉴·기본 앱에도 같은 이름을 쓴다. 기존 데이터·IPC·설치 식별자인 Paperlight와 Python 패키지 경로는 유지한다. PDF 안의 기존 콘텐츠는 브랜드 변경 대상이 아니다.

기준 구현은 `paperlight/theme.py`, `style.py`, `icons.py`, `chrome.py`, `workspace.py`, `window.py`와 앱 시작점 `__main__.py`다. 이 문서는 구현된 재사용 규칙을 기록한다. 화면별 구성은 `.impeccable/surfaces/workspace.md`에 둔다. 최신 전후 화면과 검사 결과는 `docs/design-polish/`다. `.impeccable/design.json`의 소스 해시·HTML 표본은 이번 변경 전 기록이다.

## Colors

차분한 회청색 중립색 위에 선명한 파란색 한 계열을 사용한다. 정확한 값은 앞부분 토큰을 따른다.

- **Primary:** `accent`는 저장·적용 버튼과 선택된 도구, `accent-hover`·`accent-pressed`는 실행 상태다. `selected`는 선택 배경이다.
- **Neutral:** `ink`는 기본 글자, `muted`는 보조 설명이다. `surface`는 패널, `chrome`은 주변 영역, `canvas`는 PDF 바깥 배경, `border`는 영역 경계다.
- **상태:** `danger`는 삭제 동작, `disabled` 계열은 사용 불가 상태에 쓴다. 버튼과 입력의 포커스 테두리는 별도 토큰이다. 본문 선택은 `selection-text`와 `selection-ink`를 쓴다.

## Typography

배포에 포함한 `assets/fonts/PretendardVariable.ttf`를 Qt에 등록한다. 스타일의 대체 글꼴은 맑은 고딕이다. UI 글꼴과 PDF 내부의 편집 글꼴은 별개다.

Windows에서 Qt 플랫폼이 미지정 또는 `windows`일 때 QApplication 생성 인수에 `windows:fontengine=freetype`를 지정한다. 기본 14px 글꼴에 `PreferAntialias`와 `PreferVerticalHinting`을 적용한다. 이는 앱 안의 글자 렌더링 설정이며 Windows 전체 글꼴 설정은 바꾸지 않는다. HTML/CSS 표본은 이 네이티브 렌더러의 결과를 재현하거나 검증하지 않는다.

`wordmark`는 제목줄의 Folio 라벨, `headline`은 기존 빈 화면 제목, `title`은 속성 패널 제목, `dialog`는 변환·서명 제목, `editor`는 편집 입력, `introduction`은 빈 화면 안내, `body`는 메뉴·탭·버튼, `label`은 도구명·보조 설명, `compact`는 상태 표시줄에 쓴다. 통합 작업 창의 브랜드 라벨은 한 번만 표시한다. 주요 버튼·제목·속성 캡션은 굵기 600이다. 행간과 자간은 Qt의 글꼴 계측을 따른다. 정확한 값의 원본은 `theme.py`의 `TYPE`다.

## Layout

Qt Widgets의 레이아웃과 분할 창을 사용한다. 기본 창은 작업 표시줄을 제외한 화면 안에서 최대 1400×960, 최소 창은 960×640이다. 최상단은 Windows 제목줄과 문서 탭을 합친 `window-bar`다. 왼쪽 8px 여백부터 고정 너비의 Folio 워드마크, 문서 탭, 바로 옆 34×32px 파일 추가 버튼, 빈 이동 영역, 오른쪽 최소화·최대화·닫기 순으로 놓인다. 워드마크는 라벨 안에서 가로·세로 가운데 정렬한다. 파일 추가 뒤에는 최소 80px의 빈 영역을 남긴다. 별도 제품명 배너나 OS 제목줄을 중복 표시하지 않는다.

그 아래 파일·열기·변환을 왼쪽에 모으고 변경 상태·저장·설정을 오른쪽에 둔다. 헤더 내부 여백은 왼쪽 16·위아래 9·오른쪽 12px이며 요소 간격은 `header-gap`이다. 문서 도구줄은 옅은 바탕으로 분리한다.

왼쪽 도구막대는 112px, 아이콘 옆에 글자가 있는 도구 행은 100×44px이다. 읽기와 편집 도구 사이 간격을 둔다. 페이지 목록은 155~180px, 오른쪽 속성 패널은 288~340px이며 중앙 문서가 남는 너비를 사용한다. 초기 분할 크기는 160·850·320px이며 Qt가 실제 창 크기에 맞춰 배분한다. 페이지 목록을 접고 읽기 모드에서 속성 패널을 숨겨 문서 영역을 확보한다. 속성 입력 영역은 여백 20·24·20·20px, 세로 간격 12px이며 세로로 스크롤한다. 적용·취소·삭제와 저장 안내는 흰 하단 영역에 고정한다.

웹·모바일 중단점은 없다. 이 치수는 Qt 논리 픽셀 기준이며 Windows 배율과 글꼴 계측의 영향을 받는다. 탭의 긴 이름은 가운데를 생략하고 툴팁으로 전체 경로를 제공한다. 탭이 많으면 Qt 스크롤 버튼을 사용한다.

## Elevation & Depth

패널은 색면과 얇은 경계선으로 나눈다. PDF 페이지에만 부드러운 그림자를 둔다. 실제 Qt 효과는 blurRadius 18, offset (0, 4), QColor(32, 42, 59, 28)이다. CSS 그림자 수치와 동일한 렌더링을 보장하지 않는다. 문서 주변 장면 여백은 각 26 문서 단위다. 장식용 이동·확대·전환 애니메이션은 없다.

## Shapes

버튼과 입력은 `control`, 탭 닫기·작은 상태 조작부는 `compact`, 목록 항목은 `item`, 일반 목록은 `list` 모서리를 쓴다. 문서 탭은 위쪽 두 모서리만 둥글고 아래쪽은 곧다. 큰 패널과 창 조작 버튼은 곧은 경계를 유지한다. 일반 경계선은 1px이며 문서 탭과 창 조작 버튼에는 테두리가 없다.

아이콘은 `icons.py`의 24px 격자에서 1.7 두께, 둥근 선 끝·연결로 직접 그린다. 16·20·24·32px 변형을 2배 픽셀과 devicePixelRatio 2로 만든다. 도구막대에는 22px, 일반 아이콘 버튼에는 20px 표시 크기도 사용한다. 글자 기호나 외부 아이콘 폰트로 바꾸지 않는다. 스핀 상하 화살표는 `assets/ui`의 SVG다.

## Components

- **워드마크:** `QLabel`로 그리는 Folio 글자이며 이미지 로고가 아니다. `wordmark`의 글꼴·너비와 `ink` 색을 사용한다. 마우스 이벤트를 통과시켜 제목줄의 창 이동을 방해하지 않는다.
- **주요 버튼:** 파란 바탕·흰 글자. hover, pressed, disabled 색을 각각 갖고 키보드 포커스는 테두리로 표시한다.
- **일반·보조·삭제 버튼:** 일반은 투명, 보조는 흰 바탕과 경계선, 삭제는 붉은 글자다. 일반 hover·pressed는 중립색, 삭제 hover는 연한 붉은 배경이다. 비활성 상태는 흐린 글자로 구분한다.
- **입력:** 흰 바탕과 `control-border` 경계선, hover 시 경계 강화, focus 시 2px 파란 테두리다. 포커스에서 안쪽 여백을 1px 줄여 전체 크기를 유지한다. 검색 입력은 평상시 `chrome`, focus 시 흰 바탕이다. 스핀 입력은 오른쪽 상하 버튼을 유지한다.
- **도구 탐색:** 아이콘 옆에 13px 한국어 이름을 보인다. 선택 상태는 진한 파란 바탕·흰 글자와 아이콘·굵기 600으로 구분한다. 아이콘 전용 동작에는 툴팁과 접근성 이름을 둔다.
- **문서 탭:** `window-bar` 위에 비선택 탭을 투명하게 놓고 선택 탭은 흰 바탕으로 연결한다. 위쪽 여백 5px·오른쪽 여백 3px, 최소 너비 110px·최대 210px이다. 비선택 hover에는 `document-tab-hover`를 쓴다. 닫기는 별도 선 아이콘 버튼이다. 저장하지 않은 변경은 탭의 `*`와 헤더 상태 문구로 표시한다.
- **통합 창 조작부:** `FramelessWindowHint`로 기존 OS 제목줄을 대신한다. 빈 상단 영역의 드래그는 `startSystemMove`, 더블클릭은 최대화·복원에 연결한다. 창 조작 아이콘은 16px이며 최대화 상태에서는 복원 아이콘·접근성 이름으로 바뀐다. 닫기 hover는 `window-close-hover`다. 가장자리 크기 조절은 Win32 `WM_NCHITTEST`와 물리 화면 좌표를 사용하고, 감지 폭은 `round(6 × devicePixelRatioF())`이다. 최대화·전체 화면에서는 이 감지를 하지 않는다. 닫기는 기존 창 종료 처리로 연결해 트레이 설정과 미저장 입력 보호를 유지한다.
- **목록·메뉴:** 선택 배경은 연한 파란색이다. 페이지 썸네일의 선택에는 별도 테두리를 더한다. 메뉴의 비활성 항목은 흐린 글자다.
- **문서 작업:** 적용과 파일 저장은 서로 다른 동작으로 설명한다. 미적용 입력 확인·저장 대화상자·복구 안내는 네이티브 동작을 유지한다. 별도 카드·칩 디자인은 만들지 않는다.

`.impeccable/design.json`의 HTML/CSS는 문서 패널용 상태 표본이다. 실제 제품 구현은 Qt이며 표본을 웹 제품이나 네이티브 동작 검증으로 간주하지 않는다.

## Do's and Don'ts

### Do:

- **Do** 문서가 중앙의 가변 공간을 사용하게 하고 주변 패널을 접을 수 있게 유지한다.
- **Do** 선택·비활성·키보드 포커스와 저장하지 않은 변경을 서로 구분한다.
- **Do** 번들 Pretendard의 라이선스와 소스 기반 기하학 아이콘을 유지한다.
- **Do** 배율별 Windows 창에서 한국어 줄바꿈과 조작부 잘림을 확인한다.

### Don't:

- **Don't** UI 글꼴 설정으로 PDF 원본의 글꼴이나 문서 색상을 바꾸지 않는다.
- **Don't** 생성된 래스터 그림이나 장식 애니메이션을 작업 공간에 추가하지 않는다.
- **Don't** 미니멀하게 보이도록 기존 기능·라벨·단축키·상태 표시를 제거하지 않는다.

## 0.10 전체 UI 정리

변환은 28px 바깥 여백과 14px 그룹 간격, 서명·복구는 24px 여백과 12px 간격을 쓴다. 변환·서명 제목은 26px/600, 복구 제목은 22px/600이다. 변환은 라벨이 붙은 옵션과 결과 형식에 맞는 설명을 보여주며, 관련 없는 옵션은 비활성화한다. 서명 적용은 실제 획이 있을 때만 활성화한다. 빈 문서의 탐색·확대·저장도 비활성 상태로 표현한다.

오른쪽 패널은 입력 영역만 세로 스크롤하며 가로 스크롤은 생기지 않도록 숫자 입력 너비를 배분한다. 960×640에서도 적용·취소 영역은 스크롤과 무관하게 하단에 보인다. 선택 도구는 진한 파란 바탕과 흰 글자·아이콘, 선택 페이지는 옅은 선택 바탕과 파란 테두리로 구분한다. 기능을 뜻하는 선 아이콘과 실제 문서 그림자는 유지하며 장식용 아이콘·배지·색상은 추가하지 않는다.
