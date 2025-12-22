# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models import Cliente, Pedido
from app.services.pedidos_service import PedidosService


class PedidosServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            }
        )
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_campos_obrigatorios(self):
        payload, status_code = PedidosService.criar_pedido({"cliente": "Ana"})

        self.assertEqual(status_code, 400)
        self.assertIn("Campos obrigatórios ausentes", payload.get("error", ""))
        self.assertEqual(payload.get("campos_enviados"), ["cliente"])

    def test_horario_invalido(self):
        payload, status_code = PedidosService.criar_pedido(
            {
                "telefone_cliente": "119999999",
                "destinatario": "João",
                "produto": "Buquê",
                "horario": "25:99",
                "dia_entrega": "2024-12-01",
            }
        )

        self.assertEqual(status_code, 400)
        self.assertEqual(payload.get("error"), "Formato de horário inválido")
        self.assertEqual(payload.get("formato_esperado"), "HH:MM (ex: 14:30)")

    def test_data_invalida(self):
        payload, status_code = PedidosService.criar_pedido(
            {
                "telefone_cliente": "119999999",
                "destinatario": "João",
                "produto": "Buquê",
                "horario": "10:30",
                "dia_entrega": "2024-13-40",
            }
        )

        self.assertEqual(status_code, 400)
        self.assertEqual(payload.get("error"), "Formato de data inválido")

    def test_cria_cliente_automaticamente(self):
        payload, status_code = PedidosService.criar_pedido(
            {
                "cliente": "Maria",
                "telefone_cliente": "11911112222",
                "destinatario": "Carlos",
                "produto": "Arranjo",
                "horario": "14:30",
                "dia_entrega": "2024-12-01",
            }
        )

        self.assertEqual(status_code, 201)
        self.assertTrue(payload.get("success"))
        self.assertEqual(Cliente.query.count(), 1)
        self.assertEqual(Pedido.query.count(), 1)


if __name__ == "__main__":
    unittest.main()
