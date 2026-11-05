Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"

Name "Paperlight"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\Paperlight"
InstallDirRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Paperlight" "InstallLocation"
RequestExecutionLevel user
SetCompressor /SOLID lzma
SetOverwrite on
ShowInstDetails show
ShowUninstDetails show
VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey /LANG=1042 "ProductName" "Paperlight"
VIAddVersionKey /LANG=1042 "FileDescription" "Paperlight 설치 프로그램"
VIAddVersionKey /LANG=1042 "FileVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1042 "LegalCopyright" "Paperlight"
!define MUI_ICON "..\assets\paperlight.ico"
!define MUI_UNICON "..\assets\paperlight.ico"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TEXT "오프라인 PDF 뷰어·편집기를 현재 Windows 사용자 계정에 설치합니다.$\r$\n$\r$\n관리자 권한과 Python 설치가 필요하지 않습니다. 업데이트할 때는 설치된 Paperlight를 먼저 종료하세요."
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\Paperlight.exe"
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
  IfFileExists "$INSTDIR\Paperlight.exe" 0 closed
  ClearErrors
  FileOpen $0 "$INSTDIR\Paperlight.exe" a
  IfErrors busy
  FileClose $0
  Goto closed
busy:
  MessageBox MB_OK|MB_ICONEXCLAMATION "이 폴더의 Paperlight가 실행 중이거나 파일에 접근할 수 없습니다. 앱을 종료한 뒤 다시 시도하세요." /SD IDOK
  SetErrorLevel 2
  Abort
closed:
FunctionEnd
!macroend
!insertmacro CheckAppClosed ""
!insertmacro CheckAppClosed "un."

Section "Paperlight" SEC_MAIN
  Call CheckAppClosed
  SetOutPath "$INSTDIR"
  File /r "${PAYLOAD}\*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateDirectory "$SMPROGRAMS\Paperlight"
  CreateShortcut "$SMPROGRAMS\Paperlight\Paperlight.lnk" "$INSTDIR\Paperlight.exe"
  CreateShortcut "$SMPROGRAMS\Paperlight\Paperlight 제거.lnk" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "Paperlight"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\Paperlight.exe,0"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
  WriteRegStr HKCU "${UNINSTALL_KEY}" "QuietUninstallString" '$\"$INSTDIR\Uninstall.exe$\" /S'
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1
SectionEnd

Function un.onInit
  SetShellVarContext current
  Call un.CheckAppClosed
FunctionEnd

Section "Uninstall"
  !include "${OWNED_FILES}"
  ReadRegStr $0 HKCU "${UNINSTALL_KEY}" "InstallLocation"
  ${If} $0 == $INSTDIR
    Delete "$SMPROGRAMS\Paperlight\Paperlight.lnk"
    Delete "$SMPROGRAMS\Paperlight\Paperlight 제거.lnk"
    RMDir "$SMPROGRAMS\Paperlight"
    DeleteRegKey HKCU "${UNINSTALL_KEY}"
  ${EndIf}
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  ; LOCALAPPDATA\Paperlight의 서명과 복구본, 사용자가 넣은 파일은 유지한다.
SectionEnd
