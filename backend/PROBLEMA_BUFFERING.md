# Problema: Output não aparece até Ctrl+C (Buffering)

## Sintoma

O servidor inicia, mas as mensagens só aparecem quando você pressiona Ctrl+C.

## Causa

O Python está usando **buffering** no output, então as mensagens ficam armazenadas em memória até o buffer ser esvaziado (flush).

## Solução 1: Usar script com -u (RECOMENDADO)

Use o script `iniciar_servidor.bat`:

```batch
cd backend
iniciar_servidor.bat
```

Ou execute diretamente com `-u`:

```batch
cd backend
python -u wsgi.py
```

O parâmetro `-u` desabilita o buffering.

## Solução 2: Variável de ambiente

Configure a variável de ambiente antes de executar:

```batch
set PYTHONUNBUFFERED=1
cd backend
python wsgi.py
```

Ou no PowerShell:

```powershell
$env:PYTHONUNBUFFERED=1
cd backend
python wsgi.py
```

## Solução 3: Usar o script automatizado

O script `iniciar_producao_completo.bat` já faz isso corretamente:

```batch
cd "c:\Gestor de Pedidos Plante uma flor"
iniciar_producao_completo.bat
```

## Mudanças feitas

1. **Adicionado `flush=True`** em todos os prints no `wsgi.py`
2. **Configurado `line_buffering=True`** no stdout/stderr para Windows
3. **Criado `iniciar_servidor.bat`** que usa `-u` automaticamente

## Verificação

Após iniciar, você deve ver imediatamente:

```
============================================================
PLANTE UMA FLOR - PWA v3.0 (PRODUÇÃO)
============================================================
...
[INFO] Iniciando Waitress...
[INFO] Escutando em 0.0.0.0:5000
```

Se as mensagens aparecerem imediatamente, o problema foi resolvido!

## Nota

O servidor **está funcionando** mesmo quando o output não aparece. O problema é apenas visual - o Waitress está rodando normalmente, mas o output está buffered.

Para verificar se está funcionando (mesmo sem ver o output):
- Abra outro terminal
- Execute: `Invoke-RestMethod -Uri "http://localhost:5000/api/health"`
- Se retornar JSON, o servidor está funcionando!
