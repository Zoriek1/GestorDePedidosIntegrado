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
        
        # Step 3 - Logística (campos de endereço separados)
        cep = data.get('cep', '').strip()
        rua = data.get('rua', '').strip()
        numero = data.get('numero', '').strip()
        bairro = data.get('bairro', '').strip()
        cidade = data.get('cidade', '').strip()
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
            # Step 3 - Endereço
            cep=cep if cep else None,
            rua=rua if rua else None,
            numero=numero if numero else None,
            bairro=bairro if bairro else None,
            cidade=cidade if cidade else None,
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
        if 'cep' in data:
            pedido.cep = data['cep']
        if 'rua' in data:
            pedido.rua = data['rua']
        if 'numero' in data:
            pedido.numero = data['numero']
        if 'bairro' in data:
            pedido.bairro = data['bairro']
        if 'cidade' in data:
            pedido.cidade = data['cidade']
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


@api_bp.route('/pedidos/<int:pedido_id>/distancia', methods=['GET'])
def calcular_distancia_pedido(pedido_id):
    """Calcula e retorna a distância da floricultura até o endereço do pedido"""
    try:
        from app.services.distancia import distancia_service
        
        pedido = Pedido.query.get(pedido_id)
        
        if not pedido:
            return jsonify({
                'error': 'Pedido não encontrado',
                'pedido_id': pedido_id
            }), 404
        
        # Se já tem distância calculada, retornar do cache
        if pedido.distancia_km is not None:
            return jsonify({
                'success': True,
                'pedido_id': pedido_id,
                'distancia_km': pedido.distancia_km,
                'cached': True
            })
        
        # Calcular distância
        resultado = distancia_service.calcular_distancia_pedido(pedido.endereco)
        
        if resultado:
            # Salvar no banco para cache
            pedido.distancia_km = resultado['distancia_km']
            db.session.commit()
            
            return jsonify({
                'success': True,
                'pedido_id': pedido_id,
                'distancia_km': resultado['distancia_km'],
                'duracao_min': resultado['duracao_min'],
                'cached': False
            })
        else:
            return jsonify({
                'success': False,
                'pedido_id': pedido_id,
                'error': 'Não foi possível calcular a distância',
                'endereco': pedido.endereco
            })
            
    except Exception as e:
        return jsonify({
            'error': 'Erro ao calcular distância',
            'detalhes': str(e)
        }), 500


@api_bp.route('/pedidos/calcular-distancias', methods=['POST'])
def calcular_distancias_lote():
    """Calcula distâncias para múltiplos pedidos em lote"""
    try:
        from app.services.distancia import distancia_service
        
        data = request.get_json() or {}
        pedido_ids = data.get('pedido_ids', [])
        force_recalc = data.get('force_recalc', False)  # Forçar recálculo mesmo se já tiver cache
        
        if not pedido_ids:
            # Se não especificar IDs, calcular apenas para pedidos:
            # - Não ocultos
            # - Não concluídos (status != 'concluido')
            # - Tipo Entrega (tipo_pedido == 'Entrega')
            pedidos = Pedido.query.filter(
                Pedido.oculto == False,
                Pedido.status != 'concluido',
                Pedido.tipo_pedido == 'Entrega'
            ).all()
        else:
            # Se especificar IDs, aplicar os mesmos filtros
            pedidos = Pedido.query.filter(
                Pedido.id.in_(pedido_ids),
                Pedido.status != 'concluido',
                Pedido.tipo_pedido == 'Entrega'
            ).all()
        
        resultados = []
        calculados = 0
        do_cache = 0
        erros = 0
        ignorados = 0
        
        for pedido in pedidos:
            try:
                # Se já tem distância e não é forçado, usar cache
                if pedido.distancia_km is not None and not force_recalc:
                    resultados.append({
                        'id': pedido.id,
                        'distancia_km': pedido.distancia_km,
                        'cached': True
                    })
                    do_cache += 1
                    continue
                
                # Pular pedidos sem endereço
                if not pedido.endereco:
                    resultados.append({
                        'id': pedido.id,
                        'distancia_km': None,
                        'error': 'Sem endereço'
                    })
                    ignorados += 1
                    continue
                
                # Pular pedidos do tipo Retirada
                if pedido.tipo_pedido == 'Retirada':
                    resultados.append({
                        'id': pedido.id,
                        'distancia_km': None,
                        'error': 'Tipo Retirada - não requer entrega'
                    })
                    ignorados += 1
                    continue
                
                # Validar formato do endereço antes de tentar geocodificar
                valido, motivo = distancia_service.validar_endereco(pedido.endereco)
                if not valido:
                    resultados.append({
                        'id': pedido.id,
                        'distancia_km': None,
                        'error': f'Endereço inválido: {motivo}'
                    })
                    ignorados += 1
                    continue
                
                # Calcular distância
                resultado = distancia_service.calcular_distancia_pedido(pedido.endereco)
                
                if resultado:
                    pedido.distancia_km = resultado['distancia_km']
                    resultados.append({
                        'id': pedido.id,
                        'distancia_km': resultado['distancia_km'],
                        'duracao_min': resultado['duracao_min'],
                        'cached': False
                    })
                    calculados += 1
                else:
                    resultados.append({
                        'id': pedido.id,
                        'distancia_km': None,
                        'error': 'Falha na geocodificação'
                    })
                    erros += 1
                    
            except Exception as pedido_error:
                # Erro ao processar pedido individual - não interrompe o lote
                print(f"[ERRO] Erro ao calcular distância do pedido {pedido.id}: {pedido_error}")
                resultados.append({
                    'id': pedido.id,
                    'distancia_km': None,
                    'error': f'Erro interno: {str(pedido_error)[:50]}'
                })
                erros += 1
        
        # Salvar distâncias calculadas no banco
        try:
            db.session.commit()
        except Exception as commit_error:
            print(f"[ERRO] Erro ao salvar distâncias: {commit_error}")
            db.session.rollback()
        
        # Ordenar por distância (None no final)
        resultados.sort(key=lambda x: (x['distancia_km'] is None, x['distancia_km'] or 0))
        
        return jsonify({
            'success': True,
            'total': len(resultados),
            'calculados': calculados,
            'do_cache': do_cache,
            'erros': erros,
            'ignorados': ignorados,
            'resultados': resultados
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Erro ao calcular distâncias',
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

