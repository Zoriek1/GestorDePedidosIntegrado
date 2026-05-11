# -*- coding: utf-8 -*-
"""
Serviço de Cálculo de Taxa de Cartão

Calcula a taxa do adquirente (débito/crédito) a partir de:
- forma de pagamento (string "Cartão de Débito" / "Cartão de Crédito")
- número de parcelas (apenas para crédito)
- valor bruto do pedido

Configuração lida de backend/config/taxa_cartao.json (mesma convenção
do taxa_entrega).
"""
import json
import os
from typing import Dict, List, Optional

CREDITO_LABEL = "Cartão de Crédito"
DEBITO_LABEL = "Cartão de Débito"


class TaxaCartaoService:
    """Serviço para cálculo de taxa de cartão (débito/crédito com parcelas)."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            config_path = os.path.join(base_dir, "config", "taxa_cartao.json")

        self.config_path = config_path
        self.config = self._carregar_config()

    def _config_padrao(self) -> Dict:
        return {
            "debito_pct": 0,
            "credito": [{"parcelas": n, "taxa_pct": 0} for n in range(1, 13)],
        }

    def _carregar_config(self) -> Dict:
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f) or self._config_padrao()
            return self._config_padrao()
        except Exception:
            return self._config_padrao()

    def recarregar(self) -> None:
        self.config = self._carregar_config()

    def _faixas_credito(self) -> List[Dict]:
        faixas = self.config.get("credito") or []
        return sorted(faixas, key=lambda f: int(f.get("parcelas", 0)))

    def max_parcelas(self) -> int:
        faixas = self._faixas_credito()
        return int(faixas[-1]["parcelas"]) if faixas else 1

    def calcular_taxa(
        self,
        forma_pagamento: Optional[str],
        parcelas: Optional[int],
        valor: float,
    ) -> float:
        """Retorna o valor da taxa (R$) para a forma de pagamento.

        Formas sem taxa configurada (Pix, Dinheiro, etc.) retornam 0.
        """
        if not forma_pagamento or not valor or valor <= 0:
            return 0.0

        forma = forma_pagamento.strip()

        if forma == DEBITO_LABEL:
            pct = float(self.config.get("debito_pct") or 0)
            return round(valor * pct / 100, 2)

        if forma == CREDITO_LABEL:
            faixas = self._faixas_credito()
            if not faixas:
                return 0.0
            try:
                n = int(parcelas) if parcelas else 1
            except (TypeError, ValueError):
                n = 1
            n = max(1, n)
            # Faixa exata ou fallback para a maior parcela configurada
            faixa = next((f for f in faixas if int(f.get("parcelas", 0)) == n), None)
            if faixa is None:
                # Acima do máximo: usar a maior faixa configurada
                faixa = faixas[-1]
            pct = float(faixa.get("taxa_pct") or 0)
            return round(valor * pct / 100, 2)

        return 0.0


taxa_cartao_service = TaxaCartaoService()


def aplicar_taxa_cartao_snapshot(pedido) -> float:
    """Recalcula e grava `pedido.taxa_cartao_valor` com base na config atual.

    Deve ser chamado antes de `apply_commission_lifecycle` em qualquer rota
    que crie/atualize um pedido. Retorna o valor da taxa aplicada.
    """
    from app.utils.money import parse_brl_money

    valor_float = parse_brl_money(pedido.valor) if getattr(pedido, "valor", None) else 0.0
    taxa = taxa_cartao_service.calcular_taxa(
        getattr(pedido, "pagamento", None),
        getattr(pedido, "parcelas_cartao", None),
        valor_float,
    )
    pedido.taxa_cartao_valor = taxa
    return taxa
