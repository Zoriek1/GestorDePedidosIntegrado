# Configuração do Google Sheets API

## Passo 1: Criar Projeto no Google Cloud Console

1. Acesse: https://console.cloud.google.com/
2. Clique em "Select a project" → "New Project"
3. Nome: `GestorPedidosExport` (ou outro de sua preferência)
4. Clique em "Create"

## Passo 2: Ativar Google Sheets API

1. No menu lateral, vá em "APIs & Services" → "Library"
2. Pesquise por "Google Sheets API"
3. Clique em "Enable"
4. Também ative "Google Drive API" (necessário para criar/buscar planilhas)

## Passo 3: Criar Credenciais (Service Account)

1. Vá em "APIs & Services" → "Credentials"
2. Clique em "Create Credentials" → "Service Account"
3. Preencha:
   - Nome: `gestor-pedidos-export`
   - Clique em "Create and Continue"
   - Role: "Editor" (ou pule esta etapa)
   - Clique em "Done"

4. Na lista de Service Accounts, clique no email criado
5. Vá na aba "Keys" → "Add Key" → "Create new key"
6. Escolha "JSON" e clique em "Create"
7. O arquivo será baixado automaticamente

## Passo 4: Salvar Credenciais

1. Renomeie o arquivo baixado para `google_credentials.json`
2. Mova para: `backend/user/config/google_credentials.json`

**Alternativa**: Defina a variável de ambiente `GOOGLE_APPLICATION_CREDENTIALS` com o caminho completo do arquivo.

**IMPORTANTE**: Este arquivo contém credenciais sensíveis. Ele já está no `.gitignore`.

## Passo 5: Compartilhar Acesso

O email da Service Account (ex: `gestor-pedidos-export@projeto.iam.gserviceaccount.com`) 
precisa ter acesso às planilhas.

**Opção A - Planilha específica:**
- Abra a planilha no Google Sheets
- Clique em "Compartilhar"
- Cole o email da Service Account
- Dê permissão de "Editor"

**Opção B - Pasta do Drive:**
- Crie uma pasta no Google Drive
- Compartilhe a pasta com o email da Service Account (Editor)
- As planilhas criadas pelo script ficarão nessa pasta

### Planilha de leads (opcional, separada das vendas)

- Crie uma planilha com o título **`Leads_GESTOR`** (ou outro nome e defina `GOOGLE_SHEETS_LEADS_DOCUMENT_NAME` no `.env`).
- Compartilhe com a **mesma** Service Account como **Editor** (igual à planilha de vendas).
- O script `scripts/export/exportar_leads_sheets.py` preenche só a aba **`Leads`** (cria a aba se não existir) e **não altera** as planilhas `VENDAS_*`.
- Teste: `cd backend && python scripts/export/exportar_leads_sheets.py --teste`
- Export: `python scripts/export/exportar_leads_sheets.py`
- API (mesma autenticação que exportar vendas): `POST /api/exportar-planilha-leads`

### Por que eu crio a planilha e a service account só “acessa”?

A Service Account **não é um usuário Gmail**. Planilhas criadas só por ela ficam no Drive **dela**, que você não abre no navegador como conta normal. Por isso o fluxo mais simples é: **você cria a planilha na sua conta**, compartilha com o e-mail da SA (`client_email` do JSON), e o script **edita** o arquivo que já está no seu Drive. Tecnicamente dá para criar arquivo via API, mas aí o arquivo nasce no “Drive da robô”; trazer para o seu uso costuma exigir pasta compartilhada ou troca de proprietário — mais trabalhoso que criar uma vez e compartilhar.

## Passo 6: Instalar Dependências

```bash
pip install gspread google-auth
```

## Passo 7: Testar

```bash
cd backend
python scripts/export/exportar_vendas_sheets.py --teste
```

---

## Estrutura do arquivo google_credentials.json

O arquivo deve ter este formato (os valores serão diferentes):

```json
{
  "type": "service_account",
  "project_id": "seu-projeto",
  "private_key_id": "xxx",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "gestor-pedidos-export@seu-projeto.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
```
