; =========================
; installer.iss (Inno Setup)
; =========================

; ---- Datos de tu app ----
#define MyAppName      "HelpDeskManagerApp"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#define MyAppPublisher "Tu Empresa"
#define MyAppExeName   "HelpDeskManagerApp.exe"

; ---- Rutas basadas en la ubicación del .iss ----
#define BasePath       AddBackslash(SourcePath)
#define MyAppDir       BasePath + "dist\HelpDeskManagerApp"   ; carpeta que genera PyInstaller (ONEDIR)
#define MyIcon         BasePath + "ico.ico"                   ; ícono junto al .iss

; Verificaciones de build
#if !DirExists(MyAppDir)
  #error "No existe dist\HelpDeskManagerApp. Compilá con PyInstaller antes."
#endif

#if !FileExists(MyIcon)
  #pragma warning "ico.ico no encontrado; se usará el ícono del EXE."
#endif

; ---- GUID único (usar llaves dobles) ----
#define MyAppId        "{{3D57979A-7152-4B96-B5D8-9F83607E28D1}}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=Output
OutputBaseFilename={#MyAppName}_Setup_{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
DisableDirPage=no
DisableProgramGroupPage=no
UninstallDisplayIcon={app}\{#MyAppExeName}
UsePreviousTasks=yes
CloseApplications=yes
RestartApplications=yes
AppMutex=HelpDeskManagerApp
#if FileExists(MyIcon)
SetupIconFile={#MyIcon}
#endif

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear icono en el &Escritorio"; GroupDescription: "Tareas adicionales:"; Flags: unchecked
Name: "autorun";     Description: "Iniciar {#MyAppName} con Windows"; GroupDescription: "Tareas adicionales:"; Flags: unchecked

; --- Inicio automático por USUARIO (HKCU) — NO requiere admin ---
[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: autorun; Flags: uninsdeletevalue

; --- Para TODOS los usuarios (HKLM), usar esta línea en lugar de la de arriba y activar PrivilegesRequired=admin ---
; Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: autorun; Flags: uninsdeletevalue

[Files]
Source: "{#MyAppDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#if FileExists(MyIcon)
Source: "{#MyIcon}";     DestDir: "{app}"; Flags: ignoreversion
#endif

; ----- ICONOS -----
; Si existe ico.ico, los accesos directos lo usan; si no, usan el icono del EXE
#if FileExists(MyIcon)
[Icons]
Name: "{group}\{#MyAppName}";         Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\ico.ico"; WorkingDir: "{app}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\ico.ico"; Tasks: desktopicon; WorkingDir: "{app}"
#else
[Icons]
Name: "{group}\{#MyAppName}";         Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; WorkingDir: "{app}"
#endif

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar {#MyAppName}"; Flags: nowait postinstall skipifsilent
