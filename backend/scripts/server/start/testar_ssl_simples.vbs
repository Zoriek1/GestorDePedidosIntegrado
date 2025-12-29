' Script simples para testar se certificados são encontrados
Option Explicit

Dim objFSO, backendDir
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Caminho do backend (ajuste se necessário)
backendDir = "C:\Gestor de Pedidos Plante uma flor\backend"

Dim certPath, keyPath
certPath = objFSO.BuildPath(objFSO.BuildPath(objFSO.BuildPath(backendDir, "instance"), "ssl"), "cert.pem")
keyPath = objFSO.BuildPath(objFSO.BuildPath(objFSO.BuildPath(backendDir, "instance"), "ssl"), "key.pem")

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

msg = "TESTE SSL SIMPLES" & vbCrLf & vbCrLf & _
      "BackendDir: " & backendDir & vbCrLf & vbCrLf & _
      "CertPath: " & certPath & vbCrLf & _
      "Cert existe: " & certStatus & vbCrLf & vbCrLf & _
      "KeyPath: " & keyPath & vbCrLf & _
      "Key existe: " & keyStatus

MsgBox msg, vbInformation, "Teste SSL"

