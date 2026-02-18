# -*- coding: utf-8 -*-
"""
Script para exportar vendas automaticamente para Google Sheets
Roda diariamente Ã s 19h via Task Scheduler

Estrutura: 3 abas (WhatsApp, Catálogo, Site)
- Esquerda: pedidos do dia (Valor, Cliente, Telefone, Data Entrega)
- Direita: totais de cada dia do mÃªs (com "DOMINGO" nos domingos)
"""
import calendar
import os
import re
import sys
import time
from datetime import date, datetime

from sqlalchemy import func

# Adiciona o diretÃ³rio backend ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import gspread
    from google.oauth2.service_account import Credentials  # noqa: E402
except ImportError:
    print("Instalando dependÃªncias...")
    os.system("pip install gspread google-auth")
    import gspread
    from google.oauth2.service_account import Credentials  # noqa: E402

from app import create_app  # noqa: E402
from app.models.pedido import Pedido  # noqa: E402


# ConfiguraÃ§Ãµes
# Calcular caminho do arquivo de credenciais
# Prioridade: 1) VariÃ¡vel de ambiente, 2) user/config (novo), 3) config (legado)
def _resolve_credentials_path():
    """
    Resolve o caminho das credenciais Google com fallbacks.
    Prioridade:
      1. GOOGLE_APPLICATION_CREDENTIALS (variÃ¡vel de ambiente padrÃ£o do Google)
      2. backend/user/config/google_credentials.json (caminho atual)
      3. backend/config/google_credentials.json (legado, compatibilidade)
    """
    # 1. VariÃ¡vel de ambiente tem prioridade mÃ¡xima
    env_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if env_creds and os.path.exists(env_creds):
        return env_creds

    # Calcular backend_dir baseado em __file__ (path absoluto, nÃ£o CWD)
    try:
        script_file = os.path.abspath(__file__)
        script_dir = os.path.dirname(script_file)
        # Volta de scripts/export para backend
        backend_dir = os.path.dirname(os.path.dirname(script_dir))
    except (NameError, AttributeError):
        # Se __file__ nÃ£o estiver definido (importlib), procurar backend no sys.path
        backend_dir = None
        for path in sys.path:
            path_abs = os.path.abspath(path)
            if os.path.exists(os.path.join(path_abs, "app", "__init__.py")):
                backend_dir = path_abs
                break
        if not backend_dir:
            try:
                current_dir = os.path.abspath(os.path.dirname(sys.modules[__name__].__file__))
            except (AttributeError, KeyError):
                current_dir = os.path.abspath(".")
            backend_dir = os.path.dirname(os.path.dirname(current_dir))

    # 2. Caminho atual: backend/user/config/ (prioridade)
    user_config_path = os.path.join(backend_dir, "user", "config", "google_credentials.json")
    if os.path.exists(user_config_path):
        return user_config_path

    # 3. Caminho legado: backend/config/ (compatibilidade)
    legacy_path = os.path.join(backend_dir, "config", "google_credentials.json")
    if os.path.exists(legacy_path):
        return legacy_path

    # Retorna caminho preferido para mensagem de erro clara
    return user_config_path


CREDENTIALS_PATH = _resolve_credentials_path()
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Abas canônicas (nomes esperados no Google Sheets)
ABA_WHATSAPP = "WhatsApp"
ABA_CATALOGO = "Catálogo"
ABA_SITE = "Site"

# Aliases (inclui casos comuns de mojibake)
ABA_ALIASES = {
    ABA_WHATSAPP: [ABA_WHATSAPP, "Whatsapp", "whatsapp", "WhatsApp (Caio)", "WhatsApp (Paula)"],
    ABA_CATALOGO: [ABA_CATALOGO, "Catalogo", "catalogo", "CatÃ¡logo", "catÃ¡logo"],
    ABA_SITE: [ABA_SITE, "site", "SITE"],
}

MESES_PT = {
    1: "JANEIRO",
    2: "FEVEREIRO",
    3: "MARCO",
    4: "ABRIL",
    5: "MAIO",
    6: "JUNHO",
    7: "JULHO",
    8: "AGOSTO",
    9: "SETEMBRO",
    10: "OUTUBRO",
    11: "NOVEMBRO",
    12: "DEZEMBRO",
}


def parse_valor(valor_str):
    """Converte string de valor para float"""
    if not valor_str:
        return 0.0
    raw = str(valor_str).strip()
    # Remover "R$" e espaços
    cleaned = re.sub(r"R\$\s?", "", raw, flags=re.IGNORECASE).strip()

    # Formato BR: "1.234,56" / "65,00" -> remover pontos de milhar e trocar vírgula por ponto
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def get_google_client():
    """Retorna cliente autenticado do Google Sheets"""
    if not os.path.exists(CREDENTIALS_PATH):
        # Mensagem clara indicando caminhos verificados
        raise FileNotFoundError(
            f"Arquivo de credenciais Google nÃ£o encontrado.\n"
            f"Caminho esperado: {CREDENTIALS_PATH}\n\n"
            f"OpÃ§Ãµes para resolver:\n"
            f"  1. Copie google_credentials.json para: backend/user/config/\n"
            f"  2. Defina a variÃ¡vel de ambiente GOOGLE_APPLICATION_CREDENTIALS\n\n"
            f"Siga as instruÃ§Ãµes em docs/CONFIGURAR_GOOGLE_SHEETS.md"
        )

    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    client = gspread.authorize(creds)
    # Configurar timeout para requisiÃ§Ãµes do gspread (usa requests por baixo)
    # gspread usa requests.Session internamente, mas nÃ£o expÃµe timeout diretamente
    # O timeout serÃ¡ tratado na funÃ§Ã£o retry wrapper
    return client


def retry_google_operation(operation, max_retries=2, backoff_delays=None, timeout=None):
    """
    Wrapper para operaÃ§Ãµes do Google Sheets com retry e timeout

    Args:
        operation: FunÃ§Ã£o que executa a operaÃ§Ã£o (sem argumentos)
        max_retries: NÃºmero mÃ¡ximo de tentativas
        backoff_delays: Lista de delays entre tentativas (em segundos)
        timeout: Timeout mÃ¡ximo por tentativa (em segundos) - nÃ£o usado diretamente aqui,
                 mas pode ser implementado com threading se necessÃ¡rio

    Returns:
        Resultado da operaÃ§Ã£o
    """
    if backoff_delays is None:
        backoff_delays = [1, 2]

    last_exception = None

    for attempt in range(max_retries + 1):  # 0, 1, 2 (3 tentativas no total)
        try:
            return operation()
        except (
            gspread.exceptions.APIError,
            gspread.exceptions.SpreadsheetNotFound,
            gspread.exceptions.WorksheetNotFound,
        ) as e:
            # Erros de API podem ser temporÃ¡rios (rate limit, timeout do servidor)
            last_exception = e
            if attempt < max_retries:
                # Aguardar antes de tentar novamente (backoff exponencial)
                time.sleep(backoff_delays[attempt])
                continue
            # Ãšltima tentativa falhou
            raise
        except Exception:
            # Outros erros nÃ£o devem ser repetidos
            raise

    # Se chegou aqui, todas as tentativas falharam
    if last_exception:
        raise last_exception


def get_or_create_spreadsheet(client, mes, ano):
    """Busca planilha do mÃªs (deve ser criada manualmente pelo usuÃ¡rio)"""
    nome_planilha = f"VENDAS_{MESES_PT[mes]}_{ano}"

    try:
        # Tenta abrir planilha existente
        spreadsheet = client.open(nome_planilha)
        print(f"âœ“ Planilha encontrada: {nome_planilha}")
        return spreadsheet
    except gspread.SpreadsheetNotFound:
        # Planilha nÃ£o existe - instrui o usuÃ¡rio a criar
        print(f"\nâŒ ERRO: Planilha '{nome_planilha}' nÃ£o encontrada!")
        print("\nPara resolver:")
        print("1. Abra o Google Sheets (sheets.google.com)")
        print(f"2. Crie uma planilha chamada: {nome_planilha}")
        print("3. Crie 3 abas: WhatsApp, Catálogo, Site")
        print("4. Compartilhe com a Service Account como Editor")
        print("   (email estÃ¡ em backend/config/google_credentials.json)")
        print("\nApÃ³s criar, execute novamente.")
        raise Exception(
            f"Planilha '{nome_planilha}' nÃ£o existe. Crie manualmente no Google Sheets."
        ) from None


def criar_planilha_na_pasta(client, nome_planilha, nome_pasta):
    """Cria planilha diretamente na pasta compartilhada usando API do Drive"""
    from google.oauth2.service_account import Credentials as ServiceCredentials
    from googleapiclient.discovery import build

    creds = ServiceCredentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    drive_service = build("drive", "v3", credentials=creds)

    # Busca a pasta
    folder_id = get_folder_id(drive_service, nome_pasta)

    if not folder_id:
        raise Exception(
            f"Pasta '{nome_pasta}' nÃ£o encontrada. Compartilhe a pasta com a Service Account."
        )

    # Cria a planilha diretamente na pasta (supportsAllDrives para pastas compartilhadas)
    file_metadata = {
        "name": nome_planilha,
        "mimeType": "application/vnd.google-apps.spreadsheet",
        "parents": [folder_id],
    }

    file = (
        drive_service.files()
        .create(body=file_metadata, fields="id", supportsAllDrives=True)
        .execute()
    )

    spreadsheet_id = file.get("id")
    print(f"âœ“ Planilha criada na pasta (ID: {spreadsheet_id})")

    # Transfere propriedade para o dono da pasta (sua conta pessoal)
    try:
        # Busca o email do proprietÃ¡rio da pasta
        pasta_info = (
            drive_service.files()
            .get(fileId=folder_id, fields="owners", supportsAllDrives=True)
            .execute()
        )

        owner_email = pasta_info.get("owners", [{}])[0].get("emailAddress")

        if owner_email:
            # Transfere propriedade
            drive_service.permissions().create(
                fileId=spreadsheet_id,
                body={"type": "user", "role": "owner", "emailAddress": owner_email},
                transferOwnership=True,
                supportsAllDrives=True,
            ).execute()
            print(f"âœ“ Propriedade transferida para: {owner_email}")
    except Exception as e:
        print(f"âš  NÃ£o foi possÃ­vel transferir propriedade: {e}")

    # Abre a planilha com gspread
    return client.open_by_key(spreadsheet_id)


def get_folder_id(drive_service, nome_pasta):
    """Busca o ID da pasta pelo nome"""
    try:
        # Busca pasta pelo nome
        results = (
            drive_service.files()
            .list(
                q=f"name='{nome_pasta}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                spaces="drive",
                fields="files(id, name)",
            )
            .execute()
        )

        folders = results.get("files", [])
        if folders:
            folder_id = folders[0]["id"]
            print(f"âœ“ Pasta encontrada: {nome_pasta} (ID: {folder_id})")
            return folder_id
        else:
            print(f"âš  Pasta '{nome_pasta}' nÃ£o encontrada")
            return None
    except Exception as e:
        print(f"âš  Erro ao buscar pasta: {e}")
        return None


def criar_abas_iniciais(spreadsheet, mes, ano):
    """Cria as 3 abas com estrutura inicial"""
    # Pega nÃºmero de dias do mÃªs
    _, num_dias = calendar.monthrange(ano, mes)

    # Cria abas
    for nome_aba in [ABA_WHATSAPP, ABA_CATALOGO, ABA_SITE]:
        try:
            worksheet = spreadsheet.add_worksheet(title=nome_aba, rows=100, cols=10)
        except Exception:
            worksheet = spreadsheet.worksheet(nome_aba)

        # CabeÃ§alhos (com retry)
        headers = ["Valor", "Cliente", "Telefone", "Data Venda", "", "Dia", "Total"]
        retry_google_operation(
            lambda ws=worksheet, hdrs=headers: ws.update("A1:G1", [hdrs]),
            max_retries=2,
        )

        # Coluna de dias do mÃªs (F2:G32)
        dias_data = []
        for dia in range(1, num_dias + 1):
            data_dia = date(ano, mes, dia)
            dia_semana = data_dia.weekday()  # 6 = domingo

            if dia_semana == 6:
                dias_data.append(["DOMINGO", "-"])
            else:
                dias_data.append([str(dia), "R$ 0,00"])

        # Atualizar dias com retry
        retry_google_operation(
            lambda ws=worksheet, nd=num_dias, dd=dias_data: ws.update(f"F2:G{nd + 1}", dd),
            max_retries=2,
        )

    # Remove Sheet1 padrÃ£o
    try:
        default_sheet = spreadsheet.worksheet("Sheet1")
        spreadsheet.del_worksheet(default_sheet)
    except Exception:
        pass


def get_fonte_nome(pedido):
    """Retorna o nome da fonte do pedido"""
    if pedido.fonte_pedido_rel:
        return pedido.fonte_pedido_rel.nome
    return pedido.fonte_pedido or ""


def identificar_aba(fonte_nome):
    """Identifica qual aba o pedido pertence"""

    def _repair_mojibake(value: str) -> str:
        if not value:
            return value
        if "Ã" not in value and "Â" not in value:
            return value
        try:
            return value.encode("latin1").decode("utf-8")
        except Exception:
            return value

    def _normalize(value: str) -> str:
        if not value:
            return ""
        value = _repair_mojibake(str(value)).strip().lower()
        try:
            import unicodedata

            value = unicodedata.normalize("NFKD", value)
            value = "".join([c for c in value if not unicodedata.combining(c)])
        except Exception:
            pass
        return re.sub(r"[^a-z0-9]+", "", value)

    n = _normalize(fonte_nome)
    if not n:
        return None

    # Regras robustas: não depender de acento/case/exato
    if "whatsapp" in n or n.startswith("zap"):
        return ABA_WHATSAPP
    if "catalogo" in n or "catalog" in n:
        return ABA_CATALOGO
    if n == "site" or n.endswith("site"):
        return ABA_SITE

    # Fallback: bater em aliases normalizados (casos raros)
    for canonical, aliases in ABA_ALIASES.items():
        if n in {_normalize(a) for a in aliases}:
            return canonical
    return None


def _get_or_rename_worksheet(spreadsheet, canonical_title: str):
    """
    Obtém worksheet por nome canônico.
    Se existir apenas uma variante (ex: 'CatÃ¡logo'), renomeia para o canônico.
    """
    try:
        return spreadsheet.worksheet(canonical_title)
    except Exception:
        pass

    for alias in ABA_ALIASES.get(canonical_title, []):
        if alias == canonical_title:
            continue
        try:
            ws = spreadsheet.worksheet(alias)
            try:
                ws.update_title(canonical_title)
            except Exception:
                # Se não foi possível renomear (permissão/drive), cria a aba canônica
                # para evitar que a exportação "vá parar" numa aba com nome corrompido.
                try:
                    return spreadsheet.add_worksheet(title=canonical_title, rows=100, cols=10)
                except Exception:
                    return ws
            return ws
        except Exception:
            continue

    return spreadsheet.add_worksheet(title=canonical_title, rows=100, cols=10)


def exportar_vendas():
    """FunÃ§Ã£o principal de exportaÃ§Ã£o"""
    app = create_app()

    with app.app_context():
        hoje = date.today()
        mes = hoje.month
        ano = hoje.year

        print("=" * 50)
        print(f"EXPORTAÃ‡ÃƒO DE VENDAS - {MESES_PT[mes]}/{ano}")
        print("=" * 50)

        # 1. Conecta ao Google Sheets (verifica autenticaÃ§Ã£o primeiro)
        try:
            client = get_google_client()
            print("âœ“ AutenticaÃ§Ã£o Google OK")
        except Exception as e:
            print(f"âœ— Erro ao conectar: {e}")
            return False

        # 2. Verifica se a planilha existe ANTES de buscar pedidos (com retry)
        nome_planilha = f"VENDAS_{MESES_PT[mes]}_{ano}"
        try:
            spreadsheet = retry_google_operation(
                lambda: client.open(nome_planilha), max_retries=2, backoff_delays=[1, 2]
            )
            print(f"âœ“ Planilha encontrada: {nome_planilha}")
        except gspread.SpreadsheetNotFound:
            print(f"\nâš  Planilha '{nome_planilha}' nÃ£o encontrada.")
            print("ExportaÃ§Ã£o cancelada. A planilha deve existir no Google Sheets.")
            return False  # Retorna False sem lanÃ§ar exceÃ§Ã£o (graceful failure)
        except Exception as e:
            print(f"âœ— Erro ao acessar planilha apÃ³s mÃºltiplas tentativas: {e}")
            return False

        # 3. SÃ³ busca pedidos se a planilha existe
        # Busca pedidos do mÃªs atual
        primeiro_dia = date(ano, mes, 1)
        _, ultimo = calendar.monthrange(ano, mes)
        ultimo_dia = date(ano, mes, ultimo)

        pedidos = (
            Pedido.query.filter(
                Pedido.deleted_at.is_(None),  # alinhar com API (soft delete)
                Pedido.created_at >= datetime.combine(primeiro_dia, datetime.min.time()),
                Pedido.created_at <= datetime.combine(ultimo_dia, datetime.max.time()),
                func.lower(func.trim(Pedido.status)) != "cancelado",  # alinhar com tela de vendas
            )
            .order_by(Pedido.created_at)
            .all()
        )

        print(f"Total de pedidos no mÃªs: {len(pedidos)}")

        # Organiza pedidos por aba e dia
        dados_por_aba = {ABA_WHATSAPP: {}, ABA_CATALOGO: {}, ABA_SITE: {}}

        for pedido in pedidos:
            fonte = get_fonte_nome(pedido)
            aba = identificar_aba(fonte)

            if not aba:
                continue

            dia = pedido.created_at.day

            if dia not in dados_por_aba[aba]:
                dados_por_aba[aba][dia] = []

            dados_por_aba[aba][dia].append(
                {
                    "valor": parse_valor(pedido.valor),
                    "cliente": pedido.cliente or "",
                    "telefone": pedido.telefone_cliente or "",
                    "data_venda": pedido.created_at.strftime("%d/%m/%Y %H:%M")
                    if pedido.created_at
                    else "",
                }
            )

        # Atualiza cada aba
        for nome_aba in [ABA_WHATSAPP, ABA_CATALOGO, ABA_SITE]:
            worksheet = _get_or_rename_worksheet(spreadsheet, nome_aba)

            # Garantir cabeçalho (idempotente)
            headers = [
                "Valor",
                "Cliente",
                "Telefone",
                "Data Venda",
                "",
                "Dia",
                "Total",
            ]
            retry_google_operation(
                lambda ws=worksheet, hdrs=headers: ws.update("A1:G1", [hdrs]),
                max_retries=2,
            )

            # Limpa dados antigos (mantÃ©m cabeÃ§alho)
            worksheet.batch_clear(["A2:D100"])

            # Prepara dados de pedidos (esquerda)
            pedidos_aba = dados_por_aba.get(nome_aba, {})
            linhas_pedidos = []

            for dia in sorted(pedidos_aba.keys()):
                for p in pedidos_aba[dia]:
                    linhas_pedidos.append(
                        [
                            f"R$ {p['valor']:.2f}".replace(".", ","),
                            p["cliente"],
                            p["telefone"],
                            p["data_venda"],
                        ]
                    )

            if linhas_pedidos:
                # Atualizar pedidos com retry
                num_linhas = len(linhas_pedidos)
                retry_google_operation(
                    lambda ws=worksheet, nl=num_linhas, lp=linhas_pedidos: ws.update(
                        f"A2:D{nl + 1}", lp
                    ),
                    max_retries=2,
                )

            # Atualiza totais por dia (direita)
            _, num_dias = calendar.monthrange(ano, mes)
            totais_data = []

            for dia in range(1, num_dias + 1):
                data_dia = date(ano, mes, dia)
                dia_semana = data_dia.weekday()

                if dia_semana == 6:  # Domingo
                    totais_data.append(["DOMINGO", "-"])
                else:
                    total_dia = sum(p["valor"] for p in pedidos_aba.get(dia, []))
                    totais_data.append([str(dia), f"R$ {total_dia:.2f}".replace(".", ",")])

            # Atualizar totais com retry
            retry_google_operation(
                lambda ws=worksheet, nd=num_dias, td=totais_data: ws.update(f"F2:G{nd + 1}", td),
                max_retries=2,
            )

            total_aba = sum(p["valor"] for dia_pedidos in pedidos_aba.values() for p in dia_pedidos)
            print(
                f"  {nome_aba}: {sum(len(v) for v in pedidos_aba.values())} pedidos - R$ {total_aba:.2f}"
            )

        print("\nâœ“ ExportaÃ§Ã£o concluÃ­da!")
        print(f"  Planilha: {spreadsheet.url}")

        return True


def teste_conexao():
    """Testa conexÃ£o com Google Sheets"""
    print("Testando conexÃ£o com Google Sheets...")
    try:
        get_google_client()
        print("âœ“ ConexÃ£o OK!")
        print(f"  Email da conta: Verificar em {CREDENTIALS_PATH}")
        return True
    except Exception as e:
        print(f"âœ— Erro: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Exportar vendas para Google Sheets")
    parser.add_argument("--teste", action="store_true", help="Testar conexÃ£o")

    args = parser.parse_args()

    if args.teste:
        teste_conexao()
    else:
        exportar_vendas()
