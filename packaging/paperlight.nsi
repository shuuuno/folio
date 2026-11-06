Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"

Name "Folio"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\Folio"
InstallDirRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Paperlight" "InstallLocation"
RequestExecutionLevel user
SetCompressor /SOLID lzma
SetOverwrite on
ShowInstDetails show
ShowUninstDetails show
VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey /LANG=1042 "ProductName" "Folio"
VIAddVersionKey /LANG=1042 "FileDescription" "Folio 설치 프로그램"
VIAddVersionKey /LANG=1042 "FileVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1042 "LegalCopyright" "Folio"
!define MUI_ICON "..\assets\paperlight.ico"
!define MUI_UNICON "..\assets\paperlight.ico"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TEXT "오프라인 PDF 뷰어·편집기를 현재 Windows 사용자 계정에 설치합니다.$\r$\n$\r$\n관리자 권한과 Python 설치가 필요하지 않습니다. 업데이트할 때는 설치된 Folio 또는 Paperlight를 먼저 종료하세요."
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\Folio.exe"
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Korean"

!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\Paperlight"

Function .onInit
  SetShellVarContext current
  ${IfNot} ${RunningX64}
    MessageBox MB_OK|MB_ICONSTOP "64비트 Windows가 필요합니다." /SD IDOK
    SetErrorLevel 2
    Abort
  ${EndIf}
FunctionEnd

; 열린 EXE에 쓰기 핸들을 얻을 수 없으면 파일을 건드리기 전에 중단한다.
!macro CheckAppClosed PREFIX
Function ${PREFIX}CheckAppClosed
  IfFileExists "$INSTDIR\Paperlight.exe" 0 check_folio
  ClearErrors
  FileOpen $0 "$INSTDIR\Paperlight.exe" a
  IfErrors busy
  FileClose $0
check_folio:
  IfFileExists "$INSTDIR\Folio.exe" 0 closed
  ClearErrors
  FileOpen $0 "$INSTDIR\Folio.exe" a
  IfErrors busy
  FileClose $0
  Goto closed
busy:
  MessageBox MB_OK|MB_ICONEXCLAMATION "이 폴더의 Folio 또는 Paperlight가 실행 중이거나 파일에 접근할 수 없습니다. 트레이 메뉴에서 ‘완전히 종료’한 뒤 다시 시도하세요." /SD IDOK
  SetErrorLevel 2
  Abort
closed:
FunctionEnd
!macroend
!insertmacro CheckAppClosed ""
!insertmacro CheckAppClosed "un."

Section "Folio" SEC_MAIN
  Call CheckAppClosed
  ; 기존 등록 위치에 업데이트할 때만 이전 제품의 실행 파일·바로가기를 정리한다.
  ReadRegStr $R8 HKCU "${UNINSTALL_KEY}" "InstallLocation"
  ${If} $R8 == $INSTDIR
    Delete "$INSTDIR\Paperlight.exe"
    Delete "$SMPROGRAMS\Paperlight\Paperlight.lnk"
    Delete "$SMPROGRAMS\Paperlight\Paperlight 제거.lnk"
    RMDir "$SMPROGRAMS\Paperlight"
  ${EndIf}
  SetOutPath "$INSTDIR"
  File /r "${PAYLOAD}\*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateDirectory "$SMPROGRAMS\Folio"
  CreateShortcut "$SMPROGRAMS\Folio\Folio.lnk" "$INSTDIR\Folio.exe"
  CreateShortcut "$SMPROGRAMS\Folio\Folio 제거.lnk" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "Folio"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\Folio.exe,0"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
  WriteRegStr HKCU "${UNINSTALL_KEY}" "QuietUninstallString" '$\"$INSTDIR\Uninstall.exe$\" /S'
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1
  SetRegView 64
  WriteRegStr HKCU "Software\Classes\Paperlight.PDF" "" "Folio PDF 문서"
  WriteRegStr HKCU "Software\Classes\Paperlight.PDF\DefaultIcon" "" '$\"$INSTDIR\Folio.exe$\",0'
  WriteRegStr HKCU "Software\Classes\Paperlight.PDF\shell\open\command" "" '$\"$INSTDIR\Folio.exe$\" $\"%1$\"'
  WriteRegStr HKCU "Software\Classes\.pdf\OpenWithProgids" "Paperlight.PDF" ""
  WriteRegStr HKCU "Software\Paperlight\Capabilities" "ApplicationName" "Folio"
  WriteRegStr HKCU "Software\Paperlight\Capabilities" "ApplicationDescription" "오프라인 PDF 뷰어·편집기"
  WriteRegStr HKCU "Software\Paperlight\Capabilities\FileAssociations" ".pdf" "Paperlight.PDF"
  ReadRegStr $0 HKCU "Software\RegisteredApplications" "Paperlight"
  ${If} $0 == "Software\Paperlight\Capabilities"
    DeleteRegValue HKCU "Software\RegisteredApplications" "Paperlight"
  ${EndIf}
  WriteRegStr HKCU "Software\RegisteredApplications" "Folio" "Software\Paperlight\Capabilities"
  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
  SetRegView 32
SectionEnd

Function un.onInit
  SetShellVarContext current
  Call un.CheckAppClosed
FunctionEnd

Section "Uninstall"
  !include "${OWNED_FILES}"
  ReadRegStr $0 HKCU "${UNINSTALL_KEY}" "InstallLocation"
  ${If} $0 == $INSTDIR
    Delete "$SMPROGRAMS\Folio\Folio.lnk"
    Delete "$SMPROGRAMS\Folio\Folio 제거.lnk"
    RMDir "$SMPROGRAMS\Folio"
    DeleteRegKey HKCU "${UNINSTALL_KEY}"
  ${EndIf}
  SetRegView 64
  ReadRegStr $0 HKCU "Software\Classes\Paperlight.PDF\shell\open\command" ""
  ${If} $0 == '$\"$INSTDIR\Folio.exe$\" $\"%1$\"'
    DeleteRegKey HKCU "Software\Classes\Paperlight.PDF"
    DeleteRegValue HKCU "Software\Classes\.pdf\OpenWithProgids" "Paperlight.PDF"
    DeleteRegKey HKCU "Software\Paperlight\Capabilities"
    DeleteRegValue HKCU "Software\RegisteredApplications" "Folio"
    System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
  ${EndIf}
  SetRegView 32
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  ; LOCALAPPDATA\Paperlight의 서명과 복구본, 사용자가 넣은 파일은 유지한다.
SectionEnd
