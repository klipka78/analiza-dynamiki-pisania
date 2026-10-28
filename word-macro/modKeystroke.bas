Attribute VB_Name = "modKeystroke"
Option Explicit

' ============================================================
' Analiza charakteru pisma komputerowego — rejestracja zdarzeń
' Moduł: start sesji, bufor eventów, eksport CSV
' ============================================================

#If VBA7 Then
    Private Declare PtrSafe Function QueryPerformanceCounter Lib "kernel32" ( _
        ByRef lpPerformanceCount As Currency) As Long
    Private Declare PtrSafe Function QueryPerformanceFrequency Lib "kernel32" ( _
        ByRef lpFrequency As Currency) As Long
#Else
    Private Declare Function QueryPerformanceCounter Lib "kernel32" ( _
        ByRef lpPerformanceCount As Currency) As Long
    Private Declare Function QueryPerformanceFrequency Lib "kernel32" ( _
        ByRef lpFrequency As Currency) As Long
#End If

Public Type KeystrokeEvent
    Seq As Long
    ElapsedMs As Double
    EventType As String   ' "down" | "up"
    KeyCode As Integer
    KeyName As String
    Shift As Boolean
    Ctrl As Boolean
    Alt As Boolean
End Type

' --- stan sesji ---
Public gEvents() As KeystrokeEvent
Public gEventCount As Long
Public gSessionId As String
Public gParticipantId As String
Public gTaskId As String
Public gStarted As Boolean
Public gStartCounter As Currency
Public gFreq As Currency
Public gExportFolder As String

Private Const INITIAL_CAPACITY As Long = 8192

' ------------------------------------------------------------
Public Sub StartKeystrokeCapture()
    EnsureExportFolder
    frmKeystroke.Show vbModeless
End Sub

Public Sub EnsureExportFolder()
    Dim base As String
    base = Environ$("USERPROFILE") & "\Documents\KeystrokeSessions"
    If Dir$(base, vbDirectory) = "" Then
        MkDir base
    End If
    gExportFolder = base
End Sub

Public Sub InitSession(ByVal participantId As String, ByVal taskId As String)
    Dim ok As Long
    ok = QueryPerformanceFrequency(gFreq)
    If ok = 0 Or gFreq = 0 Then
        Err.Raise vbObjectError + 1, "modKeystroke", _
            "QueryPerformanceFrequency niedostępne na tym systemie."
    End If

    QueryPerformanceCounter gStartCounter

    gParticipantId = Trim$(participantId)
    gTaskId = Trim$(taskId)
    gSessionId = Format$(Now, "yyyymmdd_hhnnss") & "_" & SanitizeFilePart(gParticipantId)
    gEventCount = 0
    ReDim gEvents(0 To INITIAL_CAPACITY - 1)
    gStarted = True
End Sub

Public Sub StopSession()
    gStarted = False
End Sub

Public Sub ResetSessionBuffer()
    gEventCount = 0
    Erase gEvents
    ReDim gEvents(0 To INITIAL_CAPACITY - 1)
    gStarted = False
    gSessionId = ""
End Sub

Public Function ElapsedMsNow() As Double
    Dim nowCounter As Currency
    QueryPerformanceCounter nowCounter
    ' Currency scale: wynik w ms
    ElapsedMsNow = (CDbl(nowCounter - gStartCounter) / CDbl(gFreq)) * 1000#
End Function

Public Sub LogKeyEvent(ByVal eventType As String, ByVal keyCode As Integer, ByVal shiftState As Integer)
    Dim idx As Long
    Dim keyName As String

    If Not gStarted Then Exit Sub
    If keyCode = 0 Then Exit Sub

    ' Pomijamy samotne modyfikatory jako „znaki treści”
    ' (i tak zapisujemy Shift/Ctrl/Alt przy każdym evencie)
    keyName = KeyCodeToName(keyCode)

    If gEventCount > UBound(gEvents) Then
        ReDim Preserve gEvents(0 To UBound(gEvents) * 2 + 1)
    End If

    idx = gEventCount
    With gEvents(idx)
        .Seq = idx + 1
        .ElapsedMs = ElapsedMsNow()
        .EventType = eventType
        .KeyCode = keyCode
        .KeyName = keyName
        .Shift = (shiftState And 1) <> 0
        .Ctrl = (shiftState And 2) <> 0
        .Alt = (shiftState And 4) <> 0
    End With
    gEventCount = gEventCount + 1
End Sub

Public Function ExportSessionCsv( _
    ByVal typedText As String, _
    ByVal referenceText As String, _
    ByRef outPath As String) As Boolean

    Dim fNum As Integer
    Dim i As Long
    Dim path As String
    Dim metaPath As String
    Dim line As String

    On Error GoTo Fail

    EnsureExportFolder
    If Len(gSessionId) = 0 Then
        gSessionId = Format$(Now, "yyyymmdd_hhnnss") & "_nosession"
    End If

    path = gExportFolder & "\" & gSessionId & "_events.csv"
    metaPath = gExportFolder & "\" & gSessionId & "_meta.csv"

    fNum = FreeFile
    Open path For Output As #fNum
    Print #fNum, "seq,elapsed_ms,event_type,key_code,key_name,shift,ctrl,alt"
    For i = 0 To gEventCount - 1
        With gEvents(i)
            line = CStr(.Seq) & "," & _
                   FormatNumberInvariant(.ElapsedMs) & "," & _
                   .EventType & "," & _
                   CStr(.KeyCode) & "," & _
                   CsvEscape(.KeyName) & "," & _
                   Bool01(.Shift) & "," & _
                   Bool01(.Ctrl) & "," & _
                   Bool01(.Alt)
            Print #fNum, line
        End With
    Next i
    Close #fNum

    fNum = FreeFile
    Open metaPath For Output As #fNum
    Print #fNum, "field,value"
    Print #fNum, "session_id," & CsvEscape(gSessionId)
    Print #fNum, "participant_id," & CsvEscape(gParticipantId)
    Print #fNum, "task_id," & CsvEscape(gTaskId)
    Print #fNum, "started_at_local," & CsvEscape(Format$(Now, "yyyy-mm-dd hh:nn:ss"))
    Print #fNum, "event_count," & CStr(gEventCount)
    Print #fNum, "export_folder," & CsvEscape(gExportFolder)
    Print #fNum, "reference_text," & CsvEscape(referenceText)
    Print #fNum, "typed_text," & CsvEscape(typedText)
    Print #fNum, "char_count_typed," & CStr(Len(typedText))
    Print #fNum, "char_count_reference," & CStr(Len(referenceText))
    Close #fNum

    outPath = path
    ExportSessionCsv = True
    Exit Function

Fail:
    On Error Resume Next
    Close #fNum
    ExportSessionCsv = False
    outPath = "Błąd: " & Err.Description
End Function

' --- pomocnicze ---

Private Function FormatNumberInvariant(ByVal value As Double) As String
    ' Zawsze kropka jako separator dziesiętny (CSV przyjazny ML)
    FormatNumberInvariant = Replace$(Format$(value, "0.000"), ",", ".")
End Function

Private Function Bool01(ByVal v As Boolean) As String
    If v Then Bool01 = "1" Else Bool01 = "0"
End Function

Private Function CsvEscape(ByVal s As String) As String
    Dim t As String
    t = Replace$(s, """", """""")
    t = Replace$(t, vbCrLf, "\n")
    t = Replace$(t, vbCr, "\n")
    t = Replace$(t, vbLf, "\n")
    If InStr(t, ",") > 0 Or InStr(t, """") > 0 Or InStr(t, "\n") > 0 Then
        CsvEscape = """" & t & """"
    Else
        CsvEscape = t
    End If
End Function

Private Function SanitizeFilePart(ByVal s As String) As String
    Dim i As Long
    Dim ch As String
    Dim out As String
    s = Trim$(s)
    If Len(s) = 0 Then
        SanitizeFilePart = "anon"
        Exit Function
    End If
    For i = 1 To Len(s)
        ch = Mid$(s, i, 1)
        Select Case AscW(ch)
            Case 48 To 57, 65 To 90, 97 To 122, 45, 95
                out = out & ch
            Case Else
                out = out & "_"
        End Select
    Next i
    SanitizeFilePart = Left$(out, 40)
End Function

Public Function KeyCodeToName(ByVal keyCode As Integer) As String
    Select Case keyCode
        Case 8: KeyCodeToName = "Backspace"
        Case 9: KeyCodeToName = "Tab"
        Case 13: KeyCodeToName = "Enter"
        Case 16: KeyCodeToName = "Shift"
        Case 17: KeyCodeToName = "Ctrl"
        Case 18: KeyCodeToName = "Alt"
        Case 19: KeyCodeToName = "Pause"
        Case 20: KeyCodeToName = "CapsLock"
        Case 27: KeyCodeToName = "Escape"
        Case 32: KeyCodeToName = "Space"
        Case 33: KeyCodeToName = "PageUp"
        Case 34: KeyCodeToName = "PageDown"
        Case 35: KeyCodeToName = "End"
        Case 36: KeyCodeToName = "Home"
        Case 37: KeyCodeToName = "Left"
        Case 38: KeyCodeToName = "Up"
        Case 39: KeyCodeToName = "Right"
        Case 40: KeyCodeToName = "Down"
        Case 45: KeyCodeToName = "Insert"
        Case 46: KeyCodeToName = "Delete"
        Case 48 To 57: KeyCodeToName = Chr$(keyCode)          ' 0-9
        Case 65 To 90: KeyCodeToName = Chr$(keyCode)          ' A-Z
        Case 96 To 105: KeyCodeToName = "Num" & CStr(keyCode - 96)
        Case 106: KeyCodeToName = "NumMul"
        Case 107: KeyCodeToName = "NumAdd"
        Case 109: KeyCodeToName = "NumSub"
        Case 110: KeyCodeToName = "NumDot"
        Case 111: KeyCodeToName = "NumDiv"
        Case 112 To 123: KeyCodeToName = "F" & CStr(keyCode - 111)
        Case 144: KeyCodeToName = "NumLock"
        Case 186: KeyCodeToName = ";"
        Case 187: KeyCodeToName = "="
        Case 188: KeyCodeToName = ","
        Case 189: KeyCodeToName = "-"
        Case 190: KeyCodeToName = "."
        Case 191: KeyCodeToName = "/"
        Case 192: KeyCodeToName = "`"
        Case 219: KeyCodeToName = "["
        Case 220: KeyCodeToName = "\"
        Case 221: KeyCodeToName = "]"
        Case 222: KeyCodeToName = "'"
        Case Else: KeyCodeToName = "VK_" & CStr(keyCode)
    End Select
End Function

Public Function DefaultTaskText(ByVal taskId As String) As String
    Select Case UCase$(Trim$(taskId))
        Case "A", "TEXT_A"
            DefaultTaskText = _
                "Analiza dynamiki wprowadzania tekstu pozwala badać indywidualne cechy " & _
                "pisania na klawiaturze. Mierzone są czasy naciskania i zwalniania klawiszy, " & _
                "odstępy między znakami oraz tempo pracy. Celem jest sprawdzenie, czy na " & _
                "podstawie tych wzorców można rozpoznać autora tekstu."
        Case "B", "TEXT_B"
            DefaultTaskText = _
                "Komputerowa analiza charakteru pisma nie dotyczy wyglądu liter, lecz " & _
                "sposobu ich wprowadzania. Każda osoba ma charakterystyczny rytm, " & _
                "częstotliwość poprawek oraz sposób korzystania z klawiszy specjalnych. " & _
                "Zebrane dane posłużą do trenowania modeli uczenia maszynowego."
        Case "C", "TEXT_C"
            DefaultTaskText = _
                "W ramach badania proszę przepisać ten akapit uważnie i naturalnym tempem. " & _
                "Nie należy się spieszyć. W razie pomyłki wolno użyć Backspace. " & _
                "Liczby do wpisania: 12, 34 oraz 56. Adres przykładowy: ul. Kwiatowa 7."
        Case Else
            DefaultTaskText = _
                "Proszę przepisać ten tekst naturalnym tempem, bez pośpiechu. " & _
                "Poprawki są dozwolone. Sesja zostanie zapisana do pliku CSV."
    End Select
End Function
