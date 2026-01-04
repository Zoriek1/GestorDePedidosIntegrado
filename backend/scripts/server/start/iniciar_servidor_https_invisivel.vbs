' ===================================================
' PLANTE UMA FLOR - Iniciar Servidor HTTPS Invisível
' Inicia o servidor Flask em modo invisível (sem janela)
' ===================================================

Option Explicit

' Obter diretório do script e calcular caminho do backend
Dim fso, scriptPath, backendPath, logPath
Set fso = CreateObject("Scripting.FileSystemObject")

' Obter caminho completo do script (já trata espaços corretamente)
scriptPath = fso.GetParentFolderName(WScript.ScriptFullName)

' O script está em: backend/scripts/server/start/
' Precisamos subir 3 níveis para chegar ao backend
' start -> server -> scripts -> backend
' Usar GetParentFolderName que funciona melhor com caminhos com espaços
backendPath = fso.GetParentFolderName(fso.GetParentFolderName(fso.GetParentFolderName(scriptPath)))
logPath = backendPath & "\servidor_https.log"

' Verificar se o caminho está correto (verificar se main.py existe)
If Not fso.FileExists(backendPath & "\main.py") Then
    ' Mostrar erro com caminhos para debug
    MsgBox "Erro ao localizar diretório do backend!" & vbCrLf & vbCrLf & _
           "Script: " & WScript.ScriptFullName & vbCrLf & _
           "Caminho calculado: " & backendPath & vbCrLf & vbCrLf & _
           "main.py não encontrado neste caminho.", _
           vbCritical, "Erro - Plante Uma Flor"
    WScript.Quit
End If

' Verificar se Python está disponível
Dim shell, pythonCheck, pythonPath
Set shell = CreateObject("WScript.Shell")
' Tentar encontrar Python
pythonCheck = shell.Run("cmd.exe /c where python >nul 2>&1", 0, True)

If pythonCheck <> 0 Then
    ' Tentar pythonw (Python sem janela)
    pythonCheck = shell.Run("cmd.exe /c where pythonw >nul 2>&1", 0, True)
    If pythonCheck = 0 Then
        pythonPath = "pythonw"
    Else
        ' Python não encontrado, mostrar erro
        MsgBox "Python não encontrado no PATH!" & vbCrLf & vbCrLf & _
               "Certifique-se de que o Python está instalado.", _
               vbCritical, "Erro - Plante Uma Flor"
        WScript.Quit
    End If
Else
    pythonPath = "python"
End If

' Verificar se certificados existem
Dim certPath, keyPath, certFound
certPath = backendPath & "\instance\ssl\cert.pem"
keyPath = backendPath & "\instance\ssl\key.pem"
certFound = False

' Verificar primeiro em instance/ssl (local novo)
If fso.FileExists(certPath) And fso.FileExists(keyPath) Then
    certFound = True
Else
    ' Tentar local antigo (config/ssl)
    certPath = backendPath & "\config\ssl\cert.pem"
    keyPath = backendPath & "\config\ssl\key.pem"
    If fso.FileExists(certPath) And fso.FileExists(keyPath) Then
        certFound = True
    End If
End If

If Not certFound Then
    Dim errorMsg
    errorMsg = "Certificados SSL não encontrados!" & vbCrLf & vbCrLf
    errorMsg = errorMsg & "Procurados em:" & vbCrLf
    errorMsg = errorMsg & "  - " & backendPath & "\instance\ssl\cert.pem" & vbCrLf
    errorMsg = errorMsg & "  - " & backendPath & "\config\ssl\cert.pem" & vbCrLf & vbCrLf
    errorMsg = errorMsg & "Execute primeiro:" & vbCrLf
    errorMsg = errorMsg & "1. scripts\ssl\INSTALAR_MKCERT.bat" & vbCrLf
    errorMsg = errorMsg & "2. scripts\ssl\GERAR_CERTIFICADOS_AUTO.bat"
    MsgBox errorMsg, vbCritical, "Erro - Plante Uma Flor"
    WScript.Quit
End If

' Criar objeto para executar comando
Dim command, exec, workingDir
' Garantir que o diretório de trabalho está correto
workingDir = backendPath

' Construir comando completo
' Usar pythonw se disponível para não mostrar janela, senão usar python
command = "cmd.exe /c cd /d """ & workingDir & """ && " & pythonPath & " main.py --https --no-reload >> """ & logPath & """ 2>&1"

' Executar em modo invisível (0 = oculto, bWaitOnReturn = False para não bloquear)
' Usar CreateObject("WScript.Shell").Run com windowStyle = 0 (oculto)
exec = shell.Run(command, 0, False)

' Verificar se servidor iniciou (porta 5000) - fazer múltiplas tentativas
Dim portCheck, portCheckCmd, maxAttempts, attempt, serverStarted
maxAttempts = 5
attempt = 0
serverStarted = False

' Verificação mais simples (sem LISTENING para evitar problemas)
portCheckCmd = "cmd.exe /c netstat -ano | findstr :5000 >nul 2>&1"

Do While attempt < maxAttempts And Not serverStarted
    ' Aguardar antes de verificar (aumentar tempo a cada tentativa)
    WScript.Sleep 2000 + (attempt * 500)
    
    portCheck = shell.Run(portCheckCmd, 0, True)
    
    If portCheck = 0 Then
        ' Porta encontrada, fazer verificação adicional mais específica
        Dim listenCheck
        listenCheck = shell.Run("cmd.exe /c netstat -ano | findstr :5000 | findstr /C:LISTENING >nul 2>&1", 0, True)
        If listenCheck = 0 Then
            serverStarted = True
        End If
    End If
    
    attempt = attempt + 1
Loop

If serverStarted Then
    ' Servidor iniciou com sucesso
    shell.Popup "Servidor HTTPS iniciado com sucesso!" & vbCrLf & vbCrLf & _
                "Acesse: https://localhost:5000" & vbCrLf & vbCrLf & _
                "Log: " & logPath, _
                3, "Servidor Iniciado - Plante Uma Flor", vbInformation
Else
    ' Verificar se há erro no log antes de mostrar mensagem
    Dim logError, logContent, logFile, logLines, i, lastLines, startLine
    logError = False
    If fso.FileExists(logPath) Then
        ' Tentar ler últimas linhas do log para ver se há erro
        On Error Resume Next
        Set logFile = fso.OpenTextFile(logPath, 1)
        If Err.Number = 0 Then
            ' Ler últimas linhas (últimas 10)
            logLines = Split(logFile.ReadAll, vbCrLf)
            logFile.Close
            
            ' Pegar últimas 10 linhas
            lastLines = ""
            If UBound(logLines) >= 0 Then
                startLine = UBound(logLines) - 9
                If startLine < 0 Then startLine = 0
                For i = startLine To UBound(logLines)
                    If Len(logLines(i)) > 0 Then
                        lastLines = lastLines & logLines(i) & vbCrLf
                        ' Verificar se há palavras-chave de erro
                        If InStr(LCase(logLines(i)), "error") > 0 Or _
                           InStr(LCase(logLines(i)), "erro") > 0 Or _
                           InStr(LCase(logLines(i)), "exception") > 0 Or _
                           InStr(LCase(logLines(i)), "traceback") > 0 Then
                            logError = True
                        End If
                    End If
                Next
            End If
            Set logFile = Nothing
        End If
        On Error GoTo 0
    End If
    
    errorMsg = "Não foi possível confirmar se o servidor iniciou." & vbCrLf & vbCrLf
    errorMsg = errorMsg & "O servidor pode estar iniciando ainda ou houve um erro." & vbCrLf & vbCrLf
    errorMsg = errorMsg & "Verifique o log: " & logPath & vbCrLf & vbCrLf
    If logError Then
        errorMsg = errorMsg & "ATENÇÃO: Erros foram detectados no log!" & vbCrLf
    End If
    errorMsg = errorMsg & vbCrLf & "Tente acessar: https://localhost:5000"
    
    shell.Popup errorMsg, _
                8, "Aviso - Plante Uma Flor", vbExclamation
End If

' Limpar objetos
Set fso = Nothing
Set shell = Nothing

