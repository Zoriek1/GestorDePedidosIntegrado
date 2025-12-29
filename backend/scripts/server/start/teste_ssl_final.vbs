' Teste final para verificar SSL
Option Explicit

Dim objFSO
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Caminho fixo para teste
Dim backendDir
backendDir = "C:\Gestor de Pedidos Plante uma flor\backend"

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

msg = "TESTE SSL - CAMINHO FIXO" & vbCrLf & vbCrLf & _
      "BackendDir: " & backendDir & vbCrLf & vbCrLf & _
      "CertPath: " & certPath & vbCrLf & _
      "Cert existe: " & certStatus & vbCrLf & vbCrLf & _
      "KeyPath: " & keyPath & vbCrLf & _
      "Key existe: " & keyStatus

MsgBox msg, vbInformation, "Teste SSL Final"

