' Script de diagnóstico para SSL
Option Explicit

Dim objFSO, objShell
Set objFSO = CreateObject("Scripting.FileSystemObject")
Set objShell = CreateObject("WScript.Shell")

' Obter diretório do script
Dim scriptDir, backendDir, tempDir
scriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Calcular backendDir (3 níveis acima)
tempDir = objFSO.GetParentFolderName(scriptDir)  ' server
tempDir = objFSO.GetParentFolderName(tempDir)     ' scripts
backendDir = objFSO.GetParentFolderName(tempDir)  ' backend

' Garantir caminho absoluto
If Not objFSO.FolderExists(backendDir) Then
    backendDir = objFSO.GetAbsolutePathName(backendDir)
End If

' Construir caminhos
Dim certPath, keyPath
certPath = objFSO.BuildPath(objFSO.BuildPath(objFSO.BuildPath(backendDir, "instance"), "ssl"), "cert.pem")
keyPath = objFSO.BuildPath(objFSO.BuildPath(objFSO.BuildPath(backendDir, "instance"), "ssl"), "key.pem")

' Verificar existência
Dim certExists, keyExists
certExists = objFSO.FileExists(certPath)
keyExists = objFSO.FileExists(keyPath)

' Verificar diretórios
Dim instanceDir, instanceSslDir
instanceDir = objFSO.BuildPath(backendDir, "instance")
instanceSslDir = objFSO.BuildPath(instanceDir, "ssl")

Dim instanceDirExists, instanceSslDirExists
instanceDirExists = objFSO.FolderExists(instanceDir)
instanceSslDirExists = objFSO.FolderExists(instanceSslDir)

' Construir mensagem de diagnóstico
Dim msg, backendExists, instanceDirStatus, instanceSslDirStatus, certStatus, keyStatus

If objFSO.FolderExists(backendDir) Then
    backendExists = "SIM"
Else
    backendExists = "NÃO"
End If

If instanceDirExists Then
    instanceDirStatus = "SIM"
Else
    instanceDirStatus = "NÃO"
End If

If instanceSslDirExists Then
    instanceSslDirStatus = "SIM"
Else
    instanceSslDirStatus = "NÃO"
End If

If certExists Then
    certStatus = "SIM"
Else
    certStatus = "NÃO"
End If

If keyExists Then
    keyStatus = "SIM"
Else
    keyStatus = "NÃO"
End If

msg = "DIAGNÓSTICO SSL" & vbCrLf & vbCrLf & _
      "ScriptDir: " & scriptDir & vbCrLf & _
      "BackendDir: " & backendDir & vbCrLf & _
      "BackendDir existe: " & backendExists & vbCrLf & vbCrLf & _
      "instanceDir: " & instanceDir & vbCrLf & _
      "instanceDir existe: " & instanceDirStatus & vbCrLf & vbCrLf & _
      "instanceSslDir: " & instanceSslDir & vbCrLf & _
      "instanceSslDir existe: " & instanceSslDirStatus & vbCrLf & vbCrLf & _
      "certPath: " & certPath & vbCrLf & _
      "cert existe: " & certStatus & vbCrLf & vbCrLf & _
      "keyPath: " & keyPath & vbCrLf & _
      "key existe: " & keyStatus

MsgBox msg, vbInformation, "Diagnóstico SSL"

' Salvar em arquivo também
Dim logFile, objFile
logFile = objFSO.BuildPath(backendDir, "diagnostico_ssl.txt")
Set objFile = objFSO.CreateTextFile(logFile, True)
objFile.WriteLine "DIAGNÓSTICO SSL - " & Now()
objFile.WriteLine ""
objFile.WriteLine "ScriptDir: " & scriptDir
objFile.WriteLine "BackendDir: " & backendDir
objFile.WriteLine "BackendDir existe: " & backendExists
objFile.WriteLine ""
objFile.WriteLine "instanceDir: " & instanceDir
objFile.WriteLine "instanceDir existe: " & instanceDirStatus
objFile.WriteLine ""
objFile.WriteLine "instanceSslDir: " & instanceSslDir
objFile.WriteLine "instanceSslDir existe: " & instanceSslDirStatus
objFile.WriteLine ""
objFile.WriteLine "certPath: " & certPath
objFile.WriteLine "cert existe: " & certStatus
objFile.WriteLine ""
objFile.WriteLine "keyPath: " & keyPath
objFile.WriteLine "key existe: " & keyStatus
objFile.Close

MsgBox "Diagnóstico salvo em: " & logFile, vbInformation, "Diagnóstico SSL"

