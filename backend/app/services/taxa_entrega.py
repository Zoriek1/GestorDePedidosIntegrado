# -*- coding: utf-8 -*-
"""
Serviço de Cálculo de Taxa de Entrega
Calcula taxa de entrega baseada em distância com configuração customizável
"""
import json
import os
from typing import Dict, Optional


class TaxaEntregaService:
    """Serviço para cálculo de taxa de entrega baseada em distância"""

    DEBUG = True

    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa o serviço de taxa de entrega

        Args:
            config_path: Caminho para arquivo de configuração JSON
        """
        if config_path is None:
            # Caminho padrão relativo ao backend
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            config_path = os.path.join(base_dir, 'config', 'taxa_entrega.json')

        self.config_path = config_path
        self.config = self._carregar_config()

        if self.DEBUG:
            print("[DEBUG] TaxaEntregaService inicializado")
            print(f"[DEBUG] Tipo de cálculo: {self.config.get('tipo', 'desconhecido')}")

    def _carregar_config(self) -> Dict:
        """Carrega configuração do arquivo JSON"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config
            else:
                print(f"[AVISO] Arquivo de configuração não encontrado: {self.config_path}")
                print("[INFO] Usando configuração padrão")
                return self._config_padrao()
        except Exception as e:
            print(f"[ERRO] Erro ao carregar configuração: {e}")
            return self._config_padrao()

    def _config_padrao(self) -> Dict:
        """Retorna configuração padrão caso o arquivo não exista"""
        return {
            "tipo": "faixas",
            "faixas": [
                {"ate_km": 5, "taxa": 10.00},
                {"ate_km": 10, "taxa": 15.00},
                {"ate_km": 20, "taxa": 20.00},
                {"ate_km": None, "taxa": 30.00}
            ],
            "taxa_minima": 5.00,
            "taxa_maxima": 50.00
        }

    def calcular_taxa(self, distancia_km: float, config: Optional[Dict] = None) -> float:
        """
        Calcula taxa de entrega baseada em distância

        Args:
            distancia_km: Distância em quilômetros
            config: Configuração customizada (opcional, usa self.config se não fornecido)

        Returns:
            Taxa de entrega em reais (float)
        """
        if distancia_km is None or distancia_km < 0:
            if self.DEBUG:
                print(f"[AVISO] Distância inválida: {distancia_km}")
            return 0.0

        config_usar = config or self.config
        tipo = config_usar.get('tipo', 'faixas')

        if self.DEBUG:
            print("\n[DEBUG] --- Calculando Taxa de Entrega ---")
            print(f"[DEBUG] Distância: {distancia_km} km")
            print(f"[DEBUG] Tipo: {tipo}")

        if tipo == "faixas":
            taxa = self._calcular_por_faixas(distancia_km, config_usar)
        elif tipo == "por_km":
            taxa = self._calcular_por_km(distancia_km, config_usar)
        else:
            print(f"[ERRO] Tipo de cálculo desconhecido: {tipo}")
            taxa = 0.0

        # Aplicar limites mínimo e máximo
        taxa_minima = config_usar.get('taxa_minima', 0)
        taxa_maxima = config_usar.get('taxa_maxima', float('inf'))

        taxa = max(taxa_minima, min(taxa, taxa_maxima))

        if self.DEBUG:
            print(f"[DEBUG] Taxa calculada: R$ {taxa:.2f}")

        return round(taxa, 2)

    def _calcular_por_faixas(self, distancia_km: float, config: Dict) -> float:
        """
        Calcula taxa usando sistema de faixas

        Args:
            distancia_km: Distância em km
            config: Configuração com faixas

        Returns:
            Taxa calculada
        """
        faixas = config.get('faixas', [])

        # Verificar se as faixas usam formato novo (de_km/ate_km) ou antigo (ate_km)
        usa_faixas_intervalo = any('de_km' in faixa for faixa in faixas)

        if usa_faixas_intervalo:
            # Novo formato: faixas com de_km e ate_km (intervalos específicos)
            # Se a distância está entre faixas, usar a próxima faixa (maior)

            for i, faixa in enumerate(faixas):
                de_km = faixa.get('de_km', 0)
                ate_km = faixa.get('ate_km')
                taxa = faixa.get('taxa', 0)

                if ate_km is None:
                    # Faixa sem limite superior (acima de de_km)
                    if distancia_km >= de_km:
                        if self.DEBUG:
                            print(f"[DEBUG] Faixa encontrada: {de_km}+ km -> R$ {taxa:.2f}")
                        return taxa
                else:
                    # Faixa com intervalo definido
                    if de_km <= distancia_km <= ate_km:
                        if self.DEBUG:
                            print(f"[DEBUG] Faixa encontrada: {de_km}-{ate_km} km -> R$ {taxa:.2f}")
                        return taxa
                    # Se a distância está acima desta faixa, verificar próxima faixa
                    elif distancia_km > ate_km:
                        # Se há próxima faixa, verificar se a distância está antes dela (entre faixas)
                        if i + 1 < len(faixas):
                            proxima_faixa = faixas[i + 1]
                            de_prox_km = proxima_faixa.get('de_km', 0)
                            # Se a distância está entre esta faixa e a próxima, usar a próxima
                            if distancia_km < de_prox_km:
                                taxa_prox = proxima_faixa.get('taxa', 0)
                                ate_prox_km = proxima_faixa.get('ate_km', '?')
                                if self.DEBUG:
                                    print(f"[DEBUG] Distância {distancia_km} km entre faixas, usando próxima: {de_prox_km}-{ate_prox_km} km -> R$ {taxa_prox:.2f}")
                                return taxa_prox
                        # Se não há próxima faixa ou a distância já passou, continuar
                        continue
                    # Se a distância está antes da primeira faixa, usar a primeira faixa
                    elif distancia_km < de_km and i == 0:
                        if self.DEBUG:
                            print(f"[DEBUG] Distância {distancia_km} km antes da primeira faixa, usando primeira: {de_km}-{ate_km} km -> R$ {taxa:.2f}")
                        return taxa

            # Se passou por todas as faixas e não encontrou, usar a última (para valores acima da última faixa)
            if faixas:
                ultima_faixa = faixas[-1]
                taxa_fallback = ultima_faixa.get('taxa', 0)
                if self.DEBUG:
                    print(f"[DEBUG] Distância {distancia_km} km acima de todas as faixas, usando última: R$ {taxa_fallback:.2f}")
                return taxa_fallback
        else:
            # Formato antigo: faixas cumulativas com apenas ate_km
            # Ordenar faixas por ate_km (None vai para o final)
            faixas_ordenadas = sorted(
                faixas,
                key=lambda x: x.get('ate_km') if x.get('ate_km') is not None else float('inf')
            )

            # Encontrar a faixa correspondente
            for faixa in faixas_ordenadas:
                ate_km = faixa.get('ate_km')
                taxa = faixa.get('taxa', 0)

                if ate_km is None:
                    # Última faixa (sem limite superior)
                    if self.DEBUG:
                        print(f"[DEBUG] Faixa encontrada: acima do limite -> R$ {taxa:.2f}")
                    return taxa
                elif distancia_km <= ate_km:
                    if self.DEBUG:
                        print(f"[DEBUG] Faixa encontrada: até {ate_km} km -> R$ {taxa:.2f}")
                    return taxa

            # Se não encontrou nenhuma faixa, usar a última
            if faixas_ordenadas:
                taxa_fallback = faixas_ordenadas[-1].get('taxa', 0)
                if self.DEBUG:
                    print(f"[DEBUG] Nenhuma faixa encontrada, usando última: R$ {taxa_fallback:.2f}")
                return taxa_fallback

        return 0.0

    def _calcular_por_km(self, distancia_km: float, config: Dict) -> float:
        """
        Calcula taxa usando valor por km

        Args:
            distancia_km: Distância em km
            config: Configuração com valor_por_km e taxa_base

        Returns:
            Taxa calculada
        """
        valor_por_km = config.get('valor_por_km', 2.50)
        taxa_base = config.get('taxa_base', 5.00)

        taxa = taxa_base + (distancia_km * valor_por_km)

        return taxa

    def obter_descricao_faixa(self, distancia_km: float) -> str:
        """
        Retorna descrição da faixa de distância

        Args:
            distancia_km: Distância em km

        Returns:
            Descrição da faixa
        """
        faixas = self.config.get('faixas', [])

        # Verificar se as faixas usam formato novo (de_km/ate_km) ou antigo (ate_km)
        usa_faixas_intervalo = any('de_km' in faixa for faixa in faixas)

        if usa_faixas_intervalo:
            # Novo formato: faixas com de_km e ate_km
            for faixa in faixas:
                de_km = faixa.get('de_km', 0)
                ate_km = faixa.get('ate_km')
                descricao = faixa.get('descricao', '')

                if ate_km is None:
                    # Faixa sem limite superior
                    if distancia_km >= de_km:
                        return descricao or f"Acima de {de_km} km"
                else:
                    # Faixa com intervalo definido
                    if de_km <= distancia_km <= ate_km:
                        return descricao or f"{de_km}-{ate_km} km"

            # Se não encontrou, usar a última faixa
            if faixas:
                ultima_faixa = faixas[-1]
                return ultima_faixa.get('descricao', 'Distância não categorizada')
        else:
            # Formato antigo: faixas cumulativas
            for faixa in sorted(
                faixas,
                key=lambda x: x.get('ate_km') if x.get('ate_km') is not None else float('inf')
            ):
                ate_km = faixa.get('ate_km')
                descricao = faixa.get('descricao', '')

                if ate_km is None:
                    return descricao or f"Acima de {faixas[-2].get('ate_km') if len(faixas) > 1 else 0} km"
                elif distancia_km <= ate_km:
                    return descricao or f"Até {ate_km} km"

        return "Distância não categorizada"


# Instância global do serviço
taxa_entrega_service = TaxaEntregaService()

