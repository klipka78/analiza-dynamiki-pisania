Attribute VB_Name = "Installer"
Option Explicit

' ============================================================
' JEDNORAZOWY INSTALATOR
' 1. Nowy dokument -> Zapisz jako test.docm (dokument z makrami)
' 2. Alt+F11 -> Plik -> Importuj plik -> ten Installer.bas
' 3. Alt+F8 -> RunInstaller -> Uruchom
' 4. Po sukcesie mozesz usunac modul Installer
' Wymaga: Ufaj dostepowi do modelu obiektowego projektu VBA
' ============================================================

Public Sub RunInstaller()
    Dim vbProj As Object
    Dim modComp As Object
    Dim formComp As Object
    Dim d As Object
    Dim cm As Object
    Dim root As String
    Dim modPath As String
    Dim formPath As String
    Dim modCode As String
    Dim formCode As String

    On Error GoTo Fail

    root = Environ$("USERPROFILE") & "\Projects\mgr\word-macro\"
    If Dir$(root & "modKeystroke.bas") = "" Then
        root = ThisDocument.Path & "\"
    End If
    If Dir$(root & "modKeystroke.bas") = "" Then
        root = InputBox("Podaj sciezke folderu word-macro (z plikami .bas):", _
                        "Installer", "C:\Users\p304500\Projects\mgr\word-macro\")
        If Right$(root, 1) <> "\" Then root = root & "\"
    End If

    modPath = root & "modKeystroke.bas"
    formPath = root & "frmKeystroke_Code.bas"

    If Dir$(modPath) = "" Or Dir$(formPath) = "" Then
        MsgBox "Nie znaleziono plikow .bas w:" & vbCrLf & root, vbCritical
        Exit Sub
    End If

    Set vbProj = ActiveDocument.VBProject

    ' --- modul ---
    On Error Resume Next
    Set modComp = vbProj.VBComponents("modKeystroke")
    On Error GoTo Fail
    If Not modComp Is Nothing Then
        vbProj.VBComponents.Remove modComp
    End If

    Set modComp = vbProj.VBComponents.Add(1) ' stdmodule
    modComp.Name = "modKeystroke"
    modCode = ReadFileText(modPath)
    modCode = Mid$(modCode, InStr(1, modCode, "Option Explicit"))
    Set cm = modComp.CodeModule
    If cm.CountOfLines > 0 Then cm.DeleteLines 1, cm.CountOfLines
    cm.AddFromString modCode

    ' --- form ---
    On Error Resume Next
    Set formComp = vbProj.VBComponents("frmKeystroke")
    On Error GoTo Fail
    If Not formComp Is Nothing Then
        vbProj.VBComponents.Remove formComp
    End If

    Set formComp = vbProj.VBComponents.Add(3) ' MSForm
    formComp.Name = "frmKeystroke"
    formComp.Properties("Caption") = "Rejestracja dynamiki pisania"
    formComp.Properties("Width") = 480
    formComp.Properties("Height") = 400
    On Error Resume Next
    formComp.Properties("KeyPreview") = True
    On Error GoTo Fail

    Set d = formComp.Designer
    AddCtrl d, "Forms.Label.1", "lblId", 12, 12, 100, 18, "ID uczestnika"
    AddCtrl d, "Forms.TextBox.1", "txtParticipantId", 120, 10, 100, 22, ""
    AddCtrl d, "Forms.Label.1", "lblTask", 240, 12, 80, 18, "Tekst zadania"
    AddCtrl d, "Forms.ComboBox.1", "cboTask", 330, 10, 120, 22, ""
    AddCtrl d, "Forms.Label.1", "lblRef", 12, 42, 200, 18, "Tekst do przepisania"
    AddCtrl d, "Forms.TextBox.1", "txtReference", 12, 62, 450, 90, ""
    With d.Controls("txtReference")
        .MultiLine = True
        .EnterKeyBehavior = True
        .ScrollBars = 2
        .Locked = True
    End With
    AddCtrl d, "Forms.Label.1", "lblType", 12, 160, 200, 18, "Pole wpisywania"
    AddCtrl d, "Forms.TextBox.1", "txtTyped", 12, 180, 450, 100, ""
    With d.Controls("txtTyped")
        .MultiLine = True
        .EnterKeyBehavior = True
        .ScrollBars = 2
    End With
    AddCtrl d, "Forms.CommandButton.1", "btnStart", 12, 295, 80, 28, "Start"
    AddCtrl d, "Forms.CommandButton.1", "btnStop", 100, 295, 80, 28, "Stop"
    AddCtrl d, "Forms.CommandButton.1", "btnExport", 188, 295, 100, 28, "Eksport CSV"
    AddCtrl d, "Forms.CommandButton.1", "btnClear", 296, 295, 80, 28, "Wyczysc"
    AddCtrl d, "Forms.CommandButton.1", "btnClose", 384, 295, 78, 28, "Zamknij"
    AddCtrl d, "Forms.Label.1", "lblStatus", 12, 335, 450, 18, "Status"
    AddCtrl d, "Forms.Label.1", "lblEvents", 12, 355, 150, 18, "Zdarzenia: 0"
    AddCtrl d, "Forms.Label.1", "lblFolder", 170, 355, 290, 18, "Folder CSV:"

    formCode = ReadFileText(formPath)
    formCode = Mid$(formCode, InStr(1, formCode, "Option Explicit"))
    Set cm = formComp.CodeModule
    If cm.CountOfLines > 0 Then cm.DeleteLines 1, cm.CountOfLines
    cm.AddFromString formCode

    ActiveDocument.Save
    MsgBox "Instalacja OK." & vbCrLf & _
           "Alt+F8 -> StartKeystrokeCapture -> Uruchom", vbInformation
    Exit Sub

Fail:
    MsgBox "Blad instalacji: " & Err.Description & vbCrLf & vbCrLf & _
           "Wlacz: Plik -> Opcje -> Centrum zaufania -> Ustawienia makr ->" & vbCrLf & _
           "Ufaj dostepowi do modelu obiektowego projektu VBA", vbCritical
End Sub

Private Sub AddCtrl(ByVal d As Object, ByVal progId As String, ByVal name As String, _
                    ByVal leftPos As Single, ByVal topPos As Single, _
                    ByVal widthPos As Single, ByVal heightPos As Single, _
                    ByVal caption As String)
    Dim c As Object
    Set c = d.Controls.Add(progId)
    c.Name = name
    c.Left = leftPos
    c.Top = topPos
    c.Width = widthPos
    c.Height = heightPos
    On Error Resume Next
    If Len(caption) > 0 Then c.Caption = caption
    On Error GoTo 0
End Sub

Private Function ReadFileText(ByVal path As String) As String
    Dim f As Integer
    Dim s As String
    f = FreeFile
    Open path For Input As #f
    s = Input$(LOF(f), f)
    Close #f
    ' Usun BOM UTF-8 jesli jest
    If Left$(s, 3) = Chr$(239) & Chr$(187) & Chr$(191) Then s = Mid$(s, 4)
    ReadFileText = s
End Function
