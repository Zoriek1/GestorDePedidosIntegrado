# -*- coding: utf-8 -*-
"""
Script de Migração de Clientes
Migra dados de clientes dos pedidos existentes para a nova tabela de clientes
"""
import os
import sys
from pathlib import Path

# Adicionar diretório backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db
from app.models import Pedido, Cliente, EnderecoCliente
from collections import defaultdict


class MigradorClientes:
    """Migrador de clientes dos pedidos para tabela de clientes"""
    
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.clientes_criados = 0
        self.enderecos_criados = 0
        self.pedidos_vinculados = 0
        self.erros = []
        
    def executar(self):
        """Executa a migração completa"""
        print("\n" + "="*60)
        print("MIGRAÇÃO DE CLIENTES - Pedidos → Tabela Clientes")
        print("="*60)
        
        if self.dry_run:
            print("\n[DRY RUN] Modo de teste - nenhuma alteração será salva no banco")
        
        print("\n[1/4] Analisando pedidos existentes...")
        clientes_unicos = self.extrair_clientes_unicos()
        
        print(f"\n[2/4] Encontrados {len(clientes_unicos)} clientes únicos")
        
        if not clientes_unicos:
            print("\n[INFO] Nenhum cliente para migrar!")
            return
        
        print("\n[3/4] Criando registros de clientes...")
        self.criar_clientes(clientes_unicos)
        
        print("\n[4/4] Vinculando pedidos aos clientes...")
        self.vincular_pedidos()
        
        self.exibir_resumo()
    
    def extrair_clientes_unicos(self):
        """
        Extrai clientes únicos dos pedidos existentes
        Agrupa por telefone (chave única)
        """
        pedidos = Pedido.query.all()
        clientes_dict = defaultdict(lambda: {
            'pedidos': [],
            'enderecos': set()
        })
        
        print(f"[INFO] Analisando {len(pedidos)} pedidos...")
        
        for pedido in pedidos:
            telefone = pedido.telefone_cliente
            
            if not telefone:
                self.erros.append(f"Pedido #{pedido.id}: sem telefone")
                continue
            
            # Limpar telefone (remover formatação)
            telefone_limpo = ''.join(c for c in telefone if c.isdigit())
            
            if not telefone_limpo:
                self.erros.append(f"Pedido #{pedido.id}: telefone inválido")
                continue
            
            # Adicionar à lista de clientes
            cliente_data = clientes_dict[telefone_limpo]
            cliente_data['pedidos'].append(pedido)
            
            # Usar nome mais recente ou mais completo
            if pedido.cliente:
                if 'nome' not in cliente_data or len(pedido.cliente) > len(cliente_data.get('nome', '')):
                    cliente_data['nome'] = pedido.cliente
            
            # Coletar endereços únicos
            if pedido.endereco:
                cliente_data['enderecos'].add(pedido.endereco)
            
            # Armazenar dados de endereço separados
            if pedido.cep or pedido.rua:
                endereco_key = f"{pedido.cep}|{pedido.rua}|{pedido.numero}"
                if 'enderecos_detalhados' not in cliente_data:
                    cliente_data['enderecos_detalhados'] = {}
                
                cliente_data['enderecos_detalhados'][endereco_key] = {
                    'cep': pedido.cep,
                    'rua': pedido.rua,
                    'numero': pedido.numero,
                    'bairro': pedido.bairro,
                    'cidade': pedido.cidade
                }
        
        return dict(clientes_dict)
    
    def criar_clientes(self, clientes_dict):
        """Cria registros de clientes na tabela"""
        for telefone, dados in clientes_dict.items():
            try:
                # Verificar se cliente já existe
                cliente_existente = Cliente.buscar_por_telefone(telefone)
                
                if cliente_existente:
                    print(f"  [SKIP] Cliente já existe: {cliente_existente.nome} ({telefone})")
                    # Atualizar dados
                    dados['cliente_obj'] = cliente_existente
                    continue
                
                # Nome do cliente
                nome = dados.get('nome', f'Cliente {telefone}')
                
                # Criar cliente
                cliente = Cliente(
                    nome=nome,
                    telefone=telefone
                )
                
                if not self.dry_run:
                    db.session.add(cliente)
                    db.session.flush()  # Obter ID sem commit
                
                dados['cliente_obj'] = cliente
                self.clientes_criados += 1
                
                print(f"  [✓] {nome} ({telefone}) - {len(dados['pedidos'])} pedidos")
                
                # Criar endereços
                if not self.dry_run and 'enderecos_detalhados' in dados:
                    self.criar_enderecos(cliente, dados['enderecos_detalhados'])
                
            except Exception as e:
                erro_msg = f"Erro ao criar cliente {telefone}: {e}"
                self.erros.append(erro_msg)
                print(f"  [ERRO] {erro_msg}")
        
        if not self.dry_run:
            try:
                db.session.commit()
                print(f"\n[✓] {self.clientes_criados} clientes criados!")
            except Exception as e:
                db.session.rollback()
                print(f"\n[ERRO] Erro ao salvar clientes: {e}")
                raise
    
    def criar_enderecos(self, cliente, enderecos_dict):
        """Cria endereços para um cliente"""
        primeiro = True
        
        for endereco_key, endereco_data in enderecos_dict.items():
            try:
                # Verificar se tem dados suficientes
                if not endereco_data.get('rua') and not endereco_data.get('cep'):
                    continue
                
                # Criar endereço
                endereco = EnderecoCliente(
                    cliente_id=cliente.id,
                    cep=endereco_data.get('cep'),
                    rua=endereco_data.get('rua'),
                    numero=endereco_data.get('numero'),
                    bairro=endereco_data.get('bairro'),
                    cidade=endereco_data.get('cidade'),
                    principal=primeiro  # Primeiro endereço é principal
                )
                
                db.session.add(endereco)
                self.enderecos_criados += 1
                primeiro = False
                
            except Exception as e:
                erro_msg = f"Erro ao criar endereço para cliente {cliente.id}: {e}"
                self.erros.append(erro_msg)
    
    def vincular_pedidos(self):
        """Vincula pedidos existentes aos clientes criados"""
        pedidos = Pedido.query.filter(Pedido.cliente_id == None).all()
        
        print(f"[INFO] Vinculando {len(pedidos)} pedidos...")
        
        for pedido in pedidos:
            try:
                telefone = pedido.telefone_cliente
                if not telefone:
                    continue
                
                # Buscar cliente por telefone
                cliente = Cliente.buscar_por_telefone(telefone)
                
                if cliente:
                    if not self.dry_run:
                        pedido.cliente_id = cliente.id
                    self.pedidos_vinculados += 1
                else:
                    self.erros.append(f"Pedido #{pedido.id}: cliente não encontrado ({telefone})")
                
            except Exception as e:
                erro_msg = f"Erro ao vincular pedido #{pedido.id}: {e}"
                self.erros.append(erro_msg)
        
        if not self.dry_run:
            try:
                db.session.commit()
                print(f"\n[✓] {self.pedidos_vinculados} pedidos vinculados!")
            except Exception as e:
                db.session.rollback()
                print(f"\n[ERRO] Erro ao vincular pedidos: {e}")
                raise
    
    def exibir_resumo(self):
        """Exibe resumo da migração"""
        print("\n" + "="*60)
        print("RESUMO DA MIGRAÇÃO")
        print("="*60)
        
        if self.dry_run:
            print("\n[DRY RUN] Nenhuma alteração foi salva no banco")
        
        print(f"\n✅ Clientes criados: {self.clientes_criados}")
        print(f"✅ Endereços criados: {self.enderecos_criados}")
        print(f"✅ Pedidos vinculados: {self.pedidos_vinculados}")
        
        if self.erros:
            print(f"\n⚠️  Erros: {len(self.erros)}")
            print("\nPrimeiros 10 erros:")
            for erro in self.erros[:10]:
                print(f"  - {erro}")
        else:
            print("\n✨ Migração concluída sem erros!")
        
        print("\n" + "="*60 + "\n")


def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migração de Clientes dos Pedidos')
    parser.add_argument('--dry-run', action='store_true', help='Executa sem salvar no banco (teste)')
    
    args = parser.parse_args()
    
    # Criar aplicação Flask
    app = create_app()
    
    with app.app_context():
        # Criar migrador
        migrador = MigradorClientes(dry_run=args.dry_run)
        
        try:
            # Executar migração
            migrador.executar()
            
            if not args.dry_run:
                print("\n[SUCESSO] Migração concluída!")
                print("\nPróximos passos:")
                print("  1. Verifique os dados na tabela clientes")
                print("  2. Teste o autocomplete no formulário")
                print("  3. Acesse /clientes para ver a lista")
            else:
                print("\n[DRY RUN] Execute sem --dry-run para aplicar as mudanças")
            
        except Exception as e:
            print(f"\n[ERRO FATAL] {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == '__main__':
    main()

