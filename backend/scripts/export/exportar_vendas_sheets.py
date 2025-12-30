# -*- coding: utf-8 -*-
"""
Script para exportar vendas automaticamente para Google Sheets
Roda diariamente às 19h via Task Scheduler

Estrutura: 3 abas (WhatsApp, Catálogo, Site)
- Esquerda: pedidos do dia (Valor, Cliente, Telefone, Data Entrega)
- Direita: totais de cada dia do mês (com "DOMINGO" nos domingos)
"""
import sys
import os
import re
import calendar
from datetime import datetime, date

# Adiciona o diretório backend ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    print("Instalando dependências...")
    os.system('pip install gspread google-auth')
    import gspread
    from google.oauth2.service_account import Credentials

from app import create_app, db
from app.models.pedido import Pedido

# Configurações
# Calcular caminho do arquivo de credenciais
# Prioridade: 1) Variável de ambiente, 2) user/config (novo), 3) config (legado)
def _resolve_credentials_path():
    """
    Resolve o caminho das credenciais Google com fallbacks.
    Prioridade:
      1. GOOGLE_APPLICATION_CREDENTIALS (variável de ambiente padrão do Google)
      2. backend/user/config/google_credentials.json (caminho atual)
      3. backend/config/google_credentials.json (legado, compatibilidade)
    """
    # 1. Variável de ambiente tem prioridade máxima
    env_creds = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if env_creds and os.path.exists(env_creds):
        return env_creds
    
    # Calcular backend_dir baseado em __file__ (path absoluto, não CWD)
    try:
        script_file = os.path.abspath(__file__)
        script_dir = os.path.dirname(script_file)
        # Volta de scripts/export para backend
        backend_dir = os.path.dirname(os.path.dirname(script_dir))
    except (NameError, AttributeError):
        # Se __file__ não estiver definido (importlib), procurar backend no sys.path
        backend_dir = None
        for path in sys.path:
            path_abs = os.path.abspath(path)
            if os.path.exists(os.path.join(path_abs, 'app', '__init__.py')):
                backend_dir = path_abs
                break
        if not backend_dir:
            try:
                current_dir = os.path.abspath(os.path.dirname(sys.modules[__name__].__file__))
            except:
                current_dir = os.path.abspath('.')
            backend_dir = os.path.dirname(os.path.dirname(current_dir))
    
    # 2. Caminho atual: backend/user/config/ (prioridade)
    user_config_path = os.path.join(backend_dir, 'user', 'config', 'google_credentials.json')
    if os.path.exists(user_config_path):
        return user_config_path
    
    # 3. Caminho legado: backend/config/ (compatibilidade)
    legacy_path = os.path.join(backend_dir, 'config', 'google_credentials.json')
    if os.path.exists(legacy_path):
        return legacy_path
    
    # Retorna caminho preferido para mensagem de erro clara
    return user_config_path

CREDENTIALS_PATH = _resolve_credentials_path()
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Mapeamento de fontes para abas
FONTES_ABAS = {
    'WhatsApp': ['WhatsApp', 'whatsapp', 'Whatsapp', 'WhatsApp (Caio)', 'WhatsApp (Paula)'],
    'Catálogo': ['Catálogo', 'Catalogo', 'catalogo', 'catálogo'],
    'Site': ['Site', 'site']
}

MESES_PT = {
    1: 'JANEIRO', 2: 'FEVEREIRO', 3: 'MARCO', 4: 'ABRIL',
    5: 'MAIO', 6: 'JUNHO', 7: 'JULHO', 8: 'AGOSTO',
    9: 'SETEMBRO', 10: 'OUTUBRO', 11: 'NOVEMBRO', 12: 'DEZEMBRO'
}


def parse_valor(valor_str):
    """Converte string de valor para float"""
    if not valor_str:
        return 0.0
    valor_limpo = re.sub(r'[R$\s]', '', str(valor_str)).replace(',', '.')
    try:
        return float(valor_limpo)
    except:
        return 0.0


def get_google_client():
    """Retorna cliente autenticado do Google Sheets"""
    if not os.path.exists(CREDENTIALS_PATH):
        # Mensagem clara indicando caminhos verificados
        raise FileNotFoundError(
            f"Arquivo de credenciais Google não encontrado.\n"
            f"Caminho esperado: {CREDENTIALS_PATH}\n\n"
            f"Opções para resolver:\n"
            f"  1. Copie google_credentials.json para: backend/user/config/\n"
            f"  2. Defina a variável de ambiente GOOGLE_APPLICATION_CREDENTIALS\n\n"
            f"Siga as instruções em docs/CONFIGURAR_GOOGLE_SHEETS.md"
        )
    
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    return gspread.authorize(creds)


def get_or_create_spreadsheet(client, mes, ano):
    """Busca planilha do mês (deve ser criada manualmente pelo usuário)"""
    nome_planilha = f"VENDAS_{MESES_PT[mes]}_{ano}"
    
    try:
        # Tenta abrir planilha existente
        spreadsheet = client.open(nome_planilha)
        print(f"✓ Planilha encontrada: {nome_planilha}")
        return spreadsheet
    except gspread.SpreadsheetNotFound:
        # Planilha não existe - instrui o usuário a criar
        print(f"\n❌ ERRO: Planilha '{nome_planilha}' não encontrada!")
        print(f"\nPara resolver:")
        print(f"1. Abra o Google Sheets (sheets.google.com)")
        print(f"2. Crie uma planilha chamada: {nome_planilha}")
        print(f"3. Crie 3 abas: WhatsApp, Catálogo, Site")
        print(f"4. Compartilhe com a Service Account como Editor")
        print(f"   (email está em backend/config/google_credentials.json)")
        print(f"\nApós criar, execute novamente.")
        raise Exception(f"Planilha '{nome_planilha}' não existe. Crie manualmente no Google Sheets.")


def criar_planilha_na_pasta(client, nome_planilha, nome_pasta):
    """Cria planilha diretamente na pasta compartilhada usando API do Drive"""
    from googleapiclient.discovery import build
    from google.oauth2.service_account import Credentials as ServiceCredentials
    
    creds = ServiceCredentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=creds)
    
    # Busca a pasta
    folder_id = get_folder_id(drive_service, nome_pasta)
    
    if not folder_id:
        raise Exception(f"Pasta '{nome_pasta}' não encontrada. Compartilhe a pasta com a Service Account.")
    
    # Cria a planilha diretamente na pasta (supportsAllDrives para pastas compartilhadas)
    file_metadata = {
        'name': nome_planilha,
        'mimeType': 'application/vnd.google-apps.spreadsheet',
        'parents': [folder_id]
    }
    
    file = drive_service.files().create(
        body=file_metadata,
        fields='id',
        supportsAllDrives=True
    ).execute()
    
    spreadsheet_id = file.get('id')
    print(f"✓ Planilha criada na pasta (ID: {spreadsheet_id})")
    
    # Transfere propriedade para o dono da pasta (sua conta pessoal)
    try:
        # Busca o email do proprietário da pasta
        pasta_info = drive_service.files().get(
            fileId=folder_id,
            fields='owners',
            supportsAllDrives=True
        ).execute()
        
        owner_email = pasta_info.get('owners', [{}])[0].get('emailAddress')
        
        if owner_email:
            # Transfere propriedade
            drive_service.permissions().create(
                fileId=spreadsheet_id,
                body={
                    'type': 'user',
                    'role': 'owner',
                    'emailAddress': owner_email
                },
                transferOwnership=True,
                supportsAllDrives=True
            ).execute()
            print(f"✓ Propriedade transferida para: {owner_email}")
    except Exception as e:
        print(f"⚠ Não foi possível transferir propriedade: {e}")
    
    # Abre a planilha com gspread
    return client.open_by_key(spreadsheet_id)


def get_folder_id(drive_service, nome_pasta):
    """Busca o ID da pasta pelo nome"""
    try:
        # Busca pasta pelo nome
        results = drive_service.files().list(
            q=f"name='{nome_pasta}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        folders = results.get('files', [])
        if folders:
            folder_id = folders[0]['id']
            print(f"✓ Pasta encontrada: {nome_pasta} (ID: {folder_id})")
            return folder_id
        else:
            print(f"⚠ Pasta '{nome_pasta}' não encontrada")
            return None
    except Exception as e:
        print(f"⚠ Erro ao buscar pasta: {e}")
        return None


def criar_abas_iniciais(spreadsheet, mes, ano):
    """Cria as 3 abas com estrutura inicial"""
    # Pega número de dias do mês
    _, num_dias = calendar.monthrange(ano, mes)
    
    # Cria abas
    for nome_aba in ['WhatsApp', 'Catálogo', 'Site']:
        try:
            worksheet = spreadsheet.add_worksheet(title=nome_aba, rows=100, cols=10)
        except:
            worksheet = spreadsheet.worksheet(nome_aba)
        
        # Cabeçalhos
        headers = ['Valor', 'Cliente', 'Telefone', 'Data Entrega', '', 'Dia', 'Total']
        worksheet.update('A1:G1', [headers])
        
        # Coluna de dias do mês (F2:G32)
        dias_data = []
        for dia in range(1, num_dias + 1):
            data_dia = date(ano, mes, dia)
            dia_semana = data_dia.weekday()  # 6 = domingo
            
            if dia_semana == 6:
                dias_data.append(['DOMINGO', '-'])
            else:
                dias_data.append([str(dia), 'R$ 0,00'])
        
        worksheet.update(f'F2:G{num_dias + 1}', dias_data)
    
    # Remove Sheet1 padrão
    try:
        default_sheet = spreadsheet.worksheet('Sheet1')
        spreadsheet.del_worksheet(default_sheet)
    except:
        pass


def get_fonte_nome(pedido):
    """Retorna o nome da fonte do pedido"""
    if pedido.fonte_pedido_rel:
        return pedido.fonte_pedido_rel.nome
    return pedido.fonte_pedido or ''


def identificar_aba(fonte_nome):
    """Identifica qual aba o pedido pertence"""
    for aba, variantes in FONTES_ABAS.items():
        if fonte_nome in variantes:
            return aba
    return None


def exportar_vendas():
    """Função principal de exportação"""
    app = create_app()
    
    with app.app_context():
        hoje = date.today()
        mes = hoje.month
        ano = hoje.year
        
        print("=" * 50)
        print(f"EXPORTAÇÃO DE VENDAS - {MESES_PT[mes]}/{ano}")
        print("=" * 50)
        
        # Conecta ao Google Sheets
        try:
            client = get_google_client()
        except Exception as e:
            print(f"✗ Erro ao conectar: {e}")
            return False
        
        # Busca ou cria planilha do mês
        spreadsheet = get_or_create_spreadsheet(client, mes, ano)
        
        # Busca pedidos do mês atual
        primeiro_dia = date(ano, mes, 1)
        _, ultimo = calendar.monthrange(ano, mes)
        ultimo_dia = date(ano, mes, ultimo)
        
        pedidos = Pedido.query.filter(
            Pedido.created_at >= datetime.combine(primeiro_dia, datetime.min.time()),
            Pedido.created_at <= datetime.combine(ultimo_dia, datetime.max.time())
        ).order_by(Pedido.created_at).all()
        
        print(f"Total de pedidos no mês: {len(pedidos)}")
        
        # Organiza pedidos por aba e dia
        dados_por_aba = {'WhatsApp': {}, 'Catálogo': {}, 'Site': {}}
        
        for pedido in pedidos:
            fonte = get_fonte_nome(pedido)
            aba = identificar_aba(fonte)
            
            if not aba:
                continue
            
            dia = pedido.created_at.day
            
            if dia not in dados_por_aba[aba]:
                dados_por_aba[aba][dia] = []
            
            dados_por_aba[aba][dia].append({
                'valor': parse_valor(pedido.valor),
                'cliente': pedido.cliente or '',
                'telefone': pedido.telefone_cliente or '',
                'data_entrega': pedido.dia_entrega.strftime('%d/%m') if pedido.dia_entrega else ''
            })
        
        # Atualiza cada aba
        for nome_aba in ['WhatsApp', 'Catálogo', 'Site']:
            try:
                worksheet = spreadsheet.worksheet(nome_aba)
            except:
                # Cria aba se não existir
                worksheet = spreadsheet.add_worksheet(title=nome_aba, rows=100, cols=10)
                headers = ['Valor', 'Cliente', 'Telefone', 'Data Entrega', '', 'Dia', 'Total']
                worksheet.update('A1:G1', [headers])
            
            # Limpa dados antigos (mantém cabeçalho)
            worksheet.batch_clear(['A2:D100'])
            
            # Prepara dados de pedidos (esquerda)
            pedidos_aba = dados_por_aba[nome_aba]
            linhas_pedidos = []
            
            for dia in sorted(pedidos_aba.keys()):
                for p in pedidos_aba[dia]:
                    linhas_pedidos.append([
                        f"R$ {p['valor']:.2f}".replace('.', ','),
                        p['cliente'],
                        p['telefone'],
                        p['data_entrega']
                    ])
            
            if linhas_pedidos:
                worksheet.update(f'A2:D{len(linhas_pedidos) + 1}', linhas_pedidos)
            
            # Atualiza totais por dia (direita)
            _, num_dias = calendar.monthrange(ano, mes)
            totais_data = []
            
            for dia in range(1, num_dias + 1):
                data_dia = date(ano, mes, dia)
                dia_semana = data_dia.weekday()
                
                if dia_semana == 6:  # Domingo
                    totais_data.append(['DOMINGO', '-'])
                else:
                    total_dia = sum(p['valor'] for p in pedidos_aba.get(dia, []))
                    totais_data.append([str(dia), f"R$ {total_dia:.2f}".replace('.', ',')])
            
            worksheet.update(f'F2:G{num_dias + 1}', totais_data)
            
            total_aba = sum(p['valor'] for dia_pedidos in pedidos_aba.values() for p in dia_pedidos)
            print(f"  {nome_aba}: {sum(len(v) for v in pedidos_aba.values())} pedidos - R$ {total_aba:.2f}")
        
        print("\n✓ Exportação concluída!")
        print(f"  Planilha: {spreadsheet.url}")
        
        return True


def teste_conexao():
    """Testa conexão com Google Sheets"""
    print("Testando conexão com Google Sheets...")
    try:
        client = get_google_client()
        print("✓ Conexão OK!")
        print(f"  Email da conta: Verificar em {CREDENTIALS_PATH}")
        return True
    except Exception as e:
        print(f"✗ Erro: {e}")
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Exportar vendas para Google Sheets')
    parser.add_argument('--teste', action='store_true', help='Testar conexão')
    
    args = parser.parse_args()
    
    if args.teste:
        teste_conexao()
    else:
        exportar_vendas()
