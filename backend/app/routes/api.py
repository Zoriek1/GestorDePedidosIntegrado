# -*- coding: utf-8 -*-
"""
Rotas da API REST - PWA v3.0
API completa para o frontend PWA
"""
from flask import Blueprint, request, jsonify
from app import db
from app.models import Pedido, RotaOtimizada
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
        # Campos de endereço - se qualquer um mudar, limpar a distância para recalcular
        endereco_mudou = False
        if 'cep' in data and data['cep'] != pedido.cep:
            pedido.cep = data['cep']
            endereco_mudou = True
        if 'rua' in data and data['rua'] != pedido.rua:
            pedido.rua = data['rua']
            endereco_mudou = True
        if 'numero' in data and data['numero'] != pedido.numero:
            pedido.numero = data['numero']
            endereco_mudou = True
        if 'bairro' in data and data['bairro'] != pedido.bairro:
            pedido.bairro = data['bairro']
            endereco_mudou = True
        if 'cidade' in data and data['cidade'] != pedido.cidade:
            pedido.cidade = data['cidade']
            endereco_mudou = True
        if 'endereco' in data and data['endereco'] != pedido.endereco:
            pedido.endereco = data['endereco']
            endereco_mudou = True
        
        # Se o endereço mudou, limpar distância para forçar recálculo
        if endereco_mudou:
            pedido.distancia_km = None
            print(f"[DEBUG] Endereço do pedido {pedido_id} alterado - distância resetada")
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
def calcular_distancia_pedido_endpoint(pedido_id):
    """Calcula e retorna a distância da floricultura até o endereço do pedido"""
    try:
        from app.services.distancia import distancia_service
        
        pedido = Pedido.query.get(pedido_id)
        
        if not pedido:
            return jsonify({
                'error': 'Pedido não encontrado',
                'pedido_id': pedido_id
            }), 404
        
        # Verificar se tem query param force_recalc
        force_recalc = request.args.get('force_recalc', 'false').lower() == 'true'
        
        # Se já tem distância calculada e não é forçado, retornar do cache
        if pedido.distancia_km is not None and not force_recalc:
            print(f"[DEBUG] Pedido {pedido_id}: retornando distância do cache: {pedido.distancia_km} km")
            return jsonify({
                'success': True,
                'pedido_id': pedido_id,
                'distancia_km': pedido.distancia_km,
                'endereco': pedido.endereco,
                'cached': True
            })
        
        print(f"\n[DEBUG] ========== CALCULANDO DISTÂNCIA INDIVIDUAL ==========")
        print(f"[DEBUG] Pedido ID: {pedido_id}")
        print(f"[DEBUG] Endereço completo: {pedido.endereco}")
        print(f"[DEBUG] Campos: rua={pedido.rua}, num={pedido.numero}, bairro={pedido.bairro}, cidade={pedido.cidade}, cep={pedido.cep}")
        print(f"[DEBUG] Forçar recálculo: {force_recalc}")
        
        # Calcular distância usando campos separados para melhor precisão
        resultado = distancia_service.calcular_distancia_pedido(
            endereco_pedido=pedido.endereco,
            pedido_id=pedido_id,
            rua=pedido.rua,
            numero=pedido.numero,
            bairro=pedido.bairro,
            cidade=pedido.cidade,
            cep=pedido.cep
        )
        
        if resultado:
            # Salvar no banco para cache
            pedido.distancia_km = resultado['distancia_km']
            # Salvar coordenadas se disponíveis
            if 'coords_destino_lat' in resultado:
                pedido.coords_lat = resultado['coords_destino_lat']
            if 'coords_destino_lon' in resultado:
                pedido.coords_lon = resultado['coords_destino_lon']
            db.session.commit()
            
            return jsonify({
                'success': True,
                'pedido_id': pedido_id,
                'distancia_km': resultado['distancia_km'],
                'duracao_min': resultado['duracao_min'],
                'endereco': pedido.endereco,
                'coords_destino': resultado.get('coords_destino'),
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
        print(f"[ERRO] Exceção ao calcular distância do pedido {pedido_id}: {e}")
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
                
                # Calcular distância usando campos separados para melhor precisão
                resultado = distancia_service.calcular_distancia_pedido(
                    endereco_pedido=pedido.endereco,
                    pedido_id=pedido.id,
                    rua=pedido.rua,
                    numero=pedido.numero,
                    bairro=pedido.bairro,
                    cidade=pedido.cidade,
                    cep=pedido.cep
                )
                
                if resultado:
                    pedido.distancia_km = resultado['distancia_km']
                    # Salvar coordenadas se disponíveis
                    if 'coords_destino_lat' in resultado:
                        pedido.coords_lat = resultado['coords_destino_lat']
                    if 'coords_destino_lon' in resultado:
                        pedido.coords_lon = resultado['coords_destino_lon']
                    resultados.append({
                        'id': pedido.id,
                        'distancia_km': resultado['distancia_km'],
                        'duracao_min': resultado['duracao_min'],
                        'endereco': pedido.endereco,
                        'coords_destino': resultado.get('coords_destino'),
                        'cached': False
                    })
                    calculados += 1
                else:
                    resultados.append({
                        'id': pedido.id,
                        'distancia_km': None,
                        'endereco': pedido.endereco,
                        'campos': {
                            'rua': pedido.rua,
                            'numero': pedido.numero,
                            'bairro': pedido.bairro,
                            'cidade': pedido.cidade,
                            'cep': pedido.cep
                        },
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


@api_bp.route('/pedidos/<int:pedido_id>/calcular-taxa', methods=['POST'])
def calcular_taxa_pedido(pedido_id):
    """Calcula e retorna a taxa de entrega para um pedido"""
    try:
        from app.services.distancia import distancia_service
        from app.services.taxa_entrega import taxa_entrega_service
        
        pedido = Pedido.query.get(pedido_id)
        
        if not pedido:
            return jsonify({
                'error': 'Pedido não encontrado',
                'pedido_id': pedido_id
            }), 404
        
        # Verificar se já tem distância calculada
        if pedido.distancia_km is None:
            # Calcular distância primeiro
            resultado = distancia_service.calcular_distancia_pedido(
                endereco_pedido=pedido.endereco,
                pedido_id=pedido_id,
                rua=pedido.rua,
                numero=pedido.numero,
                bairro=pedido.bairro,
                cidade=pedido.cidade,
                cep=pedido.cep
            )
            
            if not resultado:
                return jsonify({
                    'success': False,
                    'pedido_id': pedido_id,
                    'error': 'Não foi possível calcular a distância para calcular a taxa',
                    'endereco': pedido.endereco
                }), 400
            
            # Salvar distância e coordenadas
            pedido.distancia_km = resultado['distancia_km']
            if 'coords_destino_lat' in resultado:
                pedido.coords_lat = resultado['coords_destino_lat']
            if 'coords_destino_lon' in resultado:
                pedido.coords_lon = resultado['coords_destino_lon']
            db.session.commit()
        
        # Calcular taxa de entrega
        taxa = taxa_entrega_service.calcular_taxa(pedido.distancia_km)
        
        # Salvar taxa no pedido
        pedido.taxa_entrega = taxa
        db.session.commit()
        
        return jsonify({
            'success': True,
            'pedido_id': pedido_id,
            'distancia_km': pedido.distancia_km,
            'taxa_entrega': taxa,
            'endereco': pedido.endereco
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERRO] Exceção ao calcular taxa do pedido {pedido_id}: {e}")
        return jsonify({
            'error': 'Erro ao calcular taxa de entrega',
            'detalhes': str(e)
        }), 500


@api_bp.route('/pedidos/rota-otimizada', methods=['POST'])
def calcular_rota_otimizada():
    """Calcula rota otimizada para múltiplos pedidos"""
    try:
        from app.services.distancia import distancia_service
        from app.services.graphhopper import graphhopper_service
        from app.models import RotaOtimizada
        
        data = request.get_json() or {}
        pedido_ids = data.get('pedido_ids', [])
        nome_rota = data.get('nome', 'Rota Otimizada')
        
        if not pedido_ids:
            # Se não especificar IDs, usar pedidos elegíveis
            pedidos = Pedido.query.filter(
                Pedido.oculto == False,
                Pedido.status != 'concluido',
                Pedido.tipo_pedido == 'Entrega',
                Pedido.distancia_km.isnot(None)  # Apenas pedidos com distância calculada
            ).all()
        else:
            pedidos = Pedido.query.filter(
                Pedido.id.in_(pedido_ids),
                Pedido.status != 'concluido',
                Pedido.tipo_pedido == 'Entrega'
            ).all()
        
        if len(pedidos) < 2:
            return jsonify({
                'error': 'É necessário pelo menos 2 pedidos para calcular rota otimizada',
                'pedidos_encontrados': len(pedidos)
            }), 400
        
        # Obter coordenadas da floricultura
        origem = distancia_service.coords_floricultura
        if not origem:
            return jsonify({
                'error': 'Não foi possível obter coordenadas da floricultura'
            }), 500
        
        # Converter para formato (lat, lon) para GraphHopper
        origem_gh = (origem[1], origem[0])
        
        # Coletar waypoints dos pedidos (apenas os que têm coordenadas)
        waypoints = []
        pedidos_com_coords = []
        
        for pedido in pedidos:
            if pedido.coords_lat and pedido.coords_lon:
                waypoints.append((pedido.coords_lat, pedido.coords_lon))
                pedidos_com_coords.append(pedido)
            else:
                # Tentar geocodificar se não tiver coordenadas
                resultado = distancia_service.calcular_distancia_pedido(
                    endereco_pedido=pedido.endereco,
                    pedido_id=pedido.id,
                    rua=pedido.rua,
                    numero=pedido.numero,
                    bairro=pedido.bairro,
                    cidade=pedido.cidade,
                    cep=pedido.cep
                )
                
                if resultado and 'coords_destino_lat' in resultado:
                    lat = resultado['coords_destino_lat']
                    lon = resultado['coords_destino_lon']
                    waypoints.append((lat, lon))
                    pedido.coords_lat = lat
                    pedido.coords_lon = lon
                    pedidos_com_coords.append(pedido)
        
        if len(waypoints) < 2:
            return jsonify({
                'error': 'É necessário pelo menos 2 pedidos com coordenadas válidas',
                'waypoints_encontrados': len(waypoints)
            }), 400
        
        # Calcular rota otimizada
        resultado_rota = graphhopper_service.calcular_rota_otimizada(
            origem_gh, waypoints, retornar_origem=True
        )
        
        if not resultado_rota:
            return jsonify({
                'error': 'Não foi possível calcular rota otimizada'
            }), 500
        
        # Mapear waypoints otimizados de volta para pedidos
        sequencia_pedidos = []
        waypoints_otimizados = resultado_rota.get('sequencia_otimizada', [])
        
        # Criar mapeamento de coordenadas para pedidos (com tolerância para diferenças de precisão)
        import math
        
        # Se não temos waypoints otimizados, usar ordem original
        if not waypoints_otimizados:
            sequencia_pedidos = [p.id for p in pedidos_com_coords]
        else:
            # Criar lista de pedidos disponíveis (não usados ainda)
            pedidos_disponiveis = pedidos_com_coords.copy()
            
            # Para cada waypoint otimizado, encontrar o pedido mais próximo
            for waypoint in waypoints_otimizados:
                if not pedidos_disponiveis:
                    break
                
                pedido_encontrado = None
                menor_dist = float('inf')
                indice_encontrado = -1
                
                # Encontrar pedido mais próximo deste waypoint
                for i, pedido in enumerate(pedidos_disponiveis):
                    if pedido.coords_lat and pedido.coords_lon:
                        # Calcular distância em graus (aproximação)
                        dist = math.sqrt(
                            (pedido.coords_lat - waypoint[0])**2 + 
                            (pedido.coords_lon - waypoint[1])**2
                        )
                        if dist < menor_dist:
                            menor_dist = dist
                            pedido_encontrado = pedido
                            indice_encontrado = i
                
                # Adicionar pedido encontrado à sequência e remover da lista disponível
                if pedido_encontrado:
                    sequencia_pedidos.append(pedido_encontrado.id)
                    pedidos_disponiveis.pop(indice_encontrado)
            
            # Adicionar pedidos restantes que não foram mapeados
            for pedido in pedidos_disponiveis:
                if pedido.id not in sequencia_pedidos:
                    sequencia_pedidos.append(pedido.id)
        
        # Salvar rota no banco
        rota = RotaOtimizada(
            nome=nome_rota,
            distancia_total_km=resultado_rota['distancia_total_km'],
            duracao_total_min=resultado_rota['duracao_total_min'],
            origem_lat=origem[1],
            origem_lon=origem[0],
            num_pedidos=len(sequencia_pedidos),
            metodo_otimizacao=resultado_rota.get('metodo', 'nearest_neighbor')
        )
        rota.set_sequencia_pedidos(sequencia_pedidos)
        rota.set_waypoints_coords(waypoints_otimizados)
        
        db.session.add(rota)
        
        # Salvar coordenadas dos pedidos se ainda não tiverem
        try:
            db.session.commit()
        except Exception as commit_error:
            print(f"[ERRO] Erro ao salvar rota: {commit_error}")
            db.session.rollback()
            raise
        
        return jsonify({
            'success': True,
            'rota_id': rota.id,
            'nome': rota.nome,
            'distancia_total_km': rota.distancia_total_km,
            'duracao_total_min': rota.duracao_total_min,
            'sequencia_pedidos': rota.get_sequencia_pedidos(),
            'num_pedidos': rota.num_pedidos,
            'metodo_otimizacao': rota.metodo_otimizacao,
            'origem': {
                'lat': rota.origem_lat,
                'lon': rota.origem_lon
            },
            'waypoints': rota.get_waypoints_coords()
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERRO] Exceção ao calcular rota otimizada: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Erro ao calcular rota otimizada',
            'detalhes': str(e)
        }), 500


@api_bp.route('/pedidos/rota-otimizada/<int:rota_id>', methods=['GET'])
def obter_rota_otimizada(rota_id):
    """Obtém detalhes de uma rota otimizada"""
    try:
        from app.models import RotaOtimizada
        
        rota = RotaOtimizada.query.get(rota_id)
        
        if not rota:
            return jsonify({
                'error': 'Rota não encontrada',
                'rota_id': rota_id
            }), 404
        
        # Buscar informações dos pedidos na sequência
        pedidos_info = []
        for pedido_id in rota.get_sequencia_pedidos():
            pedido = Pedido.query.get(pedido_id)
            if pedido:
                pedidos_info.append({
                    'id': pedido.id,
                    'cliente': pedido.cliente,
                    'destinatario': pedido.destinatario,
                    'endereco': pedido.endereco,
                    'distancia_km': pedido.distancia_km,
                    'coords_lat': pedido.coords_lat,
                    'coords_lon': pedido.coords_lon
                })
        
        return jsonify({
            'success': True,
            'rota': rota.to_dict(),
            'pedidos': pedidos_info
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Erro ao obter rota otimizada',
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


@api_bp.route('/debug/geocode', methods=['GET', 'POST'])
def debug_geocode():
    """
    Endpoint de debug para testar geocodificação de um endereço.
    Mostra detalhes completos do que a API retorna.
    
    GET: /api/debug/geocode?endereco=Rua+X,+123
    GET: /api/debug/geocode?rua=Rua+X&numero=123&bairro=Centro&cidade=Goiania&cep=74000000
    POST: {"endereco": "Rua X, 123"} ou {"rua": "Rua X", "numero": "123", ...}
    """
    try:
        from app.services.distancia import distancia_service
        import requests
        
        # Aceitar tanto GET (query param) quanto POST (json body)
        if request.method == 'GET':
            endereco = request.args.get('endereco', '')
            rua = request.args.get('rua', '')
            numero = request.args.get('numero', '')
            bairro = request.args.get('bairro', '')
            cidade = request.args.get('cidade', '')
            cep = request.args.get('cep', '')
        else:
            data = request.get_json() or {}
            endereco = data.get('endereco', '')
            rua = data.get('rua', '')
            numero = data.get('numero', '')
            bairro = data.get('bairro', '')
            cidade = data.get('cidade', '')
            cep = data.get('cep', '')
        
        # Verificar se tem campos separados ou endereço completo
        tem_campos_separados = rua or bairro or cep
        
        if not endereco and not tem_campos_separados:
            return jsonify({
                'error': 'Endereço é obrigatório',
                'uso': [
                    'GET /api/debug/geocode?endereco=Rua+X,+123,+Bairro,+Cidade',
                    'GET /api/debug/geocode?rua=Rua+X&numero=123&bairro=Centro&cidade=Goiania&cep=74000000',
                    'POST {"endereco": "Rua X, 123"}',
                    'POST {"rua": "Rua X", "numero": "123", "bairro": "Centro", "cidade": "Goiânia", "cep": "74000-000"}'
                ]
            }), 400
        
        print(f"\n[DEBUG] ========== TESTE DE GEOCODIFICAÇÃO ==========")
        print(f"[DEBUG] Endereço original: {endereco}")
        print(f"[DEBUG] Campos separados: rua={rua}, num={numero}, bairro={bairro}, cidade={cidade}, cep={cep}")
        
        # Construir endereço otimizado para geocodificação
        if tem_campos_separados:
            endereco_para_geocode = distancia_service.construir_endereco_para_geocode(
                rua=rua,
                numero=numero,
                bairro=bairro,
                cidade=cidade,
                cep=cep,
                endereco_completo=endereco
            )
            print(f"[DEBUG] Endereço construído dos campos: {endereco_para_geocode}")
        else:
            endereco_para_geocode = distancia_service.limpar_endereco(endereco)
            print(f"[DEBUG] Endereço limpo: {endereco_para_geocode}")
        
        # Usar a função de geocodificação do serviço (usa Nominatim + OpenRouteService)
        print(f"[DEBUG] Chamando geocodificar()...")
        coords = distancia_service.geocodificar(endereco_para_geocode, normalizar=False)
        
        if not coords:
            return jsonify({
                'success': False,
                'endereco_original': endereco,
                'campos_separados': {
                    'rua': rua,
                    'numero': numero,
                    'bairro': bairro,
                    'cidade': cidade,
                    'cep': cep
                } if tem_campos_separados else None,
                'endereco_para_geocode': endereco_para_geocode,
                'error': 'Nenhum resultado encontrado (Nominatim e OpenRouteService falharam)',
                'dica': 'Verifique se o endereço está correto e completo. Tente com: Rua, Número, Bairro, Cidade'
            })
        
        # Calcular distância da floricultura
        distancia = None
        duracao = None
        coords_floricultura = distancia_service.coords_floricultura
        
        if coords_floricultura:
            resultado_dist = distancia_service.calcular_distancia(coords_floricultura, coords)
            if resultado_dist:
                distancia = resultado_dist['distancia_km']
                duracao = resultado_dist['duracao_min']
        
        return jsonify({
            'success': True,
            'endereco_original': endereco,
            'campos_separados': {
                'rua': rua,
                'numero': numero,
                'bairro': bairro,
                'cidade': cidade,
                'cep': cep
            } if tem_campos_separados else None,
            'endereco_para_geocode': endereco_para_geocode,
            'coords': {
                'longitude': coords[0],
                'latitude': coords[1]
            },
            'google_maps_link': f"https://www.google.com/maps?q={coords[1]},{coords[0]}",
            'distancia_km': distancia,
            'duracao_min': duracao,
            'coords_floricultura': {
                'longitude': coords_floricultura[0] if coords_floricultura else None,
                'latitude': coords_floricultura[1] if coords_floricultura else None
            } if coords_floricultura else None
        })
        
    except Exception as e:
        print(f"[ERRO] Exceção no debug de geocodificação: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Erro ao testar geocodificação',
            'detalhes': str(e)
        }), 500


@api_bp.route('/debug/limpar-distancias', methods=['POST'])
def debug_limpar_distancias():
    """
    Endpoint de debug para limpar todas as distâncias cacheadas.
    Força recálculo na próxima chamada.
    """
    try:
        # Limpar todas as distâncias
        pedidos = Pedido.query.filter(Pedido.distancia_km.isnot(None)).all()
        count = len(pedidos)
        
        for pedido in pedidos:
            pedido.distancia_km = None
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{count} distâncias limpas do cache',
            'count': count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Erro ao limpar distâncias',
            'detalhes': str(e)
        }), 500


@api_bp.route('/debug/config-floricultura', methods=['GET'])
def debug_config_floricultura():
    """
    Endpoint de debug para verificar a configuração da floricultura.
    Mostra o endereço configurado e as coordenadas geocodificadas.
    """
    try:
        from app.services.distancia import distancia_service
        import os
        
        endereco = os.environ.get('ENDERECO_FLORICULTURA', '')
        api_key = os.environ.get('OPENROUTE_API_KEY', '')
        
        # Forçar re-geocodificação da floricultura
        distancia_service._coords_floricultura = None
        coords = distancia_service.coords_floricultura
        
        return jsonify({
            'success': True,
            'endereco_configurado': endereco,
            'api_key_configurada': bool(api_key),
            'api_key_preview': api_key[:20] + '...' if api_key else None,
            'coords_floricultura': {
                'longitude': coords[0] if coords else None,
                'latitude': coords[1] if coords else None
            } if coords else None,
            'google_maps_link': f"https://www.google.com/maps?q={coords[1]},{coords[0]}" if coords else None,
            'status': 'OK' if coords else 'ERRO - Não foi possível geocodificar'
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Erro ao verificar configuração',
            'detalhes': str(e)
        }), 500


@api_bp.route('/debug/reset-floricultura', methods=['POST'])
def debug_reset_floricultura():
    """
    Força recálculo das coordenadas da floricultura.
    """
    try:
        from app.services.distancia import distancia_service
        
        # Limpar cache
        distancia_service._coords_floricultura = None
        distancia_service._enderecos_invalidos.clear()
        
        # Forçar re-geocodificação
        coords = distancia_service.coords_floricultura
        
        return jsonify({
            'success': True,
            'message': 'Cache da floricultura limpo e recalculado',
            'endereco': distancia_service.endereco_floricultura,
            'coords': {
                'longitude': coords[0] if coords else None,
                'latitude': coords[1] if coords else None
            } if coords else None,
            'google_maps_link': f"https://www.google.com/maps?q={coords[1]},{coords[0]}" if coords else None
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Erro ao resetar floricultura',
            'detalhes': str(e)
        }), 500

