' Script VBS para iniciar servidor de produção de forma silenciosa
' Executa wsgi.py sem abrir janela do CMD e sem interação

Option Explicit

Dim fso, shell, currentDir, backendDir, logFile, pidFile
Dim pythonPath, wsgiPath, process

' Obter diretório do script
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
backendDir = currentDir & "\backend"
logFile = backendDir & "\servidor_producao.log"
pidFile = backendDir & "\servidor.pid"

Set shell = CreateObject("WScript.Shell")

' Verificar se wsgi.py existe
wsgiPath = backendDir & "\wsgi.py"
If Not fso.FileExists(wsgiPath) Then
    WScript.Quit 1
End If

' Verificar se Python está instalado
On Error Resume Next
pythonPath = shell.ExpandEnvironmentStrings("%COMSPEC%")
Dim pythonCheck
pythonCheck = shell.Run("python --version", 0, True)
If pythonCheck <> 0 Then
    WScript.Quit 1
End If
On Error Goto 0

' Verificar se Waitress está instalado
On Error Resume Next
Dim waitressCheck
waitressCheck = shell.Run("python -c ""import waitress""", 0, True)
If waitressCheck <> 0 Then
    shell.Run "pip install waitress", 0, True
    ' Verificar novamente após instalação
    waitressCheck = shell.Run("python -c ""import waitress""", 0, True)
    If waitressCheck <> 0 Then
        WScript.Quit 1
    End If
End If
On Error Goto 0

' Configurar variáveis de ambiente para produção
shell.Environment("PROCESS")("FLASK_ENV") = "production"
shell.Environment("PROCESS")("FORCE_START") = "true"

' Iniciar servidor em background sem janela
' Usando Run com 0 (oculto) e redirecionando output para log
Dim command
command = "python """ & wsgiPath & """ > """ & logFile & """ 2>&1"

' Executar em background (0 = oculto, False = não aguardar)
Dim processId
On Error Resume Next
processId = shell.Run(command, 0, False)
On Error Goto 0

If processId = 0 Then
    WScript.Quit 1
End If

' Aguardar um pouco para o servidor iniciar
WScript.Sleep 5000

' Tentar encontrar PID pela porta 5000 (mais confiável)
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

' Se não encontrou pela porta, usar o processId retornado pelo Run
If foundPid = 0 Then
    foundPid = processId
End If

' Verificar se processo existe
On Error Resume Next
Dim processCheck
processCheck = shell.Run("tasklist /FI ""PID eq " & foundPid & """ 2>nul | find /I """ & foundPid & """", 0, True)
On Error Goto 0

If processCheck <> 0 Then
    WScript.Quit 1
End If

' Salvar PID em arquivo
Dim pidFileObj
Set pidFileObj = fso.CreateTextFile(pidFile, True)
pidFileObj.Write foundPid
pidFileObj.Close

WScript.Quit 0
