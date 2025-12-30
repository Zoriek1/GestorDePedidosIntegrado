# -*- coding: utf-8 -*-
"""
Rotas de Pedidos - Blueprint para endpoints de pedidos
"""
from flask import Blueprint, request
from datetime import datetime
from app.repositories.pedido_repository import PedidoRepository
from app.schemas.common import success_response, error_response
from app.schemas.pedido_schema import PedidoSchema, PedidoCreateSchema, PedidoUpdateSchema
from app.middleware import requires_edit_auth
from app.utils.backup_helper import create_backup
import importlib.util
from pathlib import Path

pedidos_bp = Blueprint('pedidos', __name__, url_prefix='/api/pedidos')

pedido_repo = PedidoRepository()
pedido_schema = PedidoSchema()
pedido_create_schema = PedidoCreateSchema()
pedido_update_schema = PedidoUpdateSchema()


@pedidos_bp.route('', methods=['GET'])
def listar_pedidos():
    """Lista pedidos com filtros opcionais"""
    try:
        status = request.args.get('status')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        search = request.args.get('search')
        
        # Converter datas se fornecidas
        data_inicio_obj = None
        data_fim_obj = None
        if data_inicio:
            try:
                data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            except ValueError:
                return error_response('Formato de data_inicio inválido. Use YYYY-MM-DD', 400)
        if data_fim:
            try:
                data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
            except ValueError:
                return error_response('Formato de data_fim inválido. Use YYYY-MM-DD', 400)
        
        pedidos = pedido_repo.buscar_com_filtros(
            status=status,
            data_inicio=data_inicio_obj,
            data_fim=data_fim_obj,
            search=search
        )
        
        # Serializar pedidos
        pedidos_data = [p.to_dict() for p in pedidos]
        
        return success_response({'pedidos': pedidos_data, 'total': len(pedidos_data)})
    except Exception as e:
        return error_response(f'Erro ao listar pedidos: {str(e)}', 500)


@pedidos_bp.route('/<int:pedido_id>', methods=['GET'])
def obter_pedido(pedido_id):
    """Obtém pedido por ID"""
    try:
        pedido = pedido_repo.get_by_id(pedido_id)
        if not pedido:
            return error_response('Pedido não encontrado', 404)
        
        return success_response({'pedido': pedido.to_dict()})
    except Exception as e:
        return error_response(f'Erro ao obter pedido: {str(e)}', 500)


@pedidos_bp.route('/<int:pedido_id>/status', methods=['PUT', 'POST'])
@requires_edit_auth
def atualizar_status(pedido_id):
    """Atualiza status de um pedido"""
    try:
        data = request.get_json() or {}
        novo_status = data.get('status', '').strip()
        
        if not novo_status:
            return error_response('Status é obrigatório', 400)
        
        pedido = pedido_repo.atualizar_status(pedido_id, novo_status)
        if not pedido:
            return error_response('Pedido não encontrado', 404)
        
        return success_response(
            {'pedido': pedido.to_dict()},
            message='Status atualizado com sucesso'
        )
    except Exception as e:
        return error_response(f'Erro ao atualizar status: {str(e)}', 500)


@pedidos_bp.route('/<int:pedido_id>', methods=['DELETE'])
@requires_edit_auth
def deletar_pedido(pedido_id):
    """Deleta pedido"""
    from app import db
    from app.models.pedido import Pedido
    from sqlalchemy import text
    
    try:
        # Criar backup antes de deletar (CRÍTICO) - em try/except separado
        try:
            create_backup(reason='critical_operation', silent=True)
        except Exception as backup_error:
            print(f"[AVISO] Falha ao criar backup antes de deletar: {backup_error}")
            # Continuar mesmo se backup falhar
        
        # Primeiro verificar se pedido existe
        pedido_exists = Pedido.query.filter_by(id=pedido_id).first()
        if not pedido_exists:
            return error_response('Pedido não encontrado', 404)
        
        # Verificar se é SQLite (necessário para desabilitar foreign keys)
        engine = db.engine
        is_sqlite = 'sqlite' in str(engine.url).lower()
        
        # Tentar deletar usando query direta (mais robusto para objetos com relacionamentos)
        try:
            # SQLite: Desabilitar temporariamente verificação de foreign keys
            # Isso permite deletar mesmo se houver referências em outras tabelas
            # (as referências devem ser nullable ou serão limpas depois)
            
            if is_sqlite:
                db.session.execute(text('PRAGMA foreign_keys = OFF'))
            
            # Abordagem 1: Query direta de DELETE (evita problemas de sessão/relacionamentos)
            result = db.session.execute(
                text('DELETE FROM pedidos WHERE id = :pedido_id'),
                {'pedido_id': pedido_id}
            )
            db.session.commit()
            
            # Reabilitar verificação de foreign keys (SQLite)
            if is_sqlite:
                db.session.execute(text('PRAGMA foreign_keys = ON'))
            
            if result.rowcount == 0:
                # Se nenhuma linha foi deletada, pode ter sido deletado concorrentemente
                return error_response('Pedido não encontrado ou já foi deletado', 404)
            
            print(f"[SUCCESS] Pedido #{pedido_id} deletado com sucesso (via DELETE direto)")
            return success_response(message='Pedido deletado com sucesso')
            
        except Exception as delete_error:
            db.session.rollback()
            # Reabilitar foreign keys mesmo em caso de erro
            if is_sqlite:
                try:
                    db.session.execute(text('PRAGMA foreign_keys = ON'))
                except:
                    pass
            
            # Se DELETE direto falhar, tentar abordagem tradicional
            print(f"[AVISO] DELETE direto falhou, tentando abordagem tradicional: {delete_error}")
            try:
                # Desabilitar foreign keys novamente (SQLite)
                if is_sqlite:
                    db.session.execute(text('PRAGMA foreign_keys = OFF'))
                
                # Limpar qualquer objeto da sessão que possa estar causando conflito
                db.session.expunge_all()
                
                # Buscar pedido novamente na sessão limpa
                pedido = Pedido.query.get(pedido_id)
                if not pedido:
                    # Reabilitar antes de retornar (SQLite)
                    if is_sqlite:
                        try:
                            db.session.execute(text('PRAGMA foreign_keys = ON'))
                        except:
                            pass
                    return error_response('Pedido não encontrado', 404)
                
                # Deletar objeto
                db.session.delete(pedido)
                db.session.commit()
                
                # Reabilitar foreign keys (SQLite)
                if is_sqlite:
                    db.session.execute(text('PRAGMA foreign_keys = ON'))
                
                print(f"[SUCCESS] Pedido #{pedido_id} deletado com sucesso (via objeto)")
                return success_response(message='Pedido deletado com sucesso')
                
            except Exception as fallback_error:
                db.session.rollback()
                # Reabilitar foreign keys antes de retornar erro (SQLite)
                if is_sqlite:
                    try:
                        db.session.execute(text('PRAGMA foreign_keys = ON'))
                    except:
                        pass
                    
                error_msg = str(fallback_error)
                error_type = type(fallback_error).__name__
                print(f"[ERRO] Falha ao deletar pedido #{pedido_id} (ambas abordagens falharam):")
                print(f"  - DELETE direto: {delete_error}")
                print(f"  - Via objeto: {error_type}: {error_msg}")
                import traceback
                traceback.print_exc()
                return error_response(
                    f'Falha ao deletar pedido do banco de dados: {error_msg}', 
                    500,
                    details={'error_type': error_type}
                )
                
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        print(f"[ERRO] Exceção inesperada ao deletar pedido #{pedido_id}: {error_type}: {error_msg}")
        import traceback
        traceback.print_exc()
        return error_response(f'Erro ao deletar pedido: {error_msg}', 500)


@pedidos_bp.route('/exportar-planilha', methods=['POST'])
@requires_edit_auth
def exportar_planilha():
    """
    Exporta vendas para Google Sheets
    CRÍTICO: Preservar esta funcionalidade exatamente como está
    """
    try:
        backend_dir = Path(__file__).parent.parent.parent
        script_path = backend_dir / 'scripts' / 'export' / 'exportar_vendas_sheets.py'
        
        if not script_path.exists():
            return error_response(
                'Script não encontrado',
                500,
                details={'path': str(script_path)}
            )
        
        # Importar e executar script (preservar lógica exata)
        import sys
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        
        spec = importlib.util.spec_from_file_location("exportar_vendas_sheets", str(script_path))
        if spec is None or spec.loader is None:
            return error_response('Erro ao carregar módulo', 500)
        
        module = importlib.util.module_from_spec(spec)
        module.__file__ = str(script_path)
        spec.loader.exec_module(module)
        
        # Nota: O script agora resolve credenciais automaticamente
        # via _resolve_credentials_path() em backend/user/config/ ou variável de ambiente
        
        if not hasattr(module, 'exportar_vendas'):
            return error_response('Função exportar_vendas não encontrada', 500)
        
        resultado = module.exportar_vendas()
        
        if resultado:
            return success_response(message='Planilha atualizada com sucesso!')
        else:
            return error_response(
                'Erro ao exportar. Verifique as credenciais do Google.',
                500
            )
            
    except FileNotFoundError as e:
        return error_response(
            'Credenciais do Google não configuradas',
            400,
            details={'error': str(e)}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(
            'Erro ao exportar planilha',
            500,
            details={'error': str(e)}
        )


@pedidos_bp.route('', methods=['POST'])
@requires_edit_auth
def criar_pedido():
    """
    Cria novo pedido via API (usado pelo PWA)
    CRÍTICO: Preservar toda a lógica existente de api.py
    """
    try:
        from app import db
        from app.models import Pedido, Cliente, FontePedido
        from datetime import datetime
        import re
        
        data = request.get_json()
        
        if not data:
            return error_response('Nenhum dado fornecido', 400)
        
        # Extração de dados (preservar lógica exata)
        cliente = data.get('cliente', '').strip()
        telefone_cliente = data.get('telefone_cliente', data.get('telefone', '')).strip()
        destinatario = data.get('destinatario', '').strip()
        tipo_pedido = data.get('tipo_pedido', 'Entrega')
        fonte_pedido_id = data.get('fonte_pedido_id')
        fonte_pedido = data.get('fonte_pedido', '').strip()
        
        produto = data.get('produto', '').strip()
        flores_cor = data.get('flores_cor', '').strip()
        valor = data.get('valor', '').strip()
        horario = data.get('horario', data.get('hora_entrega', '')).strip()
        dia_entrega_str = data.get('dia_entrega', data.get('data_entrega', '')).strip()
        
        cep = data.get('cep', '').strip()
        rua = data.get('rua', '').strip()
        numero = data.get('numero', '').strip()
        bairro = data.get('bairro', '').strip()
        cidade = data.get('cidade', '').strip()
        endereco = data.get('endereco', '').strip()
        obs_entrega = data.get('obs_entrega', '').strip()
        
        mensagem = data.get('mensagem', '').strip()
        pagamento = data.get('pagamento', '').strip()
        observacoes = data.get('observacoes', '').strip()
        status_pagamento = data.get('status_pagamento', '').strip()
        
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
            return error_response(
                f'Campos obrigatórios ausentes: {", ".join(campos_faltantes)}',
                400,
                details={'campos_enviados': list(data.keys())}
            )
        
        # Conversão de quantidade
        try:
            if isinstance(quantidade_raw, str):
                quantidade_raw = quantidade_raw.strip()
            quantidade = int(quantidade_raw) if quantidade_raw and str(quantidade_raw).strip() else 1
            if quantidade < 0:
                quantidade = 1
        except (ValueError, TypeError):
            quantidade = 1
        
        # Validação de horário: aceita HH:MM ou intervalo HH:MM - HH:MM
        pattern_simples = r'^([01]?\d|2[0-3]):[0-5]\d$'
        pattern_intervalo = r'^([01]?\d|2[0-3]):[0-5]\d\s*-\s*([01]?\d|2[0-3]):[0-5]\d$'
        
        if not (re.match(pattern_simples, horario) or re.match(pattern_intervalo, horario)):
            return error_response(
                'Formato de horário inválido',
                400,
                details={
                    'horario_recebido': horario,
                    'formato_esperado': 'HH:MM (ex: 14:30) ou intervalo HH:MM - HH:MM (ex: 08:00 - 10:00)'
                }
            )
        
        # Se for intervalo, validar que horário final é depois do inicial
        if ' - ' in horario:
            partes = horario.split(' - ')
            if len(partes) == 2:
                try:
                    h1, m1 = map(int, partes[0].strip().split(':'))
                    h2, m2 = map(int, partes[1].strip().split(':'))
                    minutos_inicial = h1 * 60 + m1
                    minutos_final = h2 * 60 + m2
                    if minutos_final <= minutos_inicial:
                        return error_response(
                            'O horário final deve ser depois do horário inicial',
                            400,
                            details={'horario_recebido': horario}
                        )
                except (ValueError, IndexError):
                    return error_response(
                        'Formato de intervalo inválido',
                        400,
                        details={'horario_recebido': horario}
                    )
        
        # Conversão de data
        try:
            if '/' in dia_entrega_str:
                dia_entrega = datetime.strptime(dia_entrega_str, '%d/%m/%Y').date()
            else:
                dia_entrega = datetime.strptime(dia_entrega_str, '%Y-%m-%d').date()
        except ValueError as e:
            return error_response(
                'Formato de data inválido',
                400,
                details={
                    'data_recebida': dia_entrega_str,
                    'formatos_aceitos': ['YYYY-MM-DD', 'DD/MM/YYYY'],
                    'detalhes': str(e)
                }
            )
        
        # Gerenciar cliente_id
        cliente_id = data.get('cliente_id', '').strip()
        if not cliente_id and cliente and telefone_cliente:
            cliente_existente = Cliente.buscar_por_telefone(telefone_cliente)
            if cliente_existente:
                cliente_id = cliente_existente.id
            else:
                try:
                    novo_cliente = Cliente(
                        nome=cliente,
                        telefone=telefone_cliente,
                        email=None,
                        observacoes=None
                    )
                    db.session.add(novo_cliente)
                    db.session.flush()
                    cliente_id = novo_cliente.id
                except Exception:
                    cliente_id = None
        
        cliente_id_int = int(cliente_id) if cliente_id else None
        
        # Processar fonte_pedido_id
        fonte_pedido_id_int = None
        if fonte_pedido_id:
            try:
                fonte_pedido_id_int = int(fonte_pedido_id)
            except (ValueError, TypeError):
                fonte_pedido_id_int = None
        elif fonte_pedido:
            fonte = FontePedido.query.filter_by(nome=fonte_pedido, ativo=True).first()
            if fonte:
                fonte_pedido_id_int = fonte.id
        
        # Criar pedido
        pedido = Pedido(
            cliente=cliente if cliente else None,
            telefone_cliente=telefone_cliente,
            destinatario=destinatario,
            tipo_pedido=tipo_pedido,
            fonte_pedido=fonte_pedido if fonte_pedido else None,
            fonte_pedido_id=fonte_pedido_id_int,
            produto=produto,
            flores_cor=flores_cor if flores_cor else None,
            valor=valor if valor else None,
            horario=horario,
            dia_entrega=dia_entrega,
            cep=cep if cep else None,
            rua=rua if rua else None,
            numero=numero if numero else None,
            bairro=bairro if bairro else None,
            cidade=cidade if cidade else None,
            endereco=endereco if endereco else None,
            obs_entrega=obs_entrega if obs_entrega else None,
            mensagem=mensagem if mensagem else None,
            pagamento=pagamento if pagamento else None,
            observacoes=observacoes if observacoes else None,
            status_pagamento=status_pagamento if status_pagamento else None,
            status='agendado',
            quantidade=quantidade,
            cliente_id=cliente_id_int
        )
        
        db.session.add(pedido)
        db.session.commit()
        
        # Inserir na tabela auxiliar da fonte (se houver)
        if fonte_pedido_id_int:
            try:
                from app.models.pedido_fonte import PedidoFonte
                PedidoFonte.adicionar_pedido(pedido.id, fonte_pedido_id_int, valor if valor else None)
            except Exception:
                pass  # Não falhar se houver erro
        
        return success_response(
            {'pedido_id': pedido.id, 'pedido': pedido.to_dict()},
            message='Pedido criado com sucesso',
            status_code=201
        )
        
    except Exception as e:
        from app import db
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return error_response(f'Erro ao criar pedido: {str(e)}', 500)


@pedidos_bp.route('/<int:pedido_id>', methods=['PUT'])
@requires_edit_auth
def atualizar_pedido(pedido_id):
    """
    Atualiza dados completos do pedido
    CRÍTICO: Preservar lógica de resetar distância quando endereço muda
    """
    try:
        from app import db
        from app.models import Pedido, FontePedido
        from datetime import datetime
        
        pedido = pedido_repo.get_by_id(pedido_id)
        if not pedido:
            return error_response('Pedido não encontrado', 404, details={'pedido_id': pedido_id})
        
        data = request.get_json() or {}
        
        # Atualizar campos (preservar lógica exata)
        if 'cliente' in data:
            pedido.cliente = data['cliente']
        if 'telefone_cliente' in data:
            pedido.telefone_cliente = data['telefone_cliente']
        if 'destinatario' in data:
            pedido.destinatario = data['destinatario']
        if 'tipo_pedido' in data:
            pedido.tipo_pedido = data['tipo_pedido']
        if 'fonte_pedido_id' in data:
            try:
                pedido.fonte_pedido_id = int(data['fonte_pedido_id']) if data['fonte_pedido_id'] else None
            except (ValueError, TypeError):
                pedido.fonte_pedido_id = None
        elif 'fonte_pedido' in data:
            fonte = FontePedido.query.filter_by(nome=data['fonte_pedido'], ativo=True).first()
            if fonte:
                pedido.fonte_pedido_id = fonte.id
            pedido.fonte_pedido = data['fonte_pedido']
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
        
        # Verificar se endereço mudou (resetar distância)
        endereco_mudou = False
        campos_endereco = ['cep', 'rua', 'numero', 'bairro', 'cidade', 'endereco']
        for campo in campos_endereco:
            if campo in data and data[campo] != getattr(pedido, campo):
                setattr(pedido, campo, data[campo])
                endereco_mudou = True
        
        if endereco_mudou:
            pedido.distancia_km = None
        
        if 'obs_entrega' in data:
            pedido.obs_entrega = data['obs_entrega']
        if 'mensagem' in data:
            pedido.mensagem = data['mensagem']
        if 'pagamento' in data:
            pedido.pagamento = data['pagamento']
        if 'observacoes' in data:
            pedido.observacoes = data['observacoes']
        if 'status_pagamento' in data:
            pedido.status_pagamento = data['status_pagamento']
        if 'status' in data:
            pedido.status = data['status']
        
        pedido.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return success_response(
            {'pedido': pedido.to_dict()},
            message='Pedido atualizado com sucesso'
        )
        
    except Exception as e:
        from app import db
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return error_response(f'Erro ao atualizar pedido: {str(e)}', 500)


@pedidos_bp.route('/por-data', methods=['GET'])
def get_pedidos_por_data():
    """Retorna contagem de pedidos por horário para uma data específica"""
    try:
        from app.models import Pedido
        from datetime import datetime
        
        data_str = request.args.get('data')
        if not data_str:
            return error_response(
                'Parâmetro "data" é obrigatório',
                400,
                details={'formato_esperado': 'YYYY-MM-DD (ex: 2025-12-20)'}
            )
        
        # Converter data
        try:
            if '/' in data_str:
                partes = data_str.split('/')
                if len(partes) == 3:
                    dia, mes, ano = partes
                    data_entrega = datetime.strptime(f'{ano}-{mes}-{dia}', '%Y-%m-%d').date()
                else:
                    return error_response('Formato de data inválido', 400)
            else:
                data_entrega = datetime.strptime(data_str, '%Y-%m-%d').date()
        except ValueError as e:
            return error_response(
                'Formato de data inválido',
                400,
                details={
                    'detalhes': str(e),
                    'formato_esperado': 'YYYY-MM-DD ou DD/MM/YYYY'
                }
            )
        
        # Buscar pedidos do dia
        pedidos = pedido_repo.buscar_por_data(data_entrega, data_entrega, excluir_ocultos=True)
        
        # Agrupar por horário
        horarios = {}
        for pedido in pedidos:
            horario = pedido.horario.strip() if pedido.horario else ''
            if horario:
                horarios[horario] = horarios.get(horario, 0) + 1
        
        return success_response({
            'data': data_str,
            'data_formatada': data_entrega.strftime('%Y-%m-%d'),
            'total_pedidos': len(pedidos),
            'horarios': horarios
        })
        
    except Exception as e:
        return error_response(f'Erro ao buscar pedidos por data: {str(e)}', 500)


@pedidos_bp.route('/<int:pedido_id>/marcar-impresso', methods=['POST', 'PUT', 'OPTIONS'])
@requires_edit_auth
def marcar_impresso(pedido_id):
    """Marca pedido como impresso"""
    try:
        from app import db
        from datetime import datetime
        
        pedido = pedido_repo.get_by_id(pedido_id)
        if not pedido:
            return error_response('Pedido não encontrado', 404)
        
        pedido.impresso = True
        pedido.updated_at = datetime.utcnow()
        db.session.commit()
        
        return success_response(
            {'pedido': pedido.to_dict()},
            message='Pedido marcado como impresso'
        )
        
    except Exception as e:
        from app import db
        db.session.rollback()
        return error_response(f'Erro ao marcar como impresso: {str(e)}', 500)

