' Script VBS para parar servidor de produção silencioso
' Lê o PID do arquivo e encerra o processo

Option Explicit

Dim fso, shell, currentDir, backendDir, pidFile, logFile
Dim pid, pidContent, processCheck

' Obter diretório do script
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
backendDir = currentDir & "\backend"
pidFile = backendDir & "\servidor.pid"
logFile = backendDir & "\servidor_producao.log"

Set shell = CreateObject("WScript.Shell")

' Verificar se arquivo PID existe
If Not fso.FileExists(pidFile) Then
    ' Tentar encontrar processo pela porta 5000
    Dim netstatOutput, lines, line, parts, foundPid
    foundPid = 0
    
    On Error Resume Next
    netstatOutput = shell.Exec("netstat -ano").StdOut.ReadAll
    lines = Split(netstatOutput, vbCrLf)
    For Each line In lines
        If InStr(line, ":5000") > 0 And InStr(line, "LISTENING") > 0 Then
            parts = Split(Trim(line))
            If UBound(parts) >= 4 Then
                foundPid = CLng(parts(UBound(parts)))
                Exit For
            End If
        End If
    Next
    On Error Goto 0
    
    If foundPid = 0 Then
        WScript.Quit 0
    End If
    
    pid = foundPid
Else
    ' Ler PID do arquivo
    On Error Resume Next
    Dim pidFileObj
    Set pidFileObj = fso.OpenTextFile(pidFile, 1)
    pid = CLng(Trim(pidFileObj.ReadAll))
    pidFileObj.Close
    On Error Goto 0
End If

' Verificar se processo existe
On Error Resume Next
processCheck = shell.Run("tasklist /FI ""PID eq " & pid & """ 2>nul | find /I """ & pid & """", 0, True)
On Error Goto 0

If processCheck <> 0 Then
    ' Remover arquivo PID se existir
    If fso.FileExists(pidFile) Then
        fso.DeleteFile pidFile, True
    End If
    WScript.Quit 0
End If

' Parar processo
On Error Resume Next
shell.Run "taskkill /PID " & pid & " /F", 0, True
On Error Goto 0

' Verificar se processo foi encerrado
WScript.Sleep 1000
On Error Resume Next
processCheck = shell.Run("tasklist /FI ""PID eq " & pid & """ 2>nul | find /I """ & pid & """", 0, True)
On Error Goto 0

If processCheck = 0 Then
    WScript.Quit 1
End If

' Remover arquivo PID
If fso.FileExists(pidFile) Then
    fso.DeleteFile pidFile, True
End If

WScript.Quit 0
