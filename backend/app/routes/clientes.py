# -*- coding: utf-8 -*-
"""
Rotas da API de Clientes - Sistema de Gestão de Clientes
API completa para gerenciar clientes, endereços, histórico e LTV
"""
from flask import Blueprint, request, jsonify
from app import db
from app.models import Cliente, EnderecoCliente, Pedido
from datetime import datetime
import re

clientes_bp = Blueprint('clientes', __name__, url_prefix='/api/clientes')


# ==================== CRUD DE CLIENTES ====================

@clientes_bp.route('', methods=['POST'])
def criar_cliente():
    """
    Cria novo cliente
    
    POST /api/clientes
    Body: {
        "nome": "João Silva",
        "telefone": "11999999999",
        "email": "joao@email.com",
        "observacoes": "Cliente VIP"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Nenhum dado fornecido'}), 400
        
        # Validar campos obrigatórios
        nome = data.get('nome', '').strip()
        telefone = data.get('telefone', '').strip()
        
        if not nome:
            return jsonify({'error': 'Nome é obrigatório'}), 400
        if not telefone:
            return jsonify({'error': 'Telefone é obrigatório'}), 400
        
        # Verificar se telefone já existe
        cliente_existente = Cliente.buscar_por_telefone(telefone)
        if cliente_existente:
            return jsonify({
                'error': 'Cliente já existe com este telefone',
                'cliente_id': cliente_existente.id,
                'nome': cliente_existente.nome
            }), 409
        
        # Criar cliente
        cliente = Cliente(
            nome=nome,
            telefone=telefone,
            email=data.get('email', '').strip() or None,
            observacoes=data.get('observacoes', '').strip() or None
        )
        
        db.session.add(cliente)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Cliente criado com sucesso',
            'cliente': cliente.to_dict(include_stats=True)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Erro ao criar cliente',
            'detalhes': str(e)
        }), 500


@clientes_bp.route('', methods=['GET'])
def listar_clientes():
    """
    Lista todos os clientes com filtros e paginação
    
    GET /api/clientes?search=joão&page=1&per_page=20&stats=true
    """
    try:
        # Parâmetros
        search = request.args.get('search', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        include_stats = request.args.get('stats', 'false').lower() == 'true'
        
        # Query base
        query = Cliente.query
        
        # Busca por nome ou telefone
        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                db.or_(
                    Cliente.nome.ilike(search_pattern),
                    Cliente.telefone.like(search_pattern)
                )
            )
        
        # Ordenar por nome
        query = query.order_by(Cliente.nome)
        
        # Paginação
        if per_page > 0:
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            clientes = pagination.items
            total = pagination.total
        else:
            clientes = query.all()
            total = len(clientes)
        
        return jsonify({
            'success': True,
            'total': total,
            'page': page,
            'per_page': per_page,
            'clientes': [c.to_dict(include_stats=include_stats) for c in clientes]
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Erro ao listar clientes',
            'detalhes': str(e)
        }), 500


@clientes_bp.route('/search', methods=['GET'])
def buscar_clientes_autocomplete():
    """
    Busca rápida para autocomplete
    
    GET /api/clientes/search?q=joão&limit=10
    """
    try:
        query_str = request.args.get('q', '').strip()
        limit = request.args.get('limit', 10, type=int)
        
        if not query_str or len(query_str) < 2:
            return jsonify({
                'success': True,
                'clientes': []
            })
        
        # Buscar por nome ou telefone
        search_pattern = f'%{query_str}%'
        clientes = Cliente.query.filter(
            db.or_(
                Cliente.nome.ilike(search_pattern),
                Cliente.telefone.like(search_pattern)
            )
        ).order_by(Cliente.nome).limit(limit).all()
        
        return jsonify({
            'success': True,
            'clientes': [c.to_dict_autocomplete() for c in clientes]
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Erro ao buscar clientes',
            'detalhes': str(e)
        }), 500


@clientes_bp.route('/<int:cliente_id>', methods=['GET'])
def obter_cliente(cliente_id):
    """
    Obtém cliente específico
    
    GET /api/clientes/123
    """
    try:
        cliente = Cliente.query.get(cliente_id)
        
        if not cliente:
            return jsonify({
                'error': 'Cliente não encontrado',
                'cliente_id': cliente_id
            }), 404
        
        return jsonify({
            'success': True,
            'cliente': cliente.to_dict(include_stats=True)
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Erro ao obter cliente',
            'detalhes': str(e)
        }), 500


@clientes_bp.route('/<int:cliente_id>', methods=['PUT'])
def atualizar_cliente(cliente_id):
    """
    Atualiza dados do cliente
    
    PUT /api/clientes/123
    Body: { "nome": "João Silva Atualizado", ... }
    """
    try:
        cliente = Cliente.query.get(cliente_id)
        
        if not cliente:
            return jsonify({
                'error': 'Cliente não encontrado',
                'cliente_id': cliente_id
            }), 404
        
        data = request.get_json()
        
        # Atualizar campos fornecidos
        if 'nome' in data:
            nome = data['nome'].strip()
            if not nome:
                return jsonify({'error': 'Nome não pode ser vazio'}), 400
            cliente.nome = nome
        
        if 'telefone' in data:
            telefone = data['telefone'].strip()
            if not telefone:
                return jsonify({'error': 'Telefone não pode ser vazio'}), 400
            
            # Verificar se telefone já existe (outro cliente)
            cliente_existente = Cliente.buscar_por_telefone(telefone)
            if cliente_existente and cliente_existente.id != cliente_id:
                return jsonify({
                    'error': 'Telefone já cadastrado para outro cliente',
                    'cliente_id': cliente_existente.id,
                    'nome': cliente_existente.nome
                }), 409
            
            cliente.telefone = telefone
        
        if 'email' in data:
            cliente.email = data['email'].strip() or None
        
        if 'observacoes' in data:
            cliente.observacoes = data['observacoes'].strip() or None
        
        cliente.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Cliente atualizado com sucesso',
            'cliente': cliente.to_dict(include_stats=True)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Erro ao atualizar cliente',
            'detalhes': str(e)
        }), 500


@clientes_bp.route('/<int:cliente_id>', methods=['DELETE'])
def deletar_cliente(cliente_id):
    """
    Deleta cliente
    
    DELETE /api/clientes/123
    """
    from app.utils.destructive_action_guard import ensure_backup_before_destructive_action, BackupRequiredException
    from app.schemas.common import error_response, success_response
    
    try:
        # Fail-closed: garantir backup antes de operação destrutiva (P0.2)
        try:
            ensure_backup_before_destructive_action(reason='delete_cliente', context={'cliente_id': cliente_id})
        except BackupRequiredException as backup_error:
            error_msg = str(backup_error)
            return error_response(
                'Backup necessário antes de operação destrutiva. Falha ao criar backup. Operação bloqueada por segurança.',
                503,
                details={'error': error_msg, 'cliente_id': cliente_id}
            )
        
        cliente = Cliente.query.get(cliente_id)
        
        if not cliente:
            return jsonify({
                'error': 'Cliente não encontrado',
                'cliente_id': cliente_id
            }), 404
        
        # Verificar se tem pedidos vinculados
        total_pedidos = cliente.get_total_pedidos()
        
        if total_pedidos > 0:
            return jsonify({
                'error': 'Não é possível deletar cliente com pedidos vinculados',
                'total_pedidos': total_pedidos,
                'sugestao': 'Desvincule os pedidos primeiro ou arquive o cliente'
            }), 400
        
        db.session.delete(cliente)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Cliente deletado com sucesso',
            'cliente_id': cliente_id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Erro ao deletar cliente',
            'detalhes': str(e)
        }), 500


# ==================== ESTATÍSTICAS E LTV ====================

@clientes_bp.route('/stats', methods=['GET'])
def obter_estatisticas():
    """
    Retorna estatísticas gerais dos clientes
    
    GET /api/clientes/stats
    """
    try:
        stats = Cliente.get_statistics()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Erro ao obter estatísticas',
            'detalhes': str(e)
        }), 500


@clientes_bp.route('/<int:cliente_id>/ltv', methods=['GET'])
def obter_ltv_cliente(cliente_id):
    """
    Calcula e retorna LTV do cliente
    
    GET /api/clientes/123/ltv
    """
    try:
        cliente = Cliente.query.get(cliente_id)
        
        if not cliente:
            return jsonify({
                'error': 'Cliente não encontrado',
                'cliente_id': cliente_id
            }), 404
        
        ltv = cliente.calcular_ltv()
        total_pedidos = cliente.get_total_pedidos()
        
        return jsonify({
            'success': True,
            'cliente_id': cliente_id,
            'nome': cliente.nome,
            'ltv': ltv,
            'total_pedidos': total_pedidos,
            'ticket_medio': round(ltv / total_pedidos, 2) if total_pedidos > 0 else 0
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Erro ao calcular LTV',
            'detalhes': str(e)
        }), 500


@clientes_bp.route('/<int:cliente_id>/pedidos', methods=['GET'])
def obter_pedidos_cliente(cliente_id):
    """
    Retorna histórico de pedidos do cliente
    
    GET /api/clientes/123/pedidos?limit=50
    """
    try:
        cliente = Cliente.query.get(cliente_id)
        
        if not cliente:
            return jsonify({
                'error': 'Cliente não encontrado',
                'cliente_id': cliente_id
            }), 404
        
        limit = request.args.get('limit', 50, type=int)
        
        # Buscar pedidos do cliente
        pedidos = cliente.pedidos.order_by(Pedido.created_at.desc()).limit(limit).all()
        
        return jsonify({
            'success': True,
            'cliente_id': cliente_id,
            'nome': cliente.nome,
            'total_pedidos': cliente.get_total_pedidos(),
            'pedidos': [p.to_dict() for p in pedidos]
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Erro ao obter pedidos',
            'detalhes': str(e)
        }), 500


# ==================== ENDEREÇOS ====================

@clientes_bp.route('/<int:cliente_id>/enderecos', methods=['GET'])
def listar_enderecos_cliente(cliente_id):
    """
    Lista endereços do cliente
    
    GET /api/clientes/123/enderecos
    """
    try:
        cliente = Cliente.query.get(cliente_id)
        
        if not cliente:
            return jsonify({
                'error': 'Cliente não encontrado',
                'cliente_id': cliente_id
            }), 404
        
        enderecos = cliente.enderecos.all()
        
        return jsonify({
            'success': True,
            'cliente_id': cliente_id,
            'total': len(enderecos),
            'enderecos': [e.to_dict() for e in enderecos]
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Erro ao listar endereços',
            'detalhes': str(e)
        }), 500


@clientes_bp.route('/<int:cliente_id>/enderecos', methods=['POST'])
def adicionar_endereco_cliente(cliente_id):
    """
    Adiciona novo endereço ao cliente
    
    POST /api/clientes/123/enderecos
    Body: {
        "apelido": "Casa",
        "cep": "74000-000",
        "rua": "Rua das Flores",
        "numero": "123",
        ...
    }
    """
    try:
        cliente = Cliente.query.get(cliente_id)
        
        if not cliente:
            return jsonify({
                'error': 'Cliente não encontrado',
                'cliente_id': cliente_id
            }), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Nenhum dado fornecido'}), 400
        
        # Criar endereço
        endereco = EnderecoCliente(
            cliente_id=cliente_id,
            apelido=data.get('apelido', '').strip() or None,
            cep=data.get('cep', '').strip() or None,
            rua=data.get('rua', '').strip() or None,
            numero=data.get('numero', '').strip() or None,
            complemento=data.get('complemento', '').strip() or None,
            bairro=data.get('bairro', '').strip() or None,
            cidade=data.get('cidade', '').strip() or None,
            estado=data.get('estado', 'GO').strip(),
            principal=data.get('principal', False)
        )
        
        # Se marcar como principal, desmarcar os outros
        if endereco.principal:
            EnderecoCliente.query.filter_by(cliente_id=cliente_id).update({'principal': False})
        
        db.session.add(endereco)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Endereço adicionado com sucesso',
            'endereco': endereco.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Erro ao adicionar endereço',
            'detalhes': str(e)
        }), 500


@clientes_bp.route('/enderecos/<int:endereco_id>', methods=['PUT'])
def atualizar_endereco(endereco_id):
    """
    Atualiza endereço existente
    
    PUT /api/clientes/enderecos/456
    """
    try:
        endereco = EnderecoCliente.query.get(endereco_id)
        
        if not endereco:
            return jsonify({
                'error': 'Endereço não encontrado',
                'endereco_id': endereco_id
            }), 404
        
        data = request.get_json()
        
        # Atualizar campos fornecidos
        if 'apelido' in data:
            endereco.apelido = data['apelido'].strip() or None
        if 'cep' in data:
            endereco.cep = data['cep'].strip() or None
        if 'rua' in data:
            endereco.rua = data['rua'].strip() or None
        if 'numero' in data:
            endereco.numero = data['numero'].strip() or None
        if 'complemento' in data:
            endereco.complemento = data['complemento'].strip() or None
        if 'bairro' in data:
            endereco.bairro = data['bairro'].strip() or None
        if 'cidade' in data:
            endereco.cidade = data['cidade'].strip() or None
        if 'estado' in data:
            endereco.estado = data['estado'].strip() or 'GO'
        if 'principal' in data:
            if data['principal']:
                # Desmarcar outros endereços do mesmo cliente
                EnderecoCliente.query.filter_by(cliente_id=endereco.cliente_id).update({'principal': False})
                endereco.principal = True
            else:
                endereco.principal = False
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Endereço atualizado com sucesso',
            'endereco': endereco.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Erro ao atualizar endereço',
            'detalhes': str(e)
        }), 500


@clientes_bp.route('/enderecos/<int:endereco_id>', methods=['DELETE'])
def deletar_endereco(endereco_id):
    """
    Deleta endereço
    
    DELETE /api/clientes/enderecos/456
    """
    from app.utils.destructive_action_guard import ensure_backup_before_destructive_action, BackupRequiredException
    from app.schemas.common import error_response
    
    try:
        # Fail-closed: garantir backup antes de operação destrutiva (P0.2)
        try:
            ensure_backup_before_destructive_action(reason='delete_endereco', context={'endereco_id': endereco_id})
        except BackupRequiredException as backup_error:
            error_msg = str(backup_error)
            return error_response(
                'Backup necessário antes de operação destrutiva. Falha ao criar backup. Operação bloqueada por segurança.',
                503,
                details={'error': error_msg, 'endereco_id': endereco_id}
            )
        
        endereco = EnderecoCliente.query.get(endereco_id)
        
        if not endereco:
            return jsonify({
                'error': 'Endereço não encontrado',
                'endereco_id': endereco_id
            }), 404
        
        db.session.delete(endereco)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Endereço deletado com sucesso',
            'endereco_id': endereco_id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Erro ao deletar endereço',
            'detalhes': str(e)
        }), 500


@clientes_bp.route('/enderecos/<int:endereco_id>/principal', methods=['POST'])
def marcar_endereco_principal(endereco_id):
    """
    Marca endereço como principal
    
    POST /api/clientes/enderecos/456/principal
    """
    try:
        endereco = EnderecoCliente.query.get(endereco_id)
        
        if not endereco:
            return jsonify({
                'error': 'Endereço não encontrado',
                'endereco_id': endereco_id
            }), 404
        
        endereco.marcar_como_principal()
        
        return jsonify({
            'success': True,
            'message': 'Endereço marcado como principal',
            'endereco': endereco.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Erro ao marcar endereço como principal',
            'detalhes': str(e)
        }), 500

