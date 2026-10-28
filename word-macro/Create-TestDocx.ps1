#Requires -Version 5.1
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$outDocx = Join-Path $root 'test.docx'
$tmp = Join-Path $env:TEMP ('testdocx_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null
New-Item -ItemType Directory -Path (Join-Path $tmp '_rels') | Out-Null
New-Item -ItemType Directory -Path (Join-Path $tmp 'word') | Out-Null
New-Item -ItemType Directory -Path (Join-Path $tmp 'word\_rels') | Out-Null

$documentXml = @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:rPr><w:b/><w:sz w:val="32"/></w:rPr><w:t>Test - rejestracja dynamiki pisania</w:t></w:r></w:p>
    <w:p><w:r><w:t>Pliki .bas z folderu word-macro NIE otwierasz dwuklikiem. Wklejasz je do Worda jako makra.</w:t></w:r></w:p>
    <w:p><w:r><w:t>========================================</w:t></w:r></w:p>
    <w:p><w:r><w:rPr><w:b/></w:rPr><w:t>CO ZROBIC (krok po kroku)</w:t></w:r></w:p>
    <w:p><w:r><w:t>1. W Wordzie: Plik - Zapisz jako - typ: Szablon programu Word z obsluga makr (*.dotm) LUB Dokument Word z obsluga makr (*.docm). Nazwa np. test.docm</w:t></w:r></w:p>
    <w:p><w:r><w:t>2. Plik - Opcje - Centrum zaufania - Ustawienia - Ustawienia makr: wlacz powiadomienia / zezwol na makra.</w:t></w:r></w:p>
    <w:p><w:r><w:t>3. Zaznacz tez: Ufaj dostepowi do modelu obiektowego projektu VBA (opcjonalne, do automatyzacji).</w:t></w:r></w:p>
    <w:p><w:r><w:t>4. Alt+F11 (edytor VBA). W projekcie dokumentu: Plik - Importuj plik - wybierz modKeystroke.bas</w:t></w:r></w:p>
    <w:p><w:r><w:t>5. Wstaw - UserForm. W Properties ustaw Name = frmKeystroke oraz KeyPreview = True</w:t></w:r></w:p>
    <w:p><w:r><w:t>6. Dodaj kontrolki o nazwach: txtParticipantId, cboTask, txtReference, txtTyped, btnStart, btnStop, btnExport, btnClear, btnClose, lblStatus, lblEvents, lblFolder (szczegoly w README.md)</w:t></w:r></w:p>
    <w:p><w:r><w:t>7. Dwuklik na formularzu - wklej kod z frmKeystroke_Code.bas (od Option Explicit)</w:t></w:r></w:p>
    <w:p><w:r><w:t>8. Zapisz. Alt+F8 - StartKeystrokeCapture - Uruchom</w:t></w:r></w:p>
    <w:p><w:r><w:t>9. W formularzu: ID (P001) - Start - przepisz tekst - Stop - Eksport CSV</w:t></w:r></w:p>
    <w:p><w:r><w:t>10. CSV znajdziesz w: Dokumenty\KeystrokeSessions\</w:t></w:r></w:p>
    <w:p><w:r><w:t>========================================</w:t></w:r></w:p>
    <w:p><w:r><w:rPr><w:b/></w:rPr><w:t>WAZNE</w:t></w:r></w:p>
    <w:p><w:r><w:t>Ten plik test.docx NIE moze zawierac makr (.docx ich nie trzyma). Do makr potrzebujesz test.docm.</w:t></w:r></w:p>
    <w:p><w:r><w:t>Szybka sciezka: otworz Install-Keystroke.bas w Notatniku, skopiuj, w VBA wstaw modul i wklej - ALBO uzyj Installer.bas (patrz folder).</w:t></w:r></w:p>
    <w:sectPr/>
  </w:body>
</w:document>
'@

$contentTypes = @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
'@

$rels = @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
'@

$wordRels = @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
</Relationships>
'@

$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText((Join-Path $tmp '[Content_Types].xml'), $contentTypes, $utf8NoBom)
[System.IO.File]::WriteAllText((Join-Path $tmp '_rels\.rels'), $rels, $utf8NoBom)
[System.IO.File]::WriteAllText((Join-Path $tmp 'word\document.xml'), $documentXml, $utf8NoBom)
[System.IO.File]::WriteAllText((Join-Path $tmp 'word\_rels\document.xml.rels'), $wordRels, $utf8NoBom)

if (Test-Path -LiteralPath $outDocx) { Remove-Item -LiteralPath $outDocx -Force }

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($tmp, $outDocx)

Remove-Item -LiteralPath $tmp -Recurse -Force
Write-Host "Created: $outDocx"
