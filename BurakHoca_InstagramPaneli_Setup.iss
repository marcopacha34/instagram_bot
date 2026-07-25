#define MyAppName "Burak Hoca Instagram Paneli"
#define MyAppVersion "3.5.0"
#define MyAppPublisher "Burak ÖZKAN"
#define MyAppURL "https://www.burakhoca.com"
#define MyAppExeName "BurakHoca_InstagramPaneli.exe"

[Setup]
AppId={{6f5517c8-6c88-4db1-b109-aa5cdc9cea12}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppContact=Burak ÖZKAN | Instagram: @Burakhocafen | Telefon: 0552 219 87 87
DefaultDirName={autopf}\Burak Hoca\Instagram Paneli
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=LICENSE
OutputDir=setup
OutputBaseFilename=BurakHoca_InstagramPaneli_Setup
SetupIconFile=burakhoca_instagram_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=110
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
CloseApplications=yes
RestartApplications=no
VersionInfoCompany=Burak ÖZKAN
VersionInfoDescription=Burak Hoca Instagram Takipçi Paneli Kurulumu
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoVersion={#MyAppVersion}
VersionInfoCopyright=Copyright (C) 2026 Burak ÖZKAN

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Kısayollar:"; Flags: checkedonce
Name: "startupicon"; Description: "Windows açılışında çalıştır"; GroupDescription: "İsteğe bağlı:"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{autostartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Burak Hoca Instagram Paneli'ni çalıştır"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
var
  PromotionPage: TWizardPage;
  PromotionTitle: TNewStaticText;
  PromotionText: TNewStaticText;
  PromotionInstagram: TNewStaticText;
  PromotionWeb: TNewStaticText;
  PromotionPhone: TNewStaticText;

procedure InitializeWizard;
begin
  WizardForm.Caption := 'Burak Hoca Instagram Paneli • Kurulum';
  WizardForm.WelcomeLabel1.Caption := 'Burak Hoca Instagram Paneli''ne Hoş Geldiniz';
  WizardForm.WelcomeLabel2.Caption :=
    'Bu kurulum programı gerekli masaüstü bileşenlerini otomatik olarak kurar.' +
    Chr(13) + Chr(10) + Chr(13) + Chr(10) +
    'Burak ÖZKAN • @Burakhocafen • www.burakhoca.com • 0552 219 87 87';

  PromotionPage := CreateCustomPage(
    wpWelcome,
    'Burak Hoca • İletişim',
    'Dijital Eğitim ve Danışmanlık'
  );

  PromotionTitle := TNewStaticText.Create(PromotionPage);
  PromotionTitle.Parent := PromotionPage.Surface;
  PromotionTitle.Caption := 'BURAK HOCA';
  PromotionTitle.Font.Name := 'Segoe UI';
  PromotionTitle.Font.Size := 18;
  PromotionTitle.Font.Style := [fsBold];
  PromotionTitle.Font.Color := $00B43383;
  PromotionTitle.Top := 18;
  PromotionTitle.Left := 8;

  PromotionText := TNewStaticText.Create(PromotionPage);
  PromotionText.Parent := PromotionPage.Surface;
  PromotionText.Caption := 'Burak ÖZKAN • Dijital Eğitim & Danışmanlık';
  PromotionText.Font.Name := 'Segoe UI';
  PromotionText.Font.Size := 11;
  PromotionText.Font.Style := [fsBold];
  PromotionText.Top := 64;
  PromotionText.Left := 8;

  PromotionInstagram := TNewStaticText.Create(PromotionPage);
  PromotionInstagram.Parent := PromotionPage.Surface;
  PromotionInstagram.Caption := 'Instagram: @Burakhocafen';
  PromotionInstagram.Font.Name := 'Segoe UI';
  PromotionInstagram.Font.Size := 10;
  PromotionInstagram.Top := 108;
  PromotionInstagram.Left := 8;

  PromotionWeb := TNewStaticText.Create(PromotionPage);
  PromotionWeb.Parent := PromotionPage.Surface;
  PromotionWeb.Caption := 'Web: www.burakhoca.com';
  PromotionWeb.Font.Name := 'Segoe UI';
  PromotionWeb.Font.Size := 10;
  PromotionWeb.Top := 138;
  PromotionWeb.Left := 8;

  PromotionPhone := TNewStaticText.Create(PromotionPage);
  PromotionPhone.Parent := PromotionPage.Surface;
  PromotionPhone.Caption := 'Telefon / WhatsApp: 0552 219 87 87';
  PromotionPhone.Font.Name := 'Segoe UI';
  PromotionPhone.Font.Size := 10;
  PromotionPhone.Top := 168;
  PromotionPhone.Left := 8;
end;

function IsChromeInstalled: Boolean;
begin
  Result :=
    FileExists(ExpandConstant('{pf}\Google\Chrome\Application\chrome.exe')) or
    FileExists(ExpandConstant('{pf32}\Google\Chrome\Application\chrome.exe')) or
    FileExists(ExpandConstant('{localappdata}\Google\Chrome\Application\chrome.exe'));
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if not IsChromeInstalled then
    MsgBox(
      'Google Chrome bulunamadı. Programın tarayıcı otomasyonu için Chrome kurulmalıdır.' +
      Chr(13) + Chr(10) + 'Kurulum tamamlandıktan sonra https://www.google.com/chrome/ adresinden Chrome yükleyin.',
      mbInformation,
      MB_OK
    );
end;
