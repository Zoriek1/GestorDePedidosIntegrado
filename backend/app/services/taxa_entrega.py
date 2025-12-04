# -*- coding: utf-8 -*-
"""
Serviço de Cálculo de Taxa de Entrega
Calcula taxa de entrega baseada em distância com configuração customizável
"""
import os
import json
from typing import Optional, Dict


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
            print(f"[DEBUG] TaxaEntregaService inicializado")
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
            print(f"\n[DEBUG] --- Calculando Taxa de Entrega ---")
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
                return taxa
            elif distancia_km <= ate_km:
                return taxa
        
        # Se não encontrou nenhuma faixa, usar a última
        if faixas_ordenadas:
            return faixas_ordenadas[-1].get('taxa', 0)
        
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

