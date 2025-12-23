' ====================================================
' Plante Uma Flor - PWA v3.0
' Script VBS para iniciar o servidor TOTALMENTE invisível
' (Sem janela, sem notificação)
' ====================================================

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Obter o diretório do script (backend/UtilsScripts)
scriptPath = fso.GetParentFolderName(WScript.ScriptFullName)

' Obter o diretório do backend (um nível acima)
backendPath = fso.GetParentFolderName(scriptPath)

' Verificar se já está rodando
Set objWMIService = GetObject("winmgmts:\\.\root\cimv2")
Set colProcesses = objWMIService.ExecQuery("SELECT * FROM Win32_Process WHERE Name = 'python.exe' AND CommandLine LIKE '%main.py%'")

If colProcesses.Count > 0 Then
    ' Servidor já está rodando - não fazer nada
    WScript.Quit
End If

' Mudar para o diretório do backend
WshShell.CurrentDirectory = backendPath

' Iniciar o servidor TOTALMENTE invisível
' 0 = Janela oculta, False = Não aguardar término
WshShell.Run "python main.py", 0, False

' Aguardar 3 segundos para o servidor iniciar
WScript.Sleep 3000

' Abrir o navegador (opcional - remova se não quiser)
' WshShell.Run "http://localhost:5000", 1, False

WScript.Quit

