# Guia Rápido: Iniciar Servidor Waitress

## Problema: Servidor não responde após iniciar

Se o servidor iniciou mas não está respondendo, siga estes passos:

## Solução 1: Usar o script automatizado (RECOMENDADO)

```batch
cd "c:\Gestor de Pedidos Plante uma flor"
iniciar_producao_completo.bat
```

Este script:
- Faz o build do frontend automaticamente
- Inicia o Waitress corretamente
- Abre em uma janela separada

## Solução 2: Iniciar manualmente

### Passo 1: Fazer build do frontend
```batch
cd frontend_v2
npm run build:fast
cd ..
```

### Passo 2: Iniciar servidor
```batch
cd backend
python wsgi.py
```

**IMPORTANTE**: O servidor deve mostrar:
```
[OK] Servidor de produção iniciado!
[INFO] Iniciando Waitress...
[INFO] Escutando em 0.0.0.0:5000
```

Se você não ver essas mensagens, há um problema.

## Solução 3: Usar Waitress diretamente (alternativa)

Se `python wsgi.py` não funcionar, tente:

```batch
cd backend
python -m waitress --listen=0.0.0.0:5000 --threads=4 wsgi:app
```

## Verificação

Após iniciar, em OUTRO terminal, teste:

```powershell
# Teste 1: Health check
Invoke-RestMethod -Uri "http://localhost:5000/api/health"

# Teste 2: Frontend
Invoke-WebRequest -Uri "http://localhost:5000/" | Select-Object StatusCode

# Teste 3: Verificar porta
netstat -an | findstr ":5000" | findstr "LISTENING"
```

Se a porta 5000 não aparecer como LISTENING, o servidor não está escutando.

## Problemas Comuns

### 1. Porta já em uso
```batch
# Verificar processos na porta 5000
netstat -ano | findstr ":5000"

# Matar processo (substitua PID pelo número)
taskkill /PID <PID> /F
```

### 2. Waitress não instalado
```batch
pip install waitress
```

### 3. Build do frontend não existe
```batch
cd frontend_v2
npm run build:fast
```

### 4. Servidor trava durante inicialização
- Verifique se há erros no console
- Tente usar `python -m waitress` diretamente
- Verifique se o arquivo `frontend_v2/dist/index.html` existe

## Debug

Para ver mais informações, execute:

```batch
cd backend
python test_init.py
```

Isso verifica se a aplicação inicializa corretamente.
