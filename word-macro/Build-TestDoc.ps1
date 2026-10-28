#Requires -Version 5.1
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$outDocm = Join-Path $root 'test.docm'
$outDocx = Join-Path $root 'test.docx'
$modPath = Join-Path $root 'modKeystroke.bas'
$formCodePath = Join-Path $root 'frmKeystroke_Code.bas'

function Get-VbaBody([string]$path) {
    $raw = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)
    $idx = $raw.IndexOf('Option Explicit')
    if ($idx -lt 0) { throw "Option Explicit not found in $path" }
    return $raw.Substring($idx).TrimEnd() + "`r`n"
}

Get-Process WINWORD -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1

Write-Host 'Starting Word...'
$word = New-Object -ComObject Word.Application
$word.Visible = $true
$word.DisplayAlerts = 0
$doc = $null

try {
    $doc = $word.Documents.Add()

    $sel = $word.Selection
    $sel.TypeText('Test - rejestracja dynamiki pisania')
    $sel.TypeParagraph()
    $sel.TypeText('1. Jesli Word pokaze ostrzezenie o makrach - kliknij Wlacz zawartosc.')
    $sel.TypeParagraph()
    $sel.TypeText('2. Nacisnij Alt+F8, wybierz StartKeystrokeCapture, kliknij Uruchom.')
    $sel.TypeParagraph()
    $sel.TypeText('3. W formularzu: ID -> Start -> przepisz tekst -> Stop -> Eksport CSV.')
    $sel.TypeParagraph()
    $sel.TypeText('CSV: Documents\KeystrokeSessions\')

    if (Test-Path -LiteralPath $outDocm) { Remove-Item -LiteralPath $outDocm -Force }
    Write-Host 'Saving empty docm first...'
    $null = $doc.SaveAs2($outDocm, 13)
    $doc.Close($false)
    $doc = $null

    Write-Host 'Reopening docm...'
    $doc = $word.Documents.Open($outDocm)

    Write-Host 'Accessing VBProject...'
    $vbproj = $doc.VBProject
    if ($null -eq $vbproj) { throw 'VBProject is null - enable Trust access to VBA project object model' }

    $components = $vbproj.VBComponents
    if ($null -eq $components) { throw 'VBComponents is null' }
    Write-Host ("Components count: " + $components.Count)

    Write-Host 'Adding module modKeystroke...'
    $mod = $components.Add(1)
    if ($null -eq $mod) { throw 'Add(1) returned null' }
    $mod.Name = 'modKeystroke'
    $modCode = Get-VbaBody $modPath
    $cm = $mod.CodeModule
    if ($cm.CountOfLines -gt 0) { $cm.DeleteLines(1, $cm.CountOfLines) }
    $cm.AddFromString($modCode)
    Write-Host 'Module OK'

    Write-Host 'Creating UserForm...'
    $form = $components.Add(3)
    if ($null -eq $form) { throw 'Add(3) returned null' }
    Start-Sleep -Milliseconds 500
    $form.Name = 'frmKeystroke'
    $form.Properties.Item('Caption').Value = 'Rejestracja dynamiki pisania'
    $form.Properties.Item('Width').Value = 480
    $form.Properties.Item('Height').Value = 400
    try { $form.Properties.Item('KeyPreview').Value = $true } catch { Write-Host 'KeyPreview skip' }

    $d = $form.Designer
    if ($null -eq $d) { throw 'Designer is null' }

    function Add-Ctrl($designer, $progId, $name, $left, $top, $width, $height, $caption) {
        $c = $designer.Controls.Add($progId)
        if ($null -eq $c) { throw "Failed control $name" }
        $c.Name = $name
        $c.Left = $left
        $c.Top = $top
        $c.Width = $width
        $c.Height = $height
        if ($null -ne $caption) { try { $c.Caption = $caption } catch {} }
        return $c
    }

    [void](Add-Ctrl $d 'Forms.Label.1' 'lblId' 12 12 100 18 'ID uczestnika')
    $txtId = Add-Ctrl $d 'Forms.TextBox.1' 'txtParticipantId' 120 10 100 22 $null
    $txtId.Text = 'P001'
    [void](Add-Ctrl $d 'Forms.Label.1' 'lblTask' 240 12 80 18 'Tekst zadania')
    $cbo = Add-Ctrl $d 'Forms.ComboBox.1' 'cboTask' 330 10 120 22 $null
    try { $cbo.Style = 2 } catch {}
    [void](Add-Ctrl $d 'Forms.Label.1' 'lblRef' 12 42 200 18 'Tekst do przepisania')
    $ref = Add-Ctrl $d 'Forms.TextBox.1' 'txtReference' 12 62 450 90 $null
    $ref.MultiLine = $true; $ref.EnterKeyBehavior = $true; $ref.ScrollBars = 2; $ref.Locked = $true
    [void](Add-Ctrl $d 'Forms.Label.1' 'lblType' 12 160 200 18 'Pole wpisywania')
    $typed = Add-Ctrl $d 'Forms.TextBox.1' 'txtTyped' 12 180 450 100 $null
    $typed.MultiLine = $true; $typed.EnterKeyBehavior = $true; $typed.ScrollBars = 2
    [void](Add-Ctrl $d 'Forms.CommandButton.1' 'btnStart' 12 295 80 28 'Start')
    [void](Add-Ctrl $d 'Forms.CommandButton.1' 'btnStop' 100 295 80 28 'Stop')
    [void](Add-Ctrl $d 'Forms.CommandButton.1' 'btnExport' 188 295 100 28 'Eksport CSV')
    [void](Add-Ctrl $d 'Forms.CommandButton.1' 'btnClear' 296 295 80 28 'Wyczysc')
    [void](Add-Ctrl $d 'Forms.CommandButton.1' 'btnClose' 384 295 78 28 'Zamknij')
    [void](Add-Ctrl $d 'Forms.Label.1' 'lblStatus' 12 335 450 18 'Status')
    [void](Add-Ctrl $d 'Forms.Label.1' 'lblEvents' 12 355 150 18 'Zdarzenia: 0')
    [void](Add-Ctrl $d 'Forms.Label.1' 'lblFolder' 170 355 290 18 'Folder CSV:')

    Write-Host 'Adding form code...'
    $formCode = Get-VbaBody $formCodePath
    $fcm = $form.CodeModule
    if ($fcm.CountOfLines -gt 0) { $fcm.DeleteLines(1, $fcm.CountOfLines) }
    $fcm.AddFromString($formCode)

    Write-Host 'Saving final docm...'
    $doc.Save()

    # Instruction docx
    $docx = $word.Documents.Add()
    $docx.Content.Text = "Test - rejestracja dynamiki pisania`r`n`r`nWAZNE: test.docx NIE ma makr.`r`nOtworz test.docm w tym samym folderze.`r`n`r`n1. Otworz test.docm`r`n2. Wlacz makra`r`n3. Alt+F8 -> StartKeystrokeCapture -> Uruchom`r`n`r`nCSV: Documents\KeystrokeSessions\"
    if (Test-Path -LiteralPath $outDocx) { Remove-Item -LiteralPath $outDocx -Force }
    $null = $docx.SaveAs2($outDocx, 12)
    $docx.Close($false)

    $doc.Close($false)
    $doc = $null
    Write-Host 'OK'
    Write-Host "Macros: $outDocm"
    Write-Host "Instructions: $outDocx"
}
catch {
    Write-Host ("ERROR: " + $_.Exception.Message) -ForegroundColor Red
    if ($_.Exception.InnerException) {
        Write-Host ("INNER: " + $_.Exception.InnerException.Message)
    }
    Write-Host $_.ScriptStackTrace
    try { if ($null -ne $doc) { $doc.Close($false) } } catch {}
    exit 1
}
finally {
    try { $word.Quit() } catch {}
    try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null } catch {}
}
