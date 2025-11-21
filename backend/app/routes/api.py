# -*- coding: utf-8 -*-
"""
Rotas da API REST - PWA v3.0
API completa para o frontend PWA
"""
from flask import Blueprint, request, jsonify
from app import db
from app.models import Pedido
from datetime import datetime
import re

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/pedidos', methods=['POST'])
def criar_pedido():
    """
    Cria novo pedido via API (usado pelo PWA)
    Compatível também com PDFgen.py existente
    """
    try:
        data = request.get_json()
        
        # Verificação inicial de dados
        if not data:
            return jsonify({'error': 'Nenhum dado fornecido'}), 400
        
        # Extração de dados do JSON
        # Step 1 - Dados do Cliente
        cliente = data.get('cliente', '').strip()
        telefone_cliente = data.get('telefone_cliente', data.get('telefone', '')).strip()
        destinatario = data.get('destinatario', '').strip()
        tipo_pedido = data.get('tipo_pedido', 'Entrega')
        
        # Step 2 - Produto e Agendamento
        produto = data.get('produto', '').strip()
        flores_cor = data.get('flores_cor', '').strip()
        valor = data.get('valor', '').strip()
        horario = data.get('horario', data.get('hora_entrega', '')).strip()
        dia_entrega_str = data.get('dia_entrega', data.get('data_entrega', '')).strip()
        
        # Step 3 - Logística
        endereco = data.get('endereco', '').strip()
        obs_entrega = data.get('obs_entrega', '').strip()
        
        # Step 4 - Finalização
        mensagem = data.get('mensagem', '').strip()
        pagamento = data.get('pagamento', '').strip()
        observacoes = data.get('observacoes', '').strip()
        
        # Quantidade (compatibilidade)
        quantidade_raw = data.get('quantidade', 1)
        
        # Validação de campos obrigatórios
        campos_obrigatorios = {
            'telefone_cliente': telefone_cliente,
            'destinatario': destinatario,
            'produto': produto,
            'horario': horario,
            'dia_entrega': dia_entrega_str
        }
        
        campos_faltantes = [campo for campo, valor in campos_obrigatorios.items() if not valor]
        if campos_faltantes:
            return jsonify({
                'error': f'Campos obrigatórios ausentes: {", ".join(campos_faltantes)}',
                'campos_enviados': list(data.keys())
            }), 400
        
        # Conversão de quantidade para inteiro
        try:
            if isinstance(quantidade_raw, str):
                quantidade_raw = quantidade_raw.strip()
            quantidade = int(quantidade_raw) if quantidade_raw and str(quantidade_raw).strip() else 1
            if quantidade < 0:
                quantidade = 1
        except (ValueError, TypeError):
            quantidade = 1
        
        # Validação de formato de horário (HH:MM)
        if not re.match(r'^([01]?\d|2[0-3]):[0-5]\d$', horario):
            return jsonify({
                'error': 'Formato de horário inválido',
                'horario_recebido': horario,
                'formato_esperado': 'HH:MM (ex: 14:30)'
            }), 400
        
        # Conversão de data de entrega
        try:
            # Aceita formatos: YYYY-MM-DD ou DD/MM/YYYY
            if '/' in dia_entrega_str:
                dia_entrega = datetime.strptime(dia_entrega_str, '%d/%m/%Y').date()
            else:
                dia_entrega = datetime.strptime(dia_entrega_str, '%Y-%m-%d').date()
        except ValueError as e:
            return jsonify({
                'error': 'Formato de data inválido',
                'data_recebida': dia_entrega_str,
                'formatos_aceitos': ['YYYY-MM-DD', 'DD/MM/YYYY'],
                'detalhes': str(e)
            }), 400
        
        # Criar instância do pedido
        pedido = Pedido(
            # Step 1
            cliente=cliente if cliente else None,
            telefone_cliente=telefone_cliente,
            destinatario=destinatario,
            tipo_pedido=tipo_pedido,
            # Step 2
            produto=produto,
            flores_cor=flores_cor if flores_cor else None,
            valor=valor if valor else None,
            horario=horario,
            dia_entrega=dia_entrega,
            # Step 3
            endereco=endereco if endereco else None,
            obs_entrega=obs_entrega if obs_entrega else None,
            # Step 4
            mensagem=mensagem if mensagem else None,
            pagamento=pagamento if pagamento else None,
            observacoes=observacoes if observacoes else None,
            # Controle
            status='agendado',
            quantidade=quantidade
        )
        
        # Inserir no banco de dados
        db.session.add(pedido)
        db.session.commit()
        
        # Resposta de sucesso
        return jsonify({
            'success': True,
            'pedido_id': pedido.id,
            'message': 'Pedido criado com sucesso',
            'pedido': pedido.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Erro interno do servidor',
            'detalhes': str(e)
        }), 500


@api_bp.route('/pedidos', methods=['GET'])
def listar_pedidos():
    """Lista todos os pedidos com filtros opcionais"""
    try:
        # Parâmetros de filtro
        status = request.args.get('status')
        limit = request.args.get('limit', type=int)
        search = request.args.get('search', '').strip()
        
        # Query base - excluir pedidos ocultos/arquivados
        query = Pedido.query.filter(Pedido.oculto == False)
        
        # Aplicar filtros
        if status:
            query = query.filter(Pedido.status == status)
        
        # Busca por cliente ou destinatário
        if search:
            query = query.filter(
                db.or_(
                    Pedido.cliente.ilike(f'%{search}%'),
                    Pedido.destinatario.ilike(f'%{search}%')
                )
            )
        
        # Ordenar por data de entrega e horário (mais recentes primeiro)
        query = query.order_by(Pedido.dia_entrega.desc(), Pedido.horario.desc())
        
        # Aplicar limite
        if limit:
            query = query.limit(limit)
        
        pedidos = query.all()
        
        return jsonify({
            'success': True,
            'count': len(pedidos),
            'pedidos': [p.to_dict() for p in pedidos]
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Erro interno do servidor',
            'detalhes': str(e)
        }), 500


@api_bp.route('/pedidos/<int:pedido_id>', methods=['GET'])
def obter_pedido(pedido_id):
    """Obtém pedido específico"""
    try:
        pedido = Pedido.query.get(pedido_id)
        
        if not pedido:
            return jsonify({
                'error': 'Pedido não encontrado',
                'pedido_id': pedido_id
            }), 404
        
        return jsonify({
            'success': True,
            'pedido': pedido.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Erro ao obter pedido',
            'detalhes': str(e)
        }), 500


@api_bp.route('/pedidos/<int:pedido_id>/status', methods=['PUT', 'POST'])
def atualizar_status(pedido_id):
    """Atualiza status do pedido"""
    try:
        data = request.get_json() or {}
        novo_status = data.get('status') or request.form.get('status')
        
        if not novo_status:
            return jsonify({'error': 'Status não fornecido'}), 400
        
        # Validar status
        status_validos = ['agendado', 'em_producao', 'pronto_entrega', 'em_rota', 'pronto_retirada', 'concluido']
        if novo_status not in status_validos:
            return jsonify({
                'error': 'Status inválido',
                'status_validos': status_validos
            }), 400
        
        # Atualizar pedido
        pedido = Pedido.query.get(pedido_id)
        
        if not pedido:
            return jsonify({
                'error': 'Pedido não encontrado',
                'pedido_id': pedido_id
            }), 404
        
        pedido.status = novo_status
        pedido.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Status atualizado para {novo_status}',
            'pedido': pedido.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Erro ao atualizar status',
            'detalhes': str(e)
        }), 500


@api_bp.route('/pedidos/<int:pedido_id>', methods=['PUT'])
def atualizar_pedido(pedido_id):
    """Atualiza dados completos do pedido"""
    try:
        pedido = Pedido.query.get(pedido_id)
        
        if not pedido:
            return jsonify({
                'error': 'Pedido não encontrado',
                'pedido_id': pedido_id
            }), 404
        
        data = request.get_json()
        
        # Atualizar campos fornecidos
        if 'cliente' in data:
            pedido.cliente = data['cliente']
        if 'telefone_cliente' in data:
            pedido.telefone_cliente = data['telefone_cliente']
        if 'destinatario' in data:
            pedido.destinatario = data['destinatario']
        if 'tipo_pedido' in data:
            pedido.tipo_pedido = data['tipo_pedido']
        if 'produto' in data:
            pedido.produto = data['produto']
        if 'flores_cor' in data:
            pedido.flores_cor = data['flores_cor']
        if 'valor' in data:
            pedido.valor = data['valor']
        if 'horario' in data:
            pedido.horario = data['horario']
        if 'dia_entrega' in data:
            dia_entrega_str = data['dia_entrega']
            if '/' in dia_entrega_str:
                pedido.dia_entrega = datetime.strptime(dia_entrega_str, '%d/%m/%Y').date()
            else:
                pedido.dia_entrega = datetime.strptime(dia_entrega_str, '%Y-%m-%d').date()
        if 'endereco' in data:
            pedido.endereco = data['endereco']
        if 'obs_entrega' in data:
            pedido.obs_entrega = data['obs_entrega']
        if 'mensagem' in data:
            pedido.mensagem = data['mensagem']
        if 'pagamento' in data:
            pedido.pagamento = data['pagamento']
        if 'observacoes' in data:
            pedido.observacoes = data['observacoes']
        if 'status' in data:
            pedido.status = data['status']
        
        pedido.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Pedido atualizado com sucesso',
            'pedido': pedido.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Erro ao atualizar pedido',
            'detalhes': str(e)
        }), 500


@api_bp.route('/pedidos/<int:pedido_id>', methods=['DELETE'])
def deletar_pedido(pedido_id):
    """Deleta pedido"""
    try:
        pedido = Pedido.query.get(pedido_id)
        
        if not pedido:
            return jsonify({
                'error': 'Pedido não encontrado',
                'pedido_id': pedido_id
            }), 404
        
        db.session.delete(pedido)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Pedido deletado com sucesso',
            'pedido_id': pedido_id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Erro ao deletar pedido',
            'detalhes': str(e)
        }), 500


@api_bp.route('/stats', methods=['GET'])
def obter_estatisticas():
    """Retorna estatísticas dos pedidos"""
    try:
        stats = Pedido.get_statistics()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'error': 'Erro ao obter estatísticas',
            'detalhes': str(e)
        }), 500


@api_bp.route('/pedidos/overdue', methods=['GET'])
def pedidos_atrasados():
    """Retorna pedidos atrasados"""
    try:
        overdue_pedidos = Pedido.get_overdue_pedidos()
        
        return jsonify({
            'success': True,
            'count': len(overdue_pedidos),
            'pedidos': [p.to_dict() for p in overdue_pedidos]
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Erro ao obter pedidos atrasados',
            'detalhes': str(e)
        }), 500


@api_bp.route('/cleanup', methods=['POST'])
def limpar_pedidos_antigos():
    """Arquiva (oculta) pedidos antigos - NÃO deleta do banco de dados"""
    try:
        data = request.get_json() or {}
        days = data.get('days', 1)
        
        count = Pedido.cleanup_old_pedidos(days=days)
        
        return jsonify({
            'success': True,
            'message': f'{count} pedidos antigos arquivados (ocultos da lista)',
            'count': count
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Erro ao limpar pedidos antigos',
            'detalhes': str(e)
        }), 500


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Verificar se o banco está acessível
        Pedido.query.count()
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'message': 'API funcionando normalmente'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500

