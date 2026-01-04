# -*- coding: utf-8 -*-
"""
Script de migração para normalizar valores de pedidos no banco de dados
Converte valores formatados (R$ X,XX) para formato numérico simples (X.XX)

Uso:
    python -m scripts.migrations.normalizar_valores_pedidos
    python -m scripts.migrations.normalizar_valores_pedidos --auto  # Executa sem confirmação
"""
import sqlite3
import re
import shutil
import sys
from pathlib import Path
from datetime import datetime


def parse_valor_to_float(valor_str):
    """
    Parse valor de qualquer formato para float
    Suporta:
    - Formato BR: "R$ 65,00", "65,00", "1.234,56"
    - Formato US: "10.00", "65.5"
    - String simples: "10", "65"
    - Números: 10.00, 65
    """
    if not valor_str:
        return None
    
    # Se já é número, retornar diretamente
    if isinstance(valor_str, (int, float)):
        return float(valor_str)
    
    valor_str = str(valor_str).strip()
    if not valor_str or valor_str == '':
        return None
    
    # Remover R$ e espaços
    cleaned = valor_str.replace("R$", "").replace("R$", "").strip()
    
    # Detectar formato brasileiro (tem vírgula)
    if "," in cleaned:
        # Formato BR: "65,00" ou "1.234,56"
        # Remover pontos (separadores de milhar) e substituir vírgula por ponto
        cleaned = cleaned.replace(".", "").replace(",", ".")
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    
    # Detectar formato americano ou numero simples (tem ponto decimal ou nao)
    if "." in cleaned:
        # Contar pontos - se tiver mais de 1, pode ser separador de milhar
        dot_count = cleaned.count(".")
        if dot_count == 1:
            # Um ponto = decimal americano: "10.00"
            try:
                return float(cleaned)
            except (ValueError, TypeError):
                return None
        else:
            # Múltiplos pontos = separadores de milhar: "1.234.567"
            # Remover todos os pontos
            cleaned = cleaned.replace(".", "")
            try:
                return float(cleaned)
            except (ValueError, TypeError):
                return None
    
    # String simples sem formatação: "10", "65"
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def format_valor_to_string(valor_float):
    """
    Formata float para string no formato numérico simples (X.XX)
    """
    if valor_float is None:
        return None
    return f"{valor_float:.2f}"


def is_valor_formatado_br(valor_str):
    """
    Verifica se o valor está em formato brasileiro (R$ X,XX ou X,XX)
    """
    if not valor_str or not isinstance(valor_str, str):
        return False
    
    # Verificar se tem R$ ou vírgula (formato BR)
    return "R$" in valor_str or ("," in valor_str and "." not in valor_str.replace(",", ""))


def normalize_valores_pedidos(auto_confirm=False):
    """
    Normaliza valores de pedidos no banco de dados
    Converte formato BR (R$ X,XX) para formato numérico simples (X.XX)
    
    Args:
        auto_confirm: Se True, executa sem pedir confirmação
    """
    # Encontrar banco de dados
    backend_dir = Path(__file__).parent.parent.parent
    possible_paths = [
        Path("C:/Users/caioc/var/lib/database/database.db"),
        backend_dir / "instance" / "database.db",
        backend_dir / "database.db",
        Path.home() / "var" / "lib" / "database" / "database.db",
    ]
    
    db_path = None
    for path in possible_paths:
        if path.exists():
            db_path = path
            break
    
    if not db_path:
        print("[ERRO] Banco de dados nao encontrado!")
        print("Procurou em:")
        for path in possible_paths:
            print(f"  - {path}")
        return False
    
    print(f"[INFO] Banco de dados encontrado: {db_path}")
    
    # Fazer backup antes de modificar
    backup_path = db_path.parent / f"database_backup_before_valor_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    print(f"[INFO] Criando backup: {backup_path}")
    try:
        shutil.copy2(db_path, backup_path)
        print(f"[OK] Backup criado com sucesso!")
    except Exception as e:
        print(f"[ERRO] Falha ao criar backup: {e}")
        if not auto_confirm:
            try:
                resposta = input("Deseja continuar mesmo assim? (s/N): ")
                if resposta.lower() != 's':
                    return False
            except EOFError:
                print("[ERRO] Nao foi possivel obter confirmacao. Use --auto para execucao automatica.")
                return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Buscar todos os pedidos com valor
        cursor.execute("SELECT id, valor FROM pedidos WHERE valor IS NOT NULL AND valor != ''")
        pedidos = cursor.fetchall()
        
        print(f"\n[INFO] Total de pedidos com valor: {len(pedidos)}")
        
        # Analisar quantos precisam ser convertidos
        precisam_conversao = []
        ja_normalizados = []
        erros = []
        
        for pedido_id, valor_original in pedidos:
            if is_valor_formatado_br(valor_original):
                precisam_conversao.append((pedido_id, valor_original))
            else:
                # Verificar se já está no formato correto
                valor_float = parse_valor_to_float(valor_original)
                if valor_float is not None:
                    ja_normalizados.append((pedido_id, valor_original))
                else:
                    erros.append((pedido_id, valor_original))
        
        print(f"\n[INFO] Analise:")
        print(f"  - Precisam conversao (formato BR): {len(precisam_conversao)}")
        print(f"  - Ja normalizados: {len(ja_normalizados)}")
        print(f"  - Com erro de parsing: {len(erros)}")
        
        if erros:
            print(f"\n[AVISO] Valores com erro de parsing:")
            for pedido_id, valor in erros[:10]:  # Mostrar apenas os 10 primeiros
                print(f"  - Pedido #{pedido_id}: '{valor}'")
            if len(erros) > 10:
                print(f"  ... e mais {len(erros) - 10} valores")
        
        if not precisam_conversao:
            print("\n[OK] Nenhum valor precisa ser convertido!")
            conn.close()
            return True
        
        # Mostrar preview dos valores que serão convertidos
        print(f"\n[INFO] Preview de conversoes (primeiros 10):")
        for pedido_id, valor_original in precisam_conversao[:10]:
            valor_float = parse_valor_to_float(valor_original)
            valor_novo = format_valor_to_string(valor_float)
            print(f"  - Pedido #{pedido_id}: '{valor_original}' -> '{valor_novo}'")
        
        if len(precisam_conversao) > 10:
            print(f"  ... e mais {len(precisam_conversao) - 10} valores")
        
        # Confirmar antes de executar
        print(f"\n[AVISO] Esta operacao ira modificar {len(precisam_conversao)} pedidos!")
        if not auto_confirm:
            try:
                resposta = input("Deseja continuar? (s/N): ")
                if resposta.lower() != 's':
                    print("[INFO] Operacao cancelada pelo usuario.")
                    conn.close()
                    return False
            except EOFError:
                print("[ERRO] Nao foi possivel obter confirmacao. Use --auto para execucao automatica.")
                conn.close()
                return False
        else:
            print("[INFO] Modo automatico: executando sem confirmacao...")
        
        # Executar conversao
        print(f"\n[INFO] Convertendo valores...")
        convertidos = 0
        falhas = 0
        
        for pedido_id, valor_original in precisam_conversao:
            try:
                valor_float = parse_valor_to_float(valor_original)
                if valor_float is None:
                    print(f"[AVISO] Pedido #{pedido_id}: Nao foi possivel converter '{valor_original}'")
                    falhas += 1
                    continue
                
                valor_novo = format_valor_to_string(valor_float)
                cursor.execute(
                    "UPDATE pedidos SET valor = ? WHERE id = ?",
                    (valor_novo, pedido_id)
                )
                convertidos += 1
                
                if convertidos % 100 == 0:
                    print(f"  [INFO] {convertidos} valores convertidos...")
                    
            except Exception as e:
                print(f"[ERRO] Pedido #{pedido_id}: Erro ao converter '{valor_original}': {e}")
                falhas += 1
        
        # Commit das alterações
        conn.commit()
        conn.close()
        
        print(f"\n[OK] Migracao concluida!")
        print(f"  - Valores convertidos: {convertidos}")
        print(f"  - Falhas: {falhas}")
        print(f"  - Backup salvo em: {backup_path}")
        
        return True
        
    except Exception as e:
        print(f"[ERRO] Erro durante migração: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    auto_mode = "--auto" in sys.argv
    
    print("=" * 70)
    print("Migracao: Normalizar Valores de Pedidos")
    print("=" * 70)
    print("Este script converte valores formatados (R$ X,XX) para formato")
    print("numerico simples (X.XX) no banco de dados.")
    if auto_mode:
        print("[MODO AUTOMATICO] Executando sem confirmacao...")
    print("=" * 70)
    normalize_valores_pedidos(auto_confirm=auto_mode)
    print("=" * 70)
