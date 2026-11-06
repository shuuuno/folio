# 구성요소 및 내부 배포 범위

Paperlight는 개인 및 같은 조직 내부 팀 사용을 위해 만든 오프라인 Windows 앱입니다. 문서를 외부로 전송하지 않습니다. 이 문서는 Paperlight 자체 코드에 새 오픈소스 라이선스를 부여하지 않습니다. 유료 라이선스 구매나 코드 서명 인증서 발급은 아직 하지 않았습니다.

| 구성요소 | 라이선스 및 원본 |
|---|---|
| PyMuPDF / MuPDF | AGPL-3.0 또는 Artifex 상용 계약. https://pymupdf.io/licensing / https://artifex.com/licensing |
| PySide6 Essentials / shiboken6 / Qt | LGPL-3.0, GPL 및 개별 구성요소 고지. https://doc.qt.io/qtforpython-6/licenses.html |
| Python | PSF 및 포함 구성요소 라이선스. https://docs.python.org/3/license.html |
| PyInstaller | GPL 및 상업용 포함 실행 파일 배포 예외. https://pyinstaller.org/en/stable/license.html |
| NSIS 3.12 | zlib/libpng, 압축 모듈별 라이선스 및 링크 예외. https://nsis.sourceforge.io/License |
| Pretendard Variable 1.3.9 | SIL Open Font License 1.1. https://github.com/orioncactus/pretendard/tree/v1.3.9 |
| fontTools | MIT. https://github.com/fonttools/fonttools/blob/main/LICENSE |

정확한 패키지 버전은 `requirements-lock.txt`에 고정합니다. 실행 파일 옆 `licenses/`에는 설치된 패키지의 LICENSE/COPYING/NOTICE와 Python·NSIS 고지를 포함합니다. Qt는 `_internal` 아래 DLL로 동적 연결되며, 빌드 방법과 앱 소스는 같은 배포 버전의 Source ZIP에 제공합니다. 해당 컴포넌트의 수정·디버깅·재연결에 필요한 권리를 제한하는 별도 EULA를 추가하지 않습니다. 맑은 고딕 파일 자체는 배포하지 않으며 Windows에 설치된 글꼴을 사용합니다. 예제 PDF에는 표시용 부분 글꼴이 포함됩니다.

[GNU FAQ](https://www.gnu.org/licenses/gpl-faq.en.html#InternalDistribution)는 같은 조직 내부의 복사·사용과 다른 조직/개인에게 전달하는 배포를 구분합니다. 이 릴리스는 내부 사용 범위로 준비했습니다. 고객·외부 협력사 배포, 공개 다운로드, 서버 서비스로 확장할 때는 실제 배포 방식에 맞춰 AGPL 준수 범위 또는 Artifex 상용 계약을 먼저 결정해야 합니다. 비공개 Git 저장소나 무료 앱이라는 이유만으로 라이선스 의무가 없어지는 것은 아닙니다.

상용 PDF 편집기의 실행 파일·코드·아이콘·UI 리소스는 Paperlight 배포물에 포함하지 않습니다.

0.9.0 UI 글꼴은 수정하지 않은 Pretendard Variable을 포함합니다. 원본 라이선스는 `assets/fonts/OFL.txt`, 배포판에서는 `_internal/assets/fonts/OFL.txt`에 있습니다. PDF 본문 글꼴과는 별개입니다. 선 아이콘은 Paperlight에서 직접 그립니다.

0.8.0의 변환 기능은 python-docx, python-pptx, Pillow, lxml, pywin32와 그 의존성을 사용합니다. 고정 버전은 requirements-lock.txt, 포함 라이선스는 배포 폴더 licenses에 있습니다. Microsoft Office와 LibreOffice 자체는 배포하지 않으며, 사용자가 설치·사용 권한을 가진 프로그램을 로컬 변환에 이용합니다.
