# -*- coding: utf-8 -*-
"""
Testes do serviço de Taxa de Cartão e do impacto na base de comissão.

Cobre:
- calcular_taxa para débito, crédito à vista e parcelado
- fallback para parcelas acima da maior faixa configurada
- formas de pagamento sem taxa (Pix, Dinheiro, em branco)
- commission_base descontando taxa_cartao (entrega + retirada)
- snapshot via aplicar_taxa_cartao_snapshot
"""
import os

os.environ.setdefault("BCRYPT_LOG_ROUNDS", "4")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-taxa-cartao")

import json  # noqa: E402
import tempfile  # noqa: E402
from datetime import date  # noqa: E402

import pytest  # noqa: E402

from app.services.commission_service import commission_base  # noqa: E402
from app.services.taxa_cartao import (  # noqa: E402
    TaxaCartaoService,
    aplicar_taxa_cartao_snapshot,
    taxa_cartao_service,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def service_factory():
    """Fabrica TaxaCartaoService com config JSON temporário."""
    tmp_files = []

    def make(config: dict) -> TaxaCartaoService:
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f)
        tmp_files.append(path)
        return TaxaCartaoService(config_path=path)

    yield make

    for p in tmp_files:
        try:
            os.unlink(p)
        except OSError:
            pass


def make_pedido(
    valor: str = "R$ 100,00",
    tipo_pedido: str = "Entrega",
    taxa_entrega: float = 0.0,
    pagamento: str | None = None,
    parcelas_cartao: int | None = None,
    taxa_cartao_valor: float = 0.0,
):
    """Cria um objeto Pedido transiente (sem persistir) para testar lógica pura."""
    from app.models.pedido import Pedido

    return Pedido(
        cliente="C",
        telefone_cliente="11999999999",
        destinatario="D",
        produto="P",
        valor=valor,
        dia_entrega=date(2025, 2, 10),
        horario="10:00",
        tipo_pedido=tipo_pedido,
        taxa_entrega=taxa_entrega,
        pagamento=pagamento,
        parcelas_cartao=parcelas_cartao,
        taxa_cartao_valor=taxa_cartao_valor,
    )


# ---------------------------------------------------------------------------
# Cálculo da taxa
# ---------------------------------------------------------------------------


class TestCalcularTaxa:
    def test_debito_aplica_percentual(self, service_factory):
        svc = service_factory({"debito_pct": 2.0, "credito": [{"parcelas": 1, "taxa_pct": 3.5}]})
        assert svc.calcular_taxa("Cartão de Débito", None, 100.0) == 2.0

    def test_credito_avista_usa_faixa_1(self, service_factory):
        svc = service_factory(
            {
                "debito_pct": 0,
                "credito": [
                    {"parcelas": 1, "taxa_pct": 3.0},
                    {"parcelas": 3, "taxa_pct": 5.0},
                ],
            }
        )
        assert svc.calcular_taxa("Cartão de Crédito", 1, 200.0) == 6.0

    def test_credito_parcelado_usa_faixa_correta(self, service_factory):
        svc = service_factory(
            {
                "debito_pct": 0,
                "credito": [
                    {"parcelas": 1, "taxa_pct": 3.0},
                    {"parcelas": 3, "taxa_pct": 5.0},
                ],
            }
        )
        # 3x em R$ 200 → 5% = R$ 10,00
        assert svc.calcular_taxa("Cartão de Crédito", 3, 200.0) == 10.0

    def test_parcelas_acima_do_maximo_usa_ultima_faixa(self, service_factory):
        svc = service_factory(
            {
                "debito_pct": 0,
                "credito": [
                    {"parcelas": 1, "taxa_pct": 3.0},
                    {"parcelas": 6, "taxa_pct": 7.0},
                ],
            }
        )
        # 12x não configurado → cai na maior faixa (6 parcelas, 7%)
        assert svc.calcular_taxa("Cartão de Crédito", 12, 100.0) == 7.0

    def test_pix_dinheiro_outros_retornam_zero(self, service_factory):
        svc = service_factory({"debito_pct": 2.0, "credito": [{"parcelas": 1, "taxa_pct": 3.0}]})
        assert svc.calcular_taxa("Pix", None, 100.0) == 0.0
        assert svc.calcular_taxa("Dinheiro", None, 100.0) == 0.0
        assert svc.calcular_taxa("Boleto", None, 100.0) == 0.0
        assert svc.calcular_taxa(None, None, 100.0) == 0.0
        assert svc.calcular_taxa("", None, 100.0) == 0.0

    def test_valor_zero_retorna_zero(self, service_factory):
        svc = service_factory({"debito_pct": 2.0, "credito": [{"parcelas": 1, "taxa_pct": 3.0}]})
        assert svc.calcular_taxa("Cartão de Débito", None, 0.0) == 0.0

    def test_parcelas_invalidas_caem_para_avista(self, service_factory):
        svc = service_factory(
            {
                "debito_pct": 0,
                "credito": [{"parcelas": 1, "taxa_pct": 3.0}],
            }
        )
        # None → 1 parcela
        assert svc.calcular_taxa("Cartão de Crédito", None, 100.0) == 3.0
        # 0 → 1 parcela
        assert svc.calcular_taxa("Cartão de Crédito", 0, 100.0) == 3.0
        # string inválida → 1 parcela
        assert svc.calcular_taxa("Cartão de Crédito", "abc", 100.0) == 3.0


# ---------------------------------------------------------------------------
# Snapshot + commission_base
# ---------------------------------------------------------------------------


class TestSnapshotECommissionBase:
    def test_aplicar_snapshot_grava_taxa_no_pedido(self, app, monkeypatch, service_factory):
        svc = service_factory({"debito_pct": 2.5, "credito": [{"parcelas": 1, "taxa_pct": 3.0}]})
        # Substituir instância global usada pelo helper
        monkeypatch.setattr("app.services.taxa_cartao.taxa_cartao_service", svc, raising=True)
        pedido = make_pedido(valor="R$ 100,00", pagamento="Cartão de Débito", parcelas_cartao=None)
        taxa = aplicar_taxa_cartao_snapshot(pedido)
        assert taxa == 2.5
        assert pedido.taxa_cartao_valor == 2.5

    def test_commission_base_entrega_desconta_entrega_e_cartao(self, app):
        pedido = make_pedido(
            valor="R$ 100,00",
            tipo_pedido="Entrega",
            taxa_entrega=10.0,
            taxa_cartao_valor=3.0,
        )
        with app.app_context():
            base = commission_base(pedido)
        # 100 − 10 − 3 = 87
        assert base == pytest.approx(87.0, abs=0.01)

    def test_commission_base_retirada_desconta_apenas_cartao(self, app):
        pedido = make_pedido(
            valor="R$ 100,00",
            tipo_pedido="Retirada",
            taxa_entrega=10.0,  # irrelevante em retirada
            taxa_cartao_valor=5.0,
        )
        with app.app_context():
            base = commission_base(pedido)
        # Retirada não conta taxa_entrega: 100 − 5 = 95
        assert base == pytest.approx(95.0, abs=0.01)

    def test_commission_base_pix_sem_cartao_desconta_so_entrega(self, app):
        pedido = make_pedido(
            valor="R$ 100,00",
            tipo_pedido="Entrega",
            taxa_entrega=10.0,
            pagamento="Pix",
            taxa_cartao_valor=0.0,
        )
        with app.app_context():
            base = commission_base(pedido)
        assert base == pytest.approx(90.0, abs=0.01)

    def test_commission_base_nunca_negativa(self, app):
        pedido = make_pedido(
            valor="R$ 10,00",
            tipo_pedido="Entrega",
            taxa_entrega=20.0,  # maior que o valor
            taxa_cartao_valor=5.0,
        )
        with app.app_context():
            base = commission_base(pedido)
        assert base == 0.0


# ---------------------------------------------------------------------------
# Configuração default e segurança
# ---------------------------------------------------------------------------


class TestConfigPadrao:
    def test_service_global_carrega_sem_erro(self):
        # A instância global pode existir mesmo com arquivo ausente
        assert taxa_cartao_service.config is not None
        assert "debito_pct" in taxa_cartao_service.config
        assert "credito" in taxa_cartao_service.config

    def test_arquivo_ausente_usa_default(self):
        svc = TaxaCartaoService(config_path="/caminho/que/nao/existe.json")
        assert svc.config["debito_pct"] == 0
        assert len(svc.config["credito"]) == 12  # 1..12
