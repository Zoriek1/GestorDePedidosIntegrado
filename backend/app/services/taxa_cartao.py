# -*- coding: utf-8 -*-
"""
Servico de Calculo de Taxa de Cartao

Calcula a taxa do adquirente (debito/credito) a partir de:
- forma de pagamento (string "Cartao de Debito" / "Cartao de Credito")
- numero de parcelas (apenas para credito)
- valor bruto do pedido

Configuracao lida de StoreSetting (multi-tenant) com fallback para
backend/config/taxa_cartao.json.
"""
import json
import os
from typing import Dict, List, Optional

from flask import current_app

CREDITO_LABEL = "Cartão de Crédito"
DEBITO_LABEL = "Cartão de Débito"


class TaxaCartaoService:
    """Servico para calculo de taxa de cartao (debito/credito com parcelas)."""

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

    def load_from_store(self, store_ref_id: Optional[int] = None) -> Dict:
        """Carrega configuracao de taxa de cartao do StoreSetting (multi-tenant).

        Se nao houver dados no banco, faz fallback para o arquivo JSON.
        """
        try:
            from app.models.store_setting import StoreSetting

            if store_ref_id is None:
                from app.services.integration_settings_service import default_store

                store_ref_id = default_store().id

            settings = StoreSetting.query.filter_by(store_ref_id=store_ref_id).first()
            if settings:
                debito_pct = getattr(settings, "taxa_cartao_debito_pct", 0) or 0
                credito_json = getattr(settings, "taxa_cartao_credito_json", None)
                if credito_json:
                    try:
                        credito = json.loads(credito_json)
                    except (json.JSONDecodeError, TypeError):
                        credito = self._config_padrao()["credito"]
                else:
                    credito = self._config_padrao()["credito"]
                return {"debito_pct": float(debito_pct), "credito": credito}
        except Exception:
            pass

        # Fallback: arquivo JSON
        return self._carregar_config()

    def save_to_store(self, config: Dict, store_ref_id: Optional[int] = None) -> None:
        """Salva configuracao de taxa de cartao no StoreSetting.

        Tambem atualiza o arquivo JSON para compatibilidade.
        """
        from app import db
        from app.models.store_setting import StoreSetting

        if store_ref_id is None:
            from app.services.integration_settings_service import default_store

            store_ref_id = default_store().id

        settings = StoreSetting.query.filter_by(store_ref_id=store_ref_id).first()
        if not settings:
            settings = StoreSetting(store_ref_id=store_ref_id)
            db.session.add(settings)

        settings.taxa_cartao_debito_pct = float(config.get("debito_pct", 0))
        settings.taxa_cartao_credito_json = json.dumps(
            config.get("credito", []), ensure_ascii=False
        )
        db.session.commit()

        # Tambem salva no arquivo JSON para compatibilidade
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

        # Atualiza cache em memoria
        self.config = config

    def _faixas_credito(self, config: Optional[Dict] = None) -> List[Dict]:
        cfg = config or self.config
        faixas = cfg.get("credito") or []
        return sorted(faixas, key=lambda f: int(f.get("parcelas", 0)))

    def max_parcelas(self, config: Optional[Dict] = None) -> int:
        faixas = self._faixas_credito(config)
        return int(faixas[-1]["parcelas"]) if faixas else 1

    def calcular_taxa(
        self,
        forma_pagamento: Optional[str],
        parcelas: Optional[int],
        valor: float,
        config: Optional[Dict] = None,
    ) -> float:
        """Retorna o valor da taxa (R$) para a forma de pagamento.

        Formas sem taxa configurada (Pix, Dinheiro, etc.) retornam 0.
        """
        if not forma_pagamento or not valor or valor <= 0:
            return 0.0

        cfg = config or self.config
        forma = forma_pagamento.strip()

        if forma == DEBITO_LABEL:
            pct = float(cfg.get("debito_pct") or 0)
            return round(valor * pct / 100, 2)

        if forma == CREDITO_LABEL:
            faixas = self._faixas_credito(cfg)
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
                # Acima do maximo: usar a maior faixa configurada
                faixa = faixas[-1]
            pct = float(faixa.get("taxa_pct") or 0)
            return round(valor * pct / 100, 2)

        return 0.0


taxa_cartao_service = TaxaCartaoService()


def aplicar_taxa_cartao_snapshot(pedido, store_ref_id: Optional[int] = None) -> float:
    """Recalcula e grava `pedido.taxa_cartao_valor` com base na config atual.

    Deve ser chamado antes de `apply_commission_lifecycle` em qualquer rota
    que crie/atualize um pedido. Retorna o valor da taxa aplicada.
    """
    from app.utils.money import parse_brl_money

    # Tenta carregar do banco (multi-tenant); se falhar, usa o config em memoria
    try:
        config = taxa_cartao_service.load_from_store(store_ref_id)
    except Exception:
        config = taxa_cartao_service.config

    valor_float = parse_brl_money(pedido.valor) if getattr(pedido, "valor", None) else 0.0
    taxa = taxa_cartao_service.calcular_taxa(
        getattr(pedido, "pagamento", None),
        getattr(pedido, "parcelas_cartao", None),
        valor_float,
        config=config,
    )
    pedido.taxa_cartao_valor = taxa
    return taxa
