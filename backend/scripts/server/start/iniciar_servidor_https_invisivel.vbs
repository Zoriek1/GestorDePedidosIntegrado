' ===================================================
' PLANTE UMA FLOR - Iniciar Servidor HTTPS Invisível
' Inicia o servidor Flask em HTTPS sem janela visível
' ===================================================

Option Explicit

Dim objShell, scriptDir, backendDir, pythonCmd, strCommand

' Criar objeto Shell
Set objShell = CreateObject("WScript.Shell")

' Obter diretório do script (backend/scripts/server/start)
Dim objFSO
Set objFSO = CreateObject("Scripting.FileSystemObject")
scriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Obter diretório do backend (3 níveis acima: start -> server -> scripts -> backend)
' scriptDir = backend/scripts/server/start
' Nível 1: backend/scripts/server
' Nível 2: backend/scripts
' Nível 3: backend
Dim tempDir
tempDir = objFSO.GetParentFolderName(scriptDir)  ' server
tempDir = objFSO.GetParentFolderName(tempDir)     ' scripts
backendDir = objFSO.GetParentFolderName(tempDir)  ' backend

' Garantir que backendDir é um caminho absoluto e válido
If Not objFSO.FolderExists(backendDir) Then
    ' Tentar método alternativo: usar GetAbsolutePathName
    backendDir = objFSO.GetAbsolutePathName(backendDir)
End If

' Verificar se backendDir contém "backend" (validação adicional)
If InStr(LCase(backendDir), "backend") = 0 Then
    ' Se não contém "backend", tentar encontrar manualmente
    ' Procurar por main.py no diretório atual e subir até encontrar
    Dim searchDir, foundBackend
    searchDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
    foundBackend = False
    
    ' Subir até 5 níveis procurando por main.py
    Dim i
    For i = 1 To 5
        If objFSO.FileExists(objFSO.BuildPath(searchDir, "main.py")) Then
            backendDir = searchDir
            foundBackend = True
            Exit For
        End If
        searchDir = objFSO.GetParentFolderName(searchDir)
    Next
    
    If Not foundBackend Then
        MsgBox "Não foi possível encontrar o diretório do backend!" & vbCrLf & vbCrLf & _
               "BackendDir calculado: " & backendDir, _
               vbCritical, "Plante Uma Flor - Erro"
        WScript.Quit 1
    End If
End If

' Definir diretório de trabalho
objShell.CurrentDirectory = backendDir

' Verificar se certificados existem
' NOTA: Certificados agora estão em instance/ssl/ (não em config/ssl/)
Dim fso
Set fso = CreateObject("Scripting.FileSystemObject")

' Construir caminhos absolutos para os certificados
Dim certPath, keyPath
Dim instancePath, sslPath
instancePath = objFSO.BuildPath(backendDir, "instance")
sslPath = objFSO.BuildPath(instancePath, "ssl")
certPath = objFSO.BuildPath(sslPath, "cert.pem")
keyPath = objFSO.BuildPath(sslPath, "key.pem")

' Normalizar caminhos (converter para caminho absoluto)
' NOTA: GetAbsolutePathName pode falhar se arquivo não existe, então usar com cuidado
On Error Resume Next
If objFSO.FolderExists(sslPath) Then
    certPath = objFSO.GetAbsolutePathName(certPath)
    keyPath = objFSO.GetAbsolutePathName(keyPath)
End If
On Error GoTo 0

' Verificar se diretório instance/ssl existe, se não, criar
Dim instanceDir, instanceSslDir
instanceDir = objFSO.BuildPath(backendDir, "instance")
instanceSslDir = objFSO.BuildPath(instanceDir, "ssl")

If Not fso.FolderExists(instanceSslDir) Then
    If Not fso.FolderExists(instanceDir) Then
        fso.CreateFolder(instanceDir)
    End If
    fso.CreateFolder(instanceSslDir)
End If

' Verificar se certificados existem no novo local (instance/ssl/)
Dim certExists, keyExists
certExists = fso.FileExists(certPath)
keyExists = fso.FileExists(keyPath)

' DEBUG: Descomentar para ver caminhos (remover após resolver problema)
' Dim debugCertStatus, debugKeyStatus
' If certExists Then debugCertStatus = "SIM" Else debugCertStatus = "NÃO" End If
' If keyExists Then debugKeyStatus = "SIM" Else debugKeyStatus = "NÃO" End If
' MsgBox "DEBUG SSL:" & vbCrLf & vbCrLf & _
'        "BackendDir: " & backendDir & vbCrLf & _
'        "CertPath: " & certPath & vbCrLf & _
'        "Cert existe: " & debugCertStatus & vbCrLf & _
'        "KeyPath: " & keyPath & vbCrLf & _
'        "Key existe: " & debugKeyStatus, vbInformation, "Debug SSL"

If Not certExists Or Not keyExists Then
    ' Fallback: verificar no local antigo (config/ssl/) para compatibilidade
    Dim oldCertPath, oldKeyPath
    oldCertPath = objFSO.BuildPath(objFSO.BuildPath(objFSO.BuildPath(backendDir, "config"), "ssl"), "cert.pem")
    oldKeyPath = objFSO.BuildPath(objFSO.BuildPath(objFSO.BuildPath(backendDir, "config"), "ssl"), "key.pem")
    
    Dim oldCertExists, oldKeyExists
    oldCertExists = fso.FileExists(oldCertPath)
    oldKeyExists = fso.FileExists(oldKeyPath)
    
    If oldCertExists And oldKeyExists Then
        ' Certificados encontrados no local antigo - tentar copiar para novo local
        On Error Resume Next
        fso.CopyFile oldCertPath, certPath, True
        fso.CopyFile oldKeyPath, keyPath, True
        On Error GoTo 0
        
        ' Verificar se cópia foi bem-sucedida
        If fso.FileExists(certPath) And fso.FileExists(keyPath) Then
            ' Sucesso - certificados copiados automaticamente
            ' Continuar normalmente
        Else
            ' Falha na cópia - informar usuário
            MsgBox "Certificados SSL encontrados no local antigo (config\ssl\)!" & vbCrLf & vbCrLf & _
                   "Tentativa de copiar para instance\ssl\ falhou." & vbCrLf & vbCrLf & _
                   "Por favor, mova manualmente:" & vbCrLf & _
                   "move config\ssl\cert.pem instance\ssl\cert.pem" & vbCrLf & _
                   "move config\ssl\key.pem instance\ssl\key.pem" & vbCrLf & vbCrLf & _
                   "Ou gere novos certificados:" & vbCrLf & _
                   "1. scripts\ssl\INSTALAR_MKCERT.bat" & vbCrLf & _
                   "2. scripts\ssl\GERAR_CERTIFICADOS_AUTO.bat", _
                   vbExclamation, "Plante Uma Flor - Aviso"
            WScript.Quit 1
        End If
    Else
        ' Certificados não encontrados em nenhum local
        Dim errorMsg, certStatus, keyStatus
        If certExists Then
            certStatus = "OK"
        Else
            certStatus = "NÃO ENCONTRADO"
        End If
        
        If keyExists Then
            keyStatus = "OK"
        Else
            keyStatus = "NÃO ENCONTRADO"
        End If
        
        errorMsg = "Certificados SSL não encontrados!" & vbCrLf & vbCrLf & _
                   "Procurados em:" & vbCrLf & _
                   "  - " & certPath & vbCrLf & _
                   "    Status: " & certStatus & vbCrLf & _
                   "  - " & keyPath & vbCrLf & _
                   "    Status: " & keyStatus & vbCrLf & vbCrLf & _
                   "BackendDir: " & backendDir & vbCrLf & vbCrLf & _
                   "Execute primeiro:" & vbCrLf & _
                   "1. scripts\ssl\INSTALAR_MKCERT.bat" & vbCrLf & _
                   "2. scripts\ssl\GERAR_CERTIFICADOS_AUTO.bat" & vbCrLf & vbCrLf & _
                   "Os certificados serão salvos em: instance\ssl\"
        MsgBox errorMsg, vbCritical, "Plante Uma Flor - Erro"
        WScript.Quit 1
    End If
End If

' Tentar encontrar Python
pythonCmd = "python"

' Verificar se python está disponível
Dim result
result = objShell.Run("cmd /c where python > nul 2>&1", 0, True)

If result <> 0 Then
    ' Tentar py launcher
    result = objShell.Run("cmd /c where py > nul 2>&1", 0, True)
    If result = 0 Then
        pythonCmd = "py"
    Else
        MsgBox "Python não encontrado!" & vbCrLf & vbCrLf & _
               "Certifique-se de que o Python está instalado e no PATH.", _
               vbCritical, "Plante Uma Flor - Erro"
        WScript.Quit 1
    End If
End If

' Criar comando para iniciar o servidor com encoding UTF-8 e log
' Definir variáveis de ambiente para UTF-8
Dim logFile
logFile = backendDir & "\servidor_https.log"

' Comando com encoding UTF-8, sem reloader (mais estável) e redirecionamento de saída
strCommand = "cmd /c ""chcp 65001 >nul 2>&1 && cd /d """ & backendDir & """ && " & _
             "set PYTHONIOENCODING=utf-8 && " & _
             "set NO_RELOAD=true && " & _
             pythonCmd & " main.py --https --no-reload > """ & logFile & """ 2>&1"""

' Executar em modo oculto (0 = janela oculta, False = não esperar conclusão)
objShell.Run strCommand, 0, False

' Aguardar 5 segundos para o servidor iniciar completamente
WScript.Sleep 5000

' Verificar se o servidor realmente iniciou (verificando o log)
Dim objFSO2, objFile, strLogContent
Set objFSO2 = CreateObject("Scripting.FileSystemObject")

If objFSO2.FileExists(logFile) Then
    On Error Resume Next
    Set objFile = objFSO2.OpenTextFile(logFile, 1)
    strLogContent = objFile.ReadAll
    objFile.Close
    On Error GoTo 0
    
    ' Verificar se há indicação de erro no log
    If InStr(strLogContent, "Erro") > 0 Or InStr(strLogContent, "Error") > 0 Then
        MsgBox "Servidor iniciado mas pode haver problemas!" & vbCrLf & vbCrLf & _
               "Verifique o log para detalhes:" & vbCrLf & _
               "backend\servidor_https.log", _
               vbExclamation, "Plante Uma Flor - Aviso"
    Else
        ' Mostrar notificação de sucesso
        On Error Resume Next
        Dim objNotify
        Set objNotify = CreateObject("WScript.Shell")
        objNotify.Popup "Servidor HTTPS iniciado com sucesso!" & vbCrLf & vbCrLf & _
                        "Acesse: https://localhost:5000" & vbCrLf & _
                        "ou https://Gestor-pedidos.local:5000" & vbCrLf & vbCrLf & _
                        "Log: backend\servidor_https.log", _
                        6, "Plante Uma Flor", vbInformation
        On Error GoTo 0
    End If
Else
    MsgBox "Servidor iniciado mas log nao encontrado!" & vbCrLf & vbCrLf & _
           "Verifique se o servidor esta funcionando:" & vbCrLf & _
           "https://localhost:5000", _
           vbExclamation, "Plante Uma Flor - Aviso"
End If

' Limpar objetos
Set objShell = Nothing
Set fso = Nothing

WScript.Quit 0


