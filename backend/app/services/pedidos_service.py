# -*- coding: utf-8 -*-
"""Serviço de domínio para operações de pedidos."""
from datetime import datetime
import re
from typing import Any, Dict, Tuple

from app import db
from app.models import Cliente, FontePedido, Pedido
from app.schemas.pedidos import PedidoCreateSchema, PedidoUpdateSchema


class PedidosService:
    """Serviços de criação e atualização de pedidos."""

    @staticmethod
    def criar_pedido(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """Cria um novo pedido com validações compatíveis com a API atual."""
        try:
            if not data:
                return {"error": "Nenhum dado fornecido"}, 400

            payload = PedidoCreateSchema.model_validate(data)

            cliente = payload.cliente or ""
            telefone_cliente = payload.telefone_cliente or ""
            destinatario = payload.destinatario or ""
            tipo_pedido = payload.tipo_pedido or "Entrega"
            fonte_pedido_id = payload.fonte_pedido_id
            fonte_pedido = payload.fonte_pedido or ""

            produto = payload.produto or ""
            flores_cor = payload.flores_cor or ""
            valor = payload.valor or ""
            horario = payload.horario or ""
            dia_entrega_str = payload.dia_entrega or ""

            cep = payload.cep or ""
            rua = payload.rua or ""
            numero = payload.numero or ""
            bairro = payload.bairro or ""
            cidade = payload.cidade or ""
            endereco = payload.endereco or ""
            obs_entrega = payload.obs_entrega or ""

            mensagem = payload.mensagem or ""
            pagamento = payload.pagamento or ""
            observacoes = payload.observacoes or ""
            status_pagamento = payload.status_pagamento or ""

            quantidade_raw = payload.quantidade

            campos_obrigatorios = {
                "telefone_cliente": telefone_cliente,
                "destinatario": destinatario,
                "produto": produto,
                "horario": horario,
                "dia_entrega": dia_entrega_str,
            }

            campos_faltantes = [
                campo for campo, valor in campos_obrigatorios.items() if not valor
            ]
            if campos_faltantes:
                return {
                    "error": f'Campos obrigatórios ausentes: {", ".join(campos_faltantes)}',
                    "campos_enviados": list(data.keys()),
                }, 400

            try:
                if isinstance(quantidade_raw, str):
                    quantidade_raw = quantidade_raw.strip()
                quantidade = (
                    int(quantidade_raw)
                    if quantidade_raw and str(quantidade_raw).strip()
                    else 1
                )
                if quantidade < 0:
                    quantidade = 1
            except (ValueError, TypeError):
                quantidade = 1

            if not re.match(r"^([01]?\d|2[0-3]):[0-5]\d$", horario):
                return {
                    "error": "Formato de horário inválido",
                    "horario_recebido": horario,
                    "formato_esperado": "HH:MM (ex: 14:30)",
                }, 400

            try:
                if "/" in dia_entrega_str:
                    dia_entrega = datetime.strptime(dia_entrega_str, "%d/%m/%Y").date()
                else:
                    dia_entrega = datetime.strptime(dia_entrega_str, "%Y-%m-%d").date()
            except ValueError as exc:
                return {
                    "error": "Formato de data inválido",
                    "data_recebida": dia_entrega_str,
                    "formatos_aceitos": ["YYYY-MM-DD", "DD/MM/YYYY"],
                    "detalhes": str(exc),
                }, 400

            cliente_id = payload.cliente_id
            if isinstance(cliente_id, str):
                cliente_id = cliente_id.strip()
            elif cliente_id is not None:
                cliente_id = str(cliente_id).strip()

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
                            observacoes=None,
                        )
                        db.session.add(novo_cliente)
                        db.session.flush()
                        cliente_id = novo_cliente.id
                        print(
                            f"[INFO] Novo cliente criado: ID={cliente_id}, Nome={cliente}, Telefone={telefone_cliente}"
                        )
                    except Exception as exc:
                        print(f"[ERRO] Erro ao criar cliente: {exc}")
                        cliente_id = None

            cliente_id_int = int(cliente_id) if cliente_id else None

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

            print(
                "[DEBUG] Criando pedido - fonte_pedido_id:"
                f" {fonte_pedido_id_int}, fonte_pedido (legacy): '{fonte_pedido}', pagamento: '{pagamento}'"
            )
            print(f"[DEBUG] Dados recebidos: {list(data.keys())}")

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
                status="agendado",
                quantidade=quantidade,
                cliente_id=cliente_id_int,
            )

            db.session.add(pedido)
            db.session.commit()

            print(
                f"[DEBUG] Pedido #{pedido.id} criado - fonte_pedido salvo: '{pedido.fonte_pedido}', pagamento salvo: '{pedido.pagamento}'"
            )

            if fonte_pedido_id_int:
                try:
                    from app.models.pedido_fonte import PedidoFonte

                    resultado_fonte = PedidoFonte.adicionar_pedido(
                        pedido.id, fonte_pedido_id_int, valor if valor else None
                    )
                    if resultado_fonte:
                        print(
                            f"[DEBUG] Pedido #{pedido.id} inserido na tabela da fonte: {resultado_fonte.get('tabela')}, número sequencial: {resultado_fonte.get('numero_sequencial')}"
                        )
                    else:
                        print(
                            f"[WARN] Não foi possível inserir pedido #{pedido.id} na tabela da fonte (fonte_id: {fonte_pedido_id_int})"
                        )
                except Exception as exc:
                    print(f"[ERRO] Erro ao inserir pedido na tabela da fonte: {exc}")

            return {
                "success": True,
                "pedido_id": pedido.id,
                "message": "Pedido criado com sucesso",
                "pedido": pedido.to_dict(),
            }, 201

        except Exception as exc:
            db.session.rollback()
            return {"error": "Erro interno do servidor", "detalhes": str(exc)}, 500

    @staticmethod
    def atualizar_pedido(pedido_id: int, data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """Atualiza um pedido existente mantendo compatibilidade com a API."""
        try:
            pedido = Pedido.query.get(pedido_id)

            if not pedido:
                return {"error": "Pedido não encontrado", "pedido_id": pedido_id}, 404

            payload = PedidoUpdateSchema.model_validate(data or {})

            if payload.cliente is not None:
                pedido.cliente = payload.cliente
            if payload.telefone_cliente is not None:
                pedido.telefone_cliente = payload.telefone_cliente
            if payload.destinatario is not None:
                pedido.destinatario = payload.destinatario
            if payload.tipo_pedido is not None:
                pedido.tipo_pedido = payload.tipo_pedido
            if payload.fonte_pedido_id is not None:
                try:
                    pedido.fonte_pedido_id = (
                        int(payload.fonte_pedido_id)
                        if payload.fonte_pedido_id
                        else None
                    )
                except (ValueError, TypeError):
                    pedido.fonte_pedido_id = None
            elif payload.fonte_pedido is not None:
                fonte = FontePedido.query.filter_by(
                    nome=payload.fonte_pedido, ativo=True
                ).first()
                if fonte:
                    pedido.fonte_pedido_id = fonte.id
                pedido.fonte_pedido = payload.fonte_pedido
            if payload.produto is not None:
                pedido.produto = payload.produto
            if payload.flores_cor is not None:
                pedido.flores_cor = payload.flores_cor
            if payload.valor is not None:
                pedido.valor = payload.valor
            if payload.horario is not None:
                pedido.horario = payload.horario
            if payload.dia_entrega is not None:
                if "/" in payload.dia_entrega:
                    pedido.dia_entrega = datetime.strptime(
                        payload.dia_entrega, "%d/%m/%Y"
                    ).date()
                else:
                    pedido.dia_entrega = datetime.strptime(
                        payload.dia_entrega, "%Y-%m-%d"
                    ).date()

            endereco_mudou = False
            if payload.cep is not None and payload.cep != pedido.cep:
                pedido.cep = payload.cep
                endereco_mudou = True
            if payload.rua is not None and payload.rua != pedido.rua:
                pedido.rua = payload.rua
                endereco_mudou = True
            if payload.numero is not None and payload.numero != pedido.numero:
                pedido.numero = payload.numero
                endereco_mudou = True
            if payload.bairro is not None and payload.bairro != pedido.bairro:
                pedido.bairro = payload.bairro
                endereco_mudou = True
            if payload.cidade is not None and payload.cidade != pedido.cidade:
                pedido.cidade = payload.cidade
                endereco_mudou = True
            if payload.endereco is not None and payload.endereco != pedido.endereco:
                pedido.endereco = payload.endereco
                endereco_mudou = True
            if payload.obs_entrega is not None:
                pedido.obs_entrega = payload.obs_entrega
            if payload.mensagem is not None:
                pedido.mensagem = payload.mensagem
            if payload.pagamento is not None:
                pedido.pagamento = payload.pagamento
            if payload.observacoes is not None:
                pedido.observacoes = payload.observacoes
            if payload.status_pagamento is not None:
                pedido.status_pagamento = payload.status_pagamento
            if payload.status is not None:
                pedido.status = payload.status
            if payload.quantidade is not None:
                try:
                    quantidade_val = int(payload.quantidade)
                    pedido.quantidade = quantidade_val if quantidade_val > 0 else 1
                except (ValueError, TypeError):
                    pedido.quantidade = 1

            if endereco_mudou:
                pedido.distancia_km = None
                print(
                    f"[DEBUG] Endereço do pedido {pedido_id} alterado - distância resetada"
                )

            pedido.updated_at = datetime.utcnow()

            db.session.commit()

            return {
                "success": True,
                "message": "Pedido atualizado com sucesso",
                "pedido": pedido.to_dict(),
            }, 200

        except Exception as exc:
            db.session.rollback()
            return {"error": "Erro ao atualizar pedido", "detalhes": str(exc)}, 500
