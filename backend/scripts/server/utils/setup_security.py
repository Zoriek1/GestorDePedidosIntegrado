# -*- coding: utf-8 -*-
"""
Script de Configuração Inicial de Segurança
Cria arquivo .env com configurações de segurança
"""
import sys
from pathlib import Path


def create_env_file():
    """Cria arquivo .env com configurações de segurança"""

    backend_dir = Path(__file__).parent.parent
    env_file = backend_dir / '.env'

    # Verificar se .env já existe
    if env_file.exists():
        print("\n[AVISO] Arquivo .env já existe!")
        resposta = input("Deseja sobrescrevê-lo? (s/n): ")
        if resposta.lower() != 's':
            print("[INFO] Operação cancelada.")
            return False

    # Solicitar senha do administrador
    print("\n" + "="*60)
    print("CONFIGURAÇÃO DE SEGURANÇA - Gestor de Pedidos")
    print("="*60)
    print("\nEste script irá configurar a autenticação do sistema.")
    print("Apenas usuários com usuário/senha poderão acessar.\n")

    senha = input("Digite uma senha forte para o administrador: ").strip()

    if len(senha) < 8:
        print("\n[ERRO] A senha deve ter pelo menos 8 caracteres!")
        return False

    confirma = input("Confirme a senha: ").strip()

    if senha != confirma:
        print("\n[ERRO] As senhas não coincidem!")
        return False

    # Solicitar endereço da floricultura (opcional)
    print("\n" + "-"*60)
    endereco_floricultura = input("Endereço da floricultura (opcional, Enter para pular): ").strip()
    if not endereco_floricultura:
        endereco_floricultura = "Rua Exemplo, 123, Bairro, Cidade - GO"

    # Conteúdo do arquivo .env
    env_content = f"""# ===========================================
# CONFIGURAÇÃO DE SEGURANÇA
# ===========================================

# Segurança - Autenticação (ATIVADA)
ENABLE_AUTH=true
ENABLE_RATE_LIMIT=true

# Usuário: admin
# Senha: (definida abaixo)
ADMIN_PASSWORD={senha}

# Ambiente
FLASK_ENV=production
USE_HTTPS=true

# Servidor
HOST=0.0.0.0
PORT=5000

# Desabilitar endpoints de debug em produção (segurança)
ENABLE_DEBUG_ENDPOINTS=false

# ===========================================
# APIS EXTERNAS
# ===========================================

OPENROUTE_API_KEY=
GRAPHHOPPER_API_KEY=
ENDERECO_FLORICULTURA={endereco_floricultura}

# ===========================================
# BACKUP
# ===========================================

ENABLE_AUTO_BACKUP=true
BACKUP_RETENTION_DAYS=30

# ===========================================
# SEGURANÇA AVANÇADA
# ===========================================

ALLOWED_IPS=
ENABLE_DETAILED_LOGGING=true
"""

    # Escrever arquivo .env
    try:
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)

        print("\n" + "="*60)
        print("[OK] Arquivo .env criado com sucesso!")
        print("="*60)
        print("\nConfigurações aplicadas:")
        print("  ✓ Autenticação: ATIVADA")
        print("  ✓ Rate Limiting: ATIVADO")
        print("  ✓ Usuário: admin")
        print(f"  ✓ Senha: {'*' * len(senha)}")
        print("  ✓ Debug Endpoints: DESATIVADOS")
        print("\n[INFO] O sistema está protegido!")
        print("[INFO] Acesso será solicitado ao abrir o navegador.")
        print("\n" + "="*60)

        return True

    except Exception as e:
        print(f"\n[ERRO] Erro ao criar arquivo .env: {e}")
        return False

if __name__ == '__main__':
    try:
        sucesso = create_env_file()

        if sucesso:
            print("\n[PRÓXIMO PASSO]")
            print("  1. Reinicie o servidor Flask")
            print("  2. Ao acessar o sistema, use:")
            print("     Usuário: admin")
            print("     Senha: (a senha que você definiu)")
            print("\n")

        sys.exit(0 if sucesso else 1)

    except KeyboardInterrupt:
        print("\n\n[INFO] Operação cancelada pelo usuário.")
        sys.exit(1)

