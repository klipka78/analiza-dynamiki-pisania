Attribute VB_Name = "frmKeystroke_Code_PASTE_INTO_FORM"
' ============================================================
' SKOPIUJ CAŁĄ TREŚĆ PONIŻEJ (od Option Explicit) do okna kodu
' formularza frmKeystroke w edytorze VBA (nie do modułu .bas).
' ============================================================

Option Explicit

Private capturing As Boolean
Private lastDownCode As Integer

Private Sub UserForm_Initialize()
    Me.KeyPreview = True
    capturing = False
    lastDownCode = 0

    txtParticipantId.Text = "P001"
    cboTask.Clear
    cboTask.AddItem "A"
    cboTask.AddItem "B"
    cboTask.AddItem "C"
    cboTask.ListIndex = 0

    lblStatus.Caption = "Gotowy. Wpisz ID, wybierz tekst, kliknij Start."
    lblEvents.Caption = "Zdarzenia: 0"
    txtReference.Text = DefaultTaskText("A")
    txtTyped.Text = ""
    txtTyped.Locked = True
    btnStop.Enabled = False
    btnExport.Enabled = False

    EnsureExportFolder
    lblFolder.Caption = "Folder CSV: " & gExportFolder
End Sub

Private Sub cboTask_Change()
    If Not capturing Then
        txtReference.Text = DefaultTaskText(cboTask.Text)
    End If
End Sub

Private Sub btnStart_Click()
    Dim pid As String
    Dim tid As String

    pid = Trim$(txtParticipantId.Text)
    If Len(pid) = 0 Then
        MsgBox "Podaj identyfikator uczestnika (np. P001).", vbExclamation
        Exit Sub
    End If

    tid = Trim$(cboTask.Text)
    If Len(tid) = 0 Then tid = "A"

    InitSession pid, tid
    txtTyped.Text = ""
    txtTyped.Locked = False
    capturing = True
    lastDownCode = 0

    btnStart.Enabled = False
    btnStop.Enabled = True
    btnExport.Enabled = False
    txtParticipantId.Enabled = False
    cboTask.Enabled = False

    lblStatus.Caption = "REJESTRACJA: sesja " & gSessionId
    lblEvents.Caption = "Zdarzenia: 0"
    On Error Resume Next
    txtTyped.SetFocus
    On Error GoTo 0
End Sub

Private Sub btnStop_Click()
    capturing = False
    StopSession
    txtTyped.Locked = True

    btnStart.Enabled = True
    btnStop.Enabled = False
    btnExport.Enabled = (gEventCount > 0)
    txtParticipantId.Enabled = True
    cboTask.Enabled = True

    lblStatus.Caption = "Zatrzymano. Zdarzenia: " & CStr(gEventCount) & ". Możesz wyeksportować CSV."
End Sub

Private Sub btnExport_Click()
    Dim ok As Boolean
    Dim outPath As String

    If gEventCount = 0 Then
        MsgBox "Brak zdarzeń do eksportu.", vbExclamation
        Exit Sub
    End If

    ok = ExportSessionCsv(txtTyped.Text, txtReference.Text, outPath)
    If ok Then
        lblStatus.Caption = "Zapisano: " & outPath
        MsgBox "Zapisano:" & vbCrLf & outPath & vbCrLf & _
               "(oraz plik *_meta.csv w tym samym folderze)", vbInformation
    Else
        MsgBox "Nie udało się zapisać CSV." & vbCrLf & outPath, vbCritical
    End If
End Sub

Private Sub btnClear_Click()
    If capturing Then
        MsgBox "Najpierw zatrzymaj rejestrację (Stop).", vbExclamation
        Exit Sub
    End If
    ResetSessionBuffer
    txtTyped.Text = ""
    txtTyped.Locked = True
    btnExport.Enabled = False
    lblEvents.Caption = "Zdarzenia: 0"
    lblStatus.Caption = "Bufor wyczyszczony."
End Sub

Private Sub btnClose_Click()
    If capturing Then
        If MsgBox("Rejestracja trwa. Zamknąć mimo to?", vbYesNo + vbQuestion) = vbNo Then
            Exit Sub
        End If
        capturing = False
        StopSession
    End If
    Unload Me
End Sub

Private Sub UserForm_KeyDown(ByVal KeyCode As MSForms.ReturnInteger, ByVal Shift As Integer)
    If Not capturing Then Exit Sub
    LogKeyEvent "down", CInt(KeyCode), Shift
    lastDownCode = KeyCode
    UpdateEventLabel
End Sub

Private Sub UserForm_KeyUp(ByVal KeyCode As MSForms.ReturnInteger, ByVal Shift As Integer)
    If Not capturing Then Exit Sub
    LogKeyEvent "up", CInt(KeyCode), Shift
    If KeyCode = lastDownCode Then lastDownCode = 0
    UpdateEventLabel
End Sub

Private Sub UpdateEventLabel()
    lblEvents.Caption = "Zdarzenia: " & CStr(gEventCount)
End Sub
