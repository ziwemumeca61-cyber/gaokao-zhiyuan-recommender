; Inno Setup 脚本：把绿色版打包成 setup.exe（带桌面快捷方式）。
; 用法：
;   1) 先用 build_portable.bat 生成 dist\高考志愿推荐系统\
;   2) 安装 Inno Setup（https://jrsoftware.org/isdl.php），用它打开本文件，点 Build
;   3) 生成的 setup.exe 在 packaging\Output\，交付客户即可
;
; 客户安装后，双击桌面「高考志愿推荐系统」即启动（内部调用 启动应用.bat）。

#define AppName "高考志愿推荐系统"
#define AppVer "1.0.0"
#define SrcDir "..\dist\高考志愿推荐系统"

[Setup]
AppName={#AppName}
AppVersion={#AppVer}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=Output
OutputBaseFilename=高考志愿推荐系统_setup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=yes

[Languages]
Name: "chs"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Files]
; 把整个绿色版目录打包进去
Source: "{#SrcDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
; 桌面 & 开始菜单快捷方式，指向启动脚本
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\启动应用.bat"; WorkingDir: "{app}"; IconFilename: "{app}\app.ico"
Name: "{group}\{#AppName}"; Filename: "{app}\启动应用.bat"; WorkingDir: "{app}"; IconFilename: "{app}\app.ico"

[Run]
; 安装完成后可选立即启动
Filename: "{app}\启动应用.bat"; Description: "立即启动"; Flags: nowait postinstall skipifsilent shellexec
