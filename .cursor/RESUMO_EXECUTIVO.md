# Resumo Executivo - Plante Uma Flor

**Versão**: 3.0 (PWA) | **Última atualização**: 2026-01-02

---

## 🎯 Stack Principal

| Camada | Tecnologia |
|--------|-----------|
| **Backend** | Flask 3.0 + SQLAlchemy 2.0 + SQLite |
| **Frontend** | React 19 + TypeScript + Vite + MUI |
| **Offline** | Dexie (IndexedDB) + Workbox (Service Worker) |
| **Backup** | Sistema customizado (AES-256-GCM) |

---

## 📁 Estrutura Rápida

```
backend/app/
  ├── models/          # Entidades (Pedido, Cliente, AuditLog)
  ├── repositories/    # Acesso a dados (Repository Pattern)
  ├── services/       # Lógica de negócio
  ├── routes/         # Controllers HTTP (Blueprints)
  ├── commands/       # Command Pattern
  └── utils/          # Backup, encryption, audit

frontend_v2/src/
  ├── features/       # Módulos por feature
  ├── api/           # Cliente HTTP
  ├── lib/offline/    # Cache + Outbox
  └── components/     # Componentes compartilhados
```

---

## 🔑 Regras Críticas

1. **Command Pattern**: Botões → Command Class → Service/Repository
2. **Atomicidade**: Pedidos só confirmados após commit no `.db`
3. **Fail-Closed**: DELETE bloqueado se backup falhar (P0.2)
4. **Soft Delete**: Pedidos marcados com `deleted_at`, não removidos (P0.3)

---

## 🔐 Sistema de Backup (P0 + P1)

### P0 - Proteção contra Perda
- **P0.1**: Backup horário (Seg-Sex 07-18h, Sáb 07-14h)
- **P0.2**: Fail-closed (bloqueia DELETE sem backup)
- **P0.3**: Soft delete + auditoria
- **P0.4**: Teste diário de restauração (06:30)

### P1 - Robustez Operacional
- **P1.1**: Validação padronizada (integrity_check + schema)
- **P1.2**: Retenção GFS (48h, 30d, 12s, 12m)
- **P1.3**: Verificação remota (tamanho + hash)
- **P1.4**: Diretório secundário (outro drive)
- **P1.5**: Health/Status (`/api/admin/backup/health`)

---

## 🚀 Comandos Rápidos

```bash
# Servidor
python backend/main.py --https

# Backup manual
python backend/scripts/backup/backup.py

# Health backup
curl -u admin:<pass> http://localhost:5000/api/admin/backup/health

# Frontend
npm run dev
```

---

## 📍 Localizações Importantes

| Item | Caminho |
|------|---------|
| **Banco de dados** | `%USERPROFILE%/var/lib/database/database.db` |
| **Backups locais** | `backend/instance/backups/` |
| **Backups remotos** | `C:\Users\<USER>\Meu Drive\...\` |
| **Logs** | `backend/instance/logs/` |
| **SSL** | `backend/instance/ssl/` |
| **Config** | `backend/.env` |

---

## 🔄 Fluxo de Pedido

```
UI (Wizard) → API POST → Route → Service → Repository → SQLite
                                                      ↓
                                            Commit → Response 201
```

---

## 🛡️ Segurança

- **Autenticação**: Seletiva (visualização livre, ações protegidas)
- **Backup**: Encriptação AES-256-GCM (remotos)
- **Auditoria**: Tabela `audit_log` (P0.3)
- **Rate Limit**: 60/min, 1000/hora

---

## 📚 Docs Principais

- `.cursor/CONTEXT.md` - Regras de negócio
- `.cursor/MEMORIA_PROJETO.md` - Memória completa
- `backend/docs/ESTUDO_BACKUP_COMPLETO.md` - Backup detalhado

---

**Para detalhes completos, ver `.cursor/MEMORIA_PROJETO.md`**
