# -*- coding: utf-8 -*-
"""
Serviço de Cálculo de Distância usando OpenRouteService
Geocodifica endereços e calcula distância de rota (dirigindo)
"""
import os
import re
import requests
from functools import lru_cache

class DistanciaService:
    """Serviço para cálculo de distância usando OpenRouteService"""
    
    # URLs das APIs do OpenRouteService
    GEOCODE_URL = "https://api.openrouteservice.org/geocode/search"
    DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"
    
    # Cache de endereços que falharam (evita requisições repetidas)
    _enderecos_invalidos = set()
    
    def __init__(self):
        self.api_key = os.environ.get('OPENROUTE_API_KEY', '')
        self.endereco_floricultura = os.environ.get('ENDERECO_FLORICULTURA', '')
        self._coords_floricultura = None
        
        if not self.api_key:
            print("[AVISO] OPENROUTE_API_KEY não configurada no .env")
        if not self.endereco_floricultura:
            print("[AVISO] ENDERECO_FLORICULTURA não configurado no .env")
    
    def validar_endereco(self, endereco):
        """
        Valida se o endereço tem formato mínimo aceitável para geocodificação
        
        Args:
            endereco: String com o endereço
            
        Returns:
            Tuple (bool, str) - (válido, motivo se inválido)
        """
        if not endereco:
            return False, "Endereço vazio"
        
        endereco = endereco.strip()
        
        # Endereço muito curto
        if len(endereco) < 10:
            return False, "Endereço muito curto"
        
        # Verificar se tem pelo menos algumas palavras
        palavras = endereco.split()
        if len(palavras) < 2:
            return False, "Endereço incompleto"
        
        # Verificar se já falhou antes (cache de inválidos)
        if endereco in self._enderecos_invalidos:
            return False, "Endereço já marcado como inválido"
        
        # Padrões que indicam endereço válido (pelo menos um deve existir)
        padroes_validos = [
            r'\d+',           # Contém número
            r'rua|av\.|avenida|alameda|praça|travessa|rod\.|rodovia',  # Tipo de logradouro
            r'bairro|setor|centro|jardim|parque|vila',  # Tipo de região
            r'\d{5}-?\d{3}',  # CEP
        ]
        
        endereco_lower = endereco.lower()
        tem_padrao_valido = any(
            re.search(padrao, endereco_lower) 
            for padrao in padroes_validos
        )
        
        if not tem_padrao_valido:
            return False, "Endereço não contém informações reconhecíveis"
        
        return True, ""
    
    def marcar_endereco_invalido(self, endereco):
        """Marca um endereço como inválido no cache"""
        if endereco:
            self._enderecos_invalidos.add(endereco.strip())
    
    @property
    def coords_floricultura(self):
        """Retorna coordenadas da floricultura (com cache)"""
        if self._coords_floricultura is None and self.endereco_floricultura:
            self._coords_floricultura = self.geocodificar(self.endereco_floricultura)
        return self._coords_floricultura
    
    def geocodificar(self, endereco):
        """
        Converte endereço em coordenadas (latitude, longitude)
        
        Args:
            endereco: String com o endereço completo
            
        Returns:
            Tuple (longitude, latitude) ou None se falhar
        """
        if not self.api_key or not endereco:
            return None
        
        try:
            headers = {
                'Authorization': self.api_key,
                'Content-Type': 'application/json'
            }
            
            params = {
                'api_key': self.api_key,
                'text': endereco,
                'boundary.country': 'BR',  # Limitar ao Brasil
                'size': 1  # Retornar apenas o melhor resultado
            }
            
            response = requests.get(
                self.GEOCODE_URL,
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                features = data.get('features', [])
                
                if features:
                    coords = features[0]['geometry']['coordinates']
                    # OpenRouteService retorna [longitude, latitude]
                    return (coords[0], coords[1])
            else:
                print(f"[ERRO] Geocodificação falhou: {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            print(f"[ERRO] Timeout ao geocodificar: {endereco}")
        except Exception as e:
            print(f"[ERRO] Erro ao geocodificar: {e}")
        
        return None
    
    def calcular_distancia(self, coords_origem, coords_destino):
        """
        Calcula a distância de rota (dirigindo) entre dois pontos
        
        Args:
            coords_origem: Tuple (longitude, latitude) do ponto de origem
            coords_destino: Tuple (longitude, latitude) do ponto de destino
            
        Returns:
            Dict com distancia_km e duracao_min, ou None se falhar
        """
        if not self.api_key or not coords_origem or not coords_destino:
            return None
        
        try:
            headers = {
                'Authorization': self.api_key,
                'Content-Type': 'application/json'
            }
            
            body = {
                'coordinates': [
                    list(coords_origem),  # [longitude, latitude]
                    list(coords_destino)
                ]
            }
            
            response = requests.post(
                self.DIRECTIONS_URL,
                headers=headers,
                json=body,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                routes = data.get('routes', [])
                
                if routes:
                    summary = routes[0].get('summary', {})
                    distancia_metros = summary.get('distance', 0)
                    duracao_segundos = summary.get('duration', 0)
                    
                    return {
                        'distancia_km': round(distancia_metros / 1000, 2),
                        'duracao_min': round(duracao_segundos / 60, 0)
                    }
            else:
                print(f"[ERRO] Cálculo de rota falhou: {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            print("[ERRO] Timeout ao calcular rota")
        except Exception as e:
            print(f"[ERRO] Erro ao calcular rota: {e}")
        
        return None
    
    def calcular_distancia_pedido(self, endereco_pedido):
        """
        Calcula a distância da floricultura até o endereço do pedido
        
        Args:
            endereco_pedido: String com o endereço de entrega
            
        Returns:
            Dict com distancia_km e duracao_min, ou None se falhar
        """
        if not endereco_pedido:
            return None
        
        # Validar formato do endereço antes de tentar geocodificar
        valido, motivo = self.validar_endereco(endereco_pedido)
        if not valido:
            print(f"[INFO] Endereço inválido para geocodificação: {motivo} - '{endereco_pedido[:50]}...'")
            return None
        
        # Obter coordenadas da floricultura
        origem = self.coords_floricultura
        if not origem:
            print("[ERRO] Não foi possível obter coordenadas da floricultura")
            return None
        
        # Geocodificar endereço do pedido
        destino = self.geocodificar(endereco_pedido)
        if not destino:
            # Marcar como inválido para não tentar novamente
            self.marcar_endereco_invalido(endereco_pedido)
            print(f"[ERRO] Não foi possível geocodificar: {endereco_pedido[:50]}...")
            return None
        
        # Calcular distância
        return self.calcular_distancia(origem, destino)
    
    def calcular_distancias_lote(self, pedidos):
        """
        Calcula distâncias para múltiplos pedidos
        
        Args:
            pedidos: Lista de dicts com 'id' e 'endereco'
            
        Returns:
            Dict com id do pedido como chave e distância como valor
        """
        resultados = {}
        
        for pedido in pedidos:
            pedido_id = pedido.get('id')
            endereco = pedido.get('endereco', '')
            
            if not endereco:
                resultados[pedido_id] = None
                continue
            
            resultado = self.calcular_distancia_pedido(endereco)
            resultados[pedido_id] = resultado
        
        return resultados


# Instância global do serviço
distancia_service = DistanciaService()

