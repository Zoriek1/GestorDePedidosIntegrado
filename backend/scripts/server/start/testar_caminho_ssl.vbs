' Script de teste para verificar caminho dos certificados SSL
Option Explicit

Dim objFSO, scriptDir, backendDir, tempDir
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Obter diretório do script
scriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Obter diretório do backend (3 níveis acima)
tempDir = objFSO.GetParentFolderName(scriptDir)  ' server
tempDir = objFSO.GetParentFolderName(tempDir)     ' scripts
backendDir = objFSO.GetParentFolderName(tempDir)  ' backend

Dim certPath, keyPath
certPath = backendDir & "\instance\ssl\cert.pem"
keyPath = backendDir & "\instance\ssl\key.pem"

Dim certExists, keyExists
certExists = objFSO.FileExists(certPath)
keyExists = objFSO.FileExists(keyPath)

Dim msg, certStatus, keyStatus
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

msg = "TESTE DE CAMINHO SSL" & vbCrLf & vbCrLf & _
      "ScriptDir: " & scriptDir & vbCrLf & _
      "BackendDir: " & backendDir & vbCrLf & vbCrLf & _
      "CertPath: " & certPath & vbCrLf & _
      "Cert existe: " & certStatus & vbCrLf & vbCrLf & _
      "KeyPath: " & keyPath & vbCrLf & _
      "Key existe: " & keyStatus

MsgBox msg, vbInformation, "Teste SSL"

