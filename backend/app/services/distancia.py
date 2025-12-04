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
    """Serviço para cálculo de distância usando OpenRouteService + Nominatim"""
    
    # URLs das APIs
    GEOCODE_URL = "https://api.openrouteservice.org/geocode/search"
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"  # Geocoding gratuito
    DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"
    
    # Cache de endereços que falharam (evita requisições repetidas)
    _enderecos_invalidos = set()
    
    # Coordenadas centrais de Goiânia para focus.point
    GOIANIA_LAT = -16.6869
    GOIANIA_LON = -49.2648
    
    # Debug mode - ativar logs detalhados
    DEBUG = True
    
    def __init__(self):
        self.api_key = os.environ.get('OPENROUTE_API_KEY', '')
        self.endereco_floricultura = os.environ.get('ENDERECO_FLORICULTURA', '')
        self._coords_floricultura = None
        
        if not self.api_key:
            print("[AVISO] OPENROUTE_API_KEY não configurada no .env")
        if not self.endereco_floricultura:
            print("[AVISO] ENDERECO_FLORICULTURA não configurado no .env")
        else:
            print(f"[DEBUG] Endereço floricultura: {self.endereco_floricultura}")
    
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
            print(f"\n[DEBUG] ========== GEOCODIFICANDO FLORICULTURA ==========")
            print(f"[DEBUG] Endereço configurado: {self.endereco_floricultura}")
            
            # Construir endereço otimizado para geocodificação (prioriza CEP)
            endereco_geocode = self.construir_endereco_para_geocode(
                endereco_completo=self.endereco_floricultura
            )
            
            if endereco_geocode:
                print(f"[DEBUG] Endereço para geocode: {endereco_geocode}")
                self._coords_floricultura = self.geocodificar(endereco_geocode, normalizar=False)
            
            if self._coords_floricultura:
                print(f"[DEBUG] ✓ Coordenadas da floricultura: lon={self._coords_floricultura[0]}, lat={self._coords_floricultura[1]}")
            else:
                print(f"[ERRO] ✗ Falha ao geocodificar endereço da floricultura!")
        return self._coords_floricultura
    
    def _parsear_endereco_com_virgulas(self, endereco):
        """
        Tenta parsear um endereço que vem separado por vírgulas
        Exemplo: "Rua 132,289,Setor Sul,Goiânia,GO,74093-210"
        
        Returns:
            Dict com rua, numero, bairro, cidade, estado, cep
        """
        if not endereco:
            return {}
        
        partes = [p.strip() for p in endereco.split(',') if p.strip()]
        
        if len(partes) < 2:
            return {}
        
        resultado = {}
        
        # Tentar identificar cada parte
        # Padrão comum: Rua, Número, Bairro, Cidade, Estado, CEP
        if len(partes) >= 1:
            resultado['rua'] = partes[0]
        
        if len(partes) >= 2:
            # Pode ser número ou bairro
            if partes[1].isdigit() or re.match(r'^\d+', partes[1]):
                resultado['numero'] = partes[1]
            else:
                resultado['bairro'] = partes[1]
        
        if len(partes) >= 3:
            if 'numero' in resultado:
                resultado['bairro'] = partes[2]
            else:
                resultado['cidade'] = partes[2]
        
        if len(partes) >= 4:
            if 'cidade' not in resultado:
                resultado['cidade'] = partes[3]
            elif partes[3].upper() in ['GO', 'GOIÁS', 'GOIAS']:
                resultado['estado'] = partes[3]
        
        if len(partes) >= 5:
            if 'estado' not in resultado:
                if partes[4].upper() in ['GO', 'GOIÁS', 'GOIAS']:
                    resultado['estado'] = partes[4]
                elif re.match(r'^\d{5}-?\d{3}', partes[4]):
                    resultado['cep'] = partes[4]
        
        if len(partes) >= 6:
            if re.match(r'^\d{5}-?\d{3}', partes[5]):
                resultado['cep'] = partes[5]
        
        return resultado
    
    def construir_endereco_para_geocode(self, rua=None, numero=None, bairro=None, cidade=None, cep=None, endereco_completo=None):
        """
        Constrói um endereço limpo e otimizado para geocodificação.
        Prioriza campos separados pois Nominatim funciona bem com endereços brasileiros.
        
        Args:
            rua: Rua/Logradouro
            numero: Número
            bairro: Bairro
            cidade: Cidade
            cep: CEP
            endereco_completo: Endereço completo (fallback)
            
        Returns:
            String com endereço formatado para geocodificação
        """
        import re
        
        # PRIORIDADE 1: Campos separados (rua + número + bairro + cidade)
        partes = []
        
        if rua and rua.strip():
            rua_limpa = rua.strip()
            partes.append(rua_limpa)
        
        if numero and numero.strip():
            numero_limpo = re.split(r'[,\s]+', numero.strip())[0]
            if numero_limpo and numero_limpo != '0':
                partes.append(numero_limpo)
        
        if bairro and bairro.strip():
            partes.append(bairro.strip())
        
        cidade_final = cidade.strip() if cidade and cidade.strip() else 'Goiânia'
        partes.append(cidade_final)
        partes.append('GO')
        partes.append('Brasil')
        
        # Se temos rua e bairro, usar campos separados
        if rua and bairro:
            endereco_geocode = ', '.join(partes)
            if self.DEBUG:
                print(f"[DEBUG] Endereço dos campos separados: {endereco_geocode}")
            return endereco_geocode
        
        # PRIORIDADE 2: Tentar parsear endereço completo com vírgulas
        if endereco_completo and endereco_completo.strip() and ',' in endereco_completo:
            parsed = self._parsear_endereco_com_virgulas(endereco_completo)
            if parsed:
                if self.DEBUG:
                    print(f"[DEBUG] Endereço parseado: {parsed}")
                # Tentar construir com campos parseados
                return self.construir_endereco_para_geocode(
                    rua=parsed.get('rua'),
                    numero=parsed.get('numero'),
                    bairro=parsed.get('bairro'),
                    cidade=parsed.get('cidade', 'Goiânia'),
                    cep=parsed.get('cep')
                )
        
        # PRIORIDADE 3: Endereço completo limpo
        if endereco_completo and endereco_completo.strip():
            endereco_limpo = self.limpar_endereco(endereco_completo)
            if self.DEBUG:
                print(f"[DEBUG] Endereço completo limpo: {endereco_limpo}")
            return endereco_limpo
        
        # Fallback: juntar o que tiver
        if partes:
            return ', '.join(partes)
        
        return None
    
    def limpar_endereco(self, endereco):
        """
        Limpa um endereço completo removendo informações que confundem a geocodificação.
        
        Args:
            endereco: String com endereço "sujo"
            
        Returns:
            String com endereço limpo
        """
        import re
        
        if not endereco:
            return endereco
        
        endereco = endereco.strip()
        
        # Remover padrões que confundem a geocodificação
        # QD (quadra), LT (lote), BL (bloco), AP (apartamento), etc
        padroes_remover = [
            r'\bQD\s*\d+\b',      # QD 54
            r'\bLT\s*\d+\b',      # LT 6
            r'\bBL\s*\d+\b',      # BL 3
            r'\bAP\s*\d+\b',      # AP 101
            r'\bLOTE\s*\d+\b',    # LOTE 6
            r'\bQUADRA\s*\d+\b',  # QUADRA 54
            r'\bBLOCO\s*\d+\b',   # BLOCO 3
            r'\b0\s+\d+\b',       # 0 14 (número estranho)
            r'\bN[°º]?\s*\d+\b',  # Nº 123, N 123
        ]
        
        for padrao in padroes_remover:
            endereco = re.sub(padrao, '', endereco, flags=re.IGNORECASE)
        
        # Limpar separadores duplicados e espaços extras
        endereco = re.sub(r'[-,\s]+', ' ', endereco)
        endereco = re.sub(r'\s+', ' ', endereco)
        endereco = endereco.strip(' -,')
        
        # Garantir que tem cidade/estado
        endereco_lower = endereco.lower()
        cidades_go = ['goiânia', 'goiania', 'aparecida', 'anápolis', 'anapolis', 'trindade', 'senador canedo']
        
        tem_cidade = any(cidade in endereco_lower for cidade in cidades_go)
        if not tem_cidade:
            endereco = f"{endereco}, Goiânia, GO, Brasil"
        elif 'brasil' not in endereco_lower:
            endereco = f"{endereco}, Brasil"
        
        return endereco
    
    def normalizar_endereco(self, endereco):
        """
        Normaliza o endereço adicionando cidade/estado se não estiver presente
        DEPRECATED: Use construir_endereco_para_geocode() para melhor precisão
        
        Args:
            endereco: String com o endereço
            
        Returns:
            String com endereço normalizado
        """
        if not endereco:
            return endereco
        
        # Usar a nova função de limpeza
        return self.limpar_endereco(endereco)
    
    def geocodificar_nominatim(self, endereco):
        """
        Geocodifica usando Nominatim (OpenStreetMap) - funciona melhor para Brasil
        
        Args:
            endereco: String com o endereço
            
        Returns:
            Tuple (longitude, latitude) ou None se falhar
        """
        if not endereco:
            return None
        
        try:
            # Nominatim requer User-Agent identificando a aplicação
            headers = {
                'User-Agent': 'PlanteumaFlor-GestorPedidos/1.0 (contato@planteumaflor.com.br)',
                'Accept': 'application/json',
                'Accept-Language': 'pt-BR,pt;q=0.9'
            }
            
            params = {
                'q': endereco,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'br',
                'addressdetails': 1
            }
            
            if self.DEBUG:
                print(f"[DEBUG] Nominatim request: {self.NOMINATIM_URL}")
                print(f"[DEBUG] Params: {params}")
            
            response = requests.get(
                self.NOMINATIM_URL,
                headers=headers,
                params=params,
                timeout=15
            )
            
            if self.DEBUG:
                print(f"[DEBUG] Nominatim status: {response.status_code}")
            
            if response.status_code == 200:
                results = response.json()
                
                if self.DEBUG:
                    print(f"[DEBUG] Nominatim resultados: {len(results)}")
                
                if results and len(results) > 0:
                    result = results[0]
                    lat = float(result['lat'])
                    lon = float(result['lon'])
                    display_name = result.get('display_name', 'N/A')
                    
                    if self.DEBUG:
                        print(f"[DEBUG] Nominatim encontrou:")
                        print(f"[DEBUG]   Display: {display_name[:100]}...")
                        print(f"[DEBUG]   Coordenadas: lon={lon}, lat={lat}")
                    
                    return (lon, lat)
                else:
                    if self.DEBUG:
                        print(f"[DEBUG] Nominatim: nenhum resultado para '{endereco}'")
            else:
                if self.DEBUG:
                    print(f"[DEBUG] Nominatim erro HTTP: {response.status_code} - {response.text[:200]}")
            
        except requests.exceptions.Timeout:
            print(f"[ERRO] Nominatim timeout para: {endereco}")
        except requests.exceptions.ConnectionError as e:
            print(f"[ERRO] Nominatim conexão falhou: {e}")
        except Exception as e:
            print(f"[ERRO] Nominatim erro: {e}")
        
        return None
    
    def geocodificar(self, endereco, normalizar=True):
        """
        Converte endereço em coordenadas (latitude, longitude)
        Usa Nominatim (OpenStreetMap) como principal, OpenRouteService como backup
        
        Args:
            endereco: String com o endereço completo
            normalizar: Se True, adiciona cidade/estado se não presente
            
        Returns:
            Tuple (longitude, latitude) ou None se falhar
        """
        if not endereco:
            return None
        
        # Normalizar endereço se solicitado
        endereco_original = endereco
        if normalizar:
            endereco = self.normalizar_endereco(endereco)
        
        if self.DEBUG:
            print(f"\n[DEBUG] --- Geocodificando ---")
            print(f"[DEBUG] Endereço original: {endereco_original}")
            print(f"[DEBUG] Endereço para API: {endereco}")
        
        # TENTATIVA 1: Nominatim (OpenStreetMap) - funciona melhor para Brasil
        if self.DEBUG:
            print(f"[DEBUG] Tentando Nominatim...")
        
        coords = self.geocodificar_nominatim(endereco)
        if coords:
            return coords
        
        # TENTATIVA 2: OpenRouteService como backup
        if self.DEBUG:
            print(f"[DEBUG] Nominatim falhou, tentando OpenRouteService...")
        
        if not self.api_key:
            return None
        
        try:
            headers = {
                'Authorization': self.api_key,
                'Content-Type': 'application/json'
            }
            
            params = {
                'api_key': self.api_key,
                'text': endereco,
                'boundary.country': 'BR',
                'size': 1,
                'focus.point.lat': self.GOIANIA_LAT,
                'focus.point.lon': self.GOIANIA_LON
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
                    feature = features[0]
                    coords = feature['geometry']['coordinates']
                    properties = feature.get('properties', {})
                    
                    label = properties.get('label', 'N/A')
                    confidence = properties.get('confidence', 0)
                    accuracy = properties.get('accuracy', 'N/A')
                    
                    # Rejeitar se for fallback/centroid com baixa confiança
                    if accuracy == 'centroid' and confidence < 0.7:
                        if self.DEBUG:
                            print(f"[DEBUG] Resultado rejeitado (centroid com baixa confiança)")
                        return None
                    
                    if self.DEBUG:
                        print(f"[DEBUG] OpenRouteService encontrou:")
                        print(f"[DEBUG]   Label: {label}")
                        print(f"[DEBUG]   Confidence: {confidence}")
                        print(f"[DEBUG]   Coordenadas: lon={coords[0]}, lat={coords[1]}")
                    
                    return (coords[0], coords[1])
                else:
                    if self.DEBUG:
                        print(f"[DEBUG] Nenhum resultado encontrado")
            else:
                print(f"[ERRO] Geocodificação falhou: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"[ERRO] Timeout ao geocodificar: {endereco}")
        except Exception as e:
            print(f"[ERRO] Erro ao geocodificar: {e}")
        
        return None
    
    def _validar_coordenadas(self, coords):
        """
        Valida se as coordenadas são válidas
        
        Args:
            coords: Tuple (lon, lat) ou (lat, lon)
            
        Returns:
            bool - True se válidas
        """
        if not coords or len(coords) < 2:
            return False
        
        lon, lat = coords[0], coords[1]
        
        # Validar ranges: longitude [-180, 180], latitude [-90, 90]
        if not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
            return False
        
        # Validar se não são zeros (pode indicar erro)
        if lon == 0 and lat == 0:
            return False
        
        return True
    
    def _calcular_distancia_haversine(self, coords_origem, coords_destino):
        """
        Calcula distância em linha reta usando fórmula de Haversine
        Útil como último recurso quando APIs falharem
        
        Args:
            coords_origem: Tuple (longitude, latitude)
            coords_destino: Tuple (longitude, latitude)
            
        Returns:
            Dict com distancia_km e duracao_min estimada, ou None
        """
        import math
        
        if not self._validar_coordenadas(coords_origem) or not self._validar_coordenadas(coords_destino):
            return None
        
        try:
            lat1, lon1 = math.radians(coords_origem[1]), math.radians(coords_origem[0])
            lat2, lon2 = math.radians(coords_destino[1]), math.radians(coords_destino[0])
            
            # Raio da Terra em km
            R = 6371.0
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
            c = 2 * math.asin(math.sqrt(a))
            
            distancia_km = R * c
            
            # Estimar duração: média de 40 km/h em cidade
            duracao_min = (distancia_km / 40) * 60
            
            if self.DEBUG:
                print(f"[DEBUG] Distância Haversine (linha reta): {distancia_km:.2f} km")
                print(f"[DEBUG] Duração estimada: {duracao_min:.1f} min")
            
            return {
                'distancia_km': round(distancia_km, 2),
                'duracao_min': round(duracao_min, 1),
                'coords_origem': coords_origem,
                'coords_destino': coords_destino,
                'metodo': 'haversine'
            }
        except Exception as e:
            if self.DEBUG:
                print(f"[ERRO] Erro ao calcular distância Haversine: {e}")
            return None
    
    def calcular_distancia(self, coords_origem, coords_destino):
        """
        Calcula a distância de rota (dirigindo) entre dois pontos
        Tenta usar GraphHopper primeiro, com fallback para OpenRouteService e Haversine
        
        Args:
            coords_origem: Tuple (longitude, latitude) do ponto de origem
            coords_destino: Tuple (longitude, latitude) do ponto de destino
            
        Returns:
            Dict com distancia_km, duracao_min e coordenadas, ou None se falhar
        """
        if not coords_origem or not coords_destino:
            if self.DEBUG:
                print("[ERRO] Coordenadas de origem ou destino não fornecidas")
            return None
        
        # Validar coordenadas
        if not self._validar_coordenadas(coords_origem):
            if self.DEBUG:
                print(f"[ERRO] Coordenadas de origem inválidas: {coords_origem}")
            return None
        
        if not self._validar_coordenadas(coords_destino):
            if self.DEBUG:
                print(f"[ERRO] Coordenadas de destino inválidas: {coords_destino}")
            return None
        
        if self.DEBUG:
            print(f"\n[DEBUG] ========== CALCULANDO DISTÂNCIA ==========")
            print(f"[DEBUG] Origem:  lon={coords_origem[0]}, lat={coords_origem[1]}")
            print(f"[DEBUG] Destino: lon={coords_destino[0]}, lat={coords_destino[1]}")
        
        # TENTATIVA 1: GraphHopper (preferido)
        if self.DEBUG:
            print(f"[DEBUG] Tentativa 1: GraphHopper...")
        
        try:
            from app.services.graphhopper import graphhopper_service
            
            # GraphHopper usa (lat, lon), mas recebemos (lon, lat)
            origem_gh = (coords_origem[1], coords_origem[0])  # Converter para (lat, lon)
            destino_gh = (coords_destino[1], coords_destino[0])
            
            resultado_gh = graphhopper_service.calcular_rota(origem_gh, destino_gh)
            
            if resultado_gh:
                if self.DEBUG:
                    print(f"[DEBUG] ✓ Sucesso com GraphHopper: {resultado_gh['distancia_km']} km")
                # Converter de volta para (lon, lat) para manter compatibilidade
                return {
                    'distancia_km': resultado_gh['distancia_km'],
                    'duracao_min': resultado_gh['duracao_min'],
                    'coords_origem': coords_origem,
                    'coords_destino': coords_destino,
                    'metodo': 'graphhopper'
                }
            else:
                if self.DEBUG:
                    print(f"[DEBUG] ✗ GraphHopper retornou None")
        except ImportError as e:
            if self.DEBUG:
                print(f"[DEBUG] GraphHopper não disponível: {e}")
        except Exception as e:
            if self.DEBUG:
                print(f"[DEBUG] ✗ GraphHopper falhou: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
        
        # TENTATIVA 2: OpenRouteService (fallback)
        if self.DEBUG:
            print(f"[DEBUG] Tentativa 2: OpenRouteService...")
        
        if not self.api_key:
            if self.DEBUG:
                print(f"[DEBUG] ✗ OPENROUTE_API_KEY não configurada, pulando OpenRouteService")
        else:
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
                
                if self.DEBUG:
                    print(f"[DEBUG] Enviando requisição para OpenRouteService...")
                
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
                        
                        distancia_km = round(distancia_metros / 1000, 2)
                        duracao_min = round(duracao_segundos / 60, 0)
                        
                        if self.DEBUG:
                            print(f"[DEBUG] ✓ Sucesso com OpenRouteService: {distancia_km} km, {duracao_min} min")
                        
                        return {
                            'distancia_km': distancia_km,
                            'duracao_min': duracao_min,
                            'coords_origem': coords_origem,
                            'coords_destino': coords_destino,
                            'metodo': 'openrouteservice'
                        }
                    else:
                        if self.DEBUG:
                            print(f"[DEBUG] ✗ OpenRouteService não retornou rotas")
                else:
                    if self.DEBUG:
                        print(f"[ERRO] OpenRouteService retornou status {response.status_code}: {response.text[:200]}")
                    
            except requests.exceptions.Timeout:
                if self.DEBUG:
                    print(f"[ERRO] Timeout ao calcular rota com OpenRouteService")
            except Exception as e:
                if self.DEBUG:
                    print(f"[ERRO] Erro ao calcular rota com OpenRouteService: {type(e).__name__}: {e}")
                    import traceback
                    traceback.print_exc()
        
        # TENTATIVA 3: Haversine (último recurso - distância em linha reta)
        if self.DEBUG:
            print(f"[DEBUG] Tentativa 3: Haversine (distância em linha reta)...")
        
        resultado_haversine = self._calcular_distancia_haversine(coords_origem, coords_destino)
        if resultado_haversine:
            if self.DEBUG:
                print(f"[DEBUG] ✓ Usando distância Haversine como último recurso")
            return resultado_haversine
        
        if self.DEBUG:
            print(f"[ERRO] ✗ Todas as tentativas falharam ao calcular distância")
        
        return None
    
    def calcular_distancia_pedido(self, endereco_pedido=None, pedido_id=None, rua=None, numero=None, bairro=None, cidade=None, cep=None):
        """
        Calcula a distância da floricultura até o endereço do pedido.
        Prioriza campos separados para melhor precisão na geocodificação.
        
        Args:
            endereco_pedido: String com o endereço de entrega (fallback)
            pedido_id: ID do pedido (opcional, para logs)
            rua: Rua/Logradouro
            numero: Número
            bairro: Bairro
            cidade: Cidade
            cep: CEP
            
        Returns:
            Dict com distancia_km, duracao_min e coordenadas, ou None se falhar
        """
        print(f"\n[DEBUG] ========== CALCULANDO DISTÂNCIA PEDIDO {pedido_id or '?'} ==========")
        
        # Construir endereço otimizado para geocodificação
        endereco_geocode = self.construir_endereco_para_geocode(
            rua=rua,
            numero=numero,
            bairro=bairro,
            cidade=cidade,
            cep=cep,
            endereco_completo=endereco_pedido
        )
        
        if not endereco_geocode:
            print(f"[ERRO] Não foi possível construir endereço para geocodificação")
            return None
        
        print(f"[DEBUG] Endereço original: {endereco_pedido}")
        print(f"[DEBUG] Campos separados: rua={rua}, num={numero}, bairro={bairro}, cidade={cidade}, cep={cep}")
        print(f"[DEBUG] Endereço para geocode: {endereco_geocode}")
        
        # Validar formato do endereço antes de tentar geocodificar
        valido, motivo = self.validar_endereco(endereco_geocode)
        if not valido:
            print(f"[INFO] Endereço inválido para geocodificação: {motivo}")
            return None
        
        # Obter coordenadas da floricultura
        if self.DEBUG:
            print(f"[DEBUG] Obtendo coordenadas da floricultura...")
        
        origem = self.coords_floricultura
        if not origem:
            erro_msg = "Não foi possível obter coordenadas da floricultura. Verifique se ENDERECO_FLORICULTURA está configurado corretamente no .env"
            print(f"[ERRO] {erro_msg}")
            if self.DEBUG:
                print(f"[DEBUG] Endereço configurado: {self.endereco_floricultura}")
            return None
        
        if self.DEBUG:
            print(f"[DEBUG] ✓ Coordenadas da floricultura obtidas: lon={origem[0]}, lat={origem[1]}")
        
        # Geocodificar endereço do pedido
        if self.DEBUG:
            print(f"[DEBUG] Geocodificando endereço do pedido...")
        
        destino = self.geocodificar(endereco_geocode, normalizar=False)  # Já está normalizado
        if not destino:
            # Marcar como inválido para não tentar novamente
            self.marcar_endereco_invalido(endereco_geocode)
            erro_msg = f"Não foi possível geocodificar o endereço: {endereco_geocode[:80]}..."
            print(f"[ERRO] {erro_msg}")
            if self.DEBUG:
                print(f"[DEBUG] Endereço original: {endereco_pedido}")
                print(f"[DEBUG] Endereço processado: {endereco_geocode}")
            return None
        
        if self.DEBUG:
            print(f"[DEBUG] ✓ Endereço geocodificado: lon={destino[0]}, lat={destino[1]}")
        
        # Calcular distância
        if self.DEBUG:
            print(f"[DEBUG] Calculando distância entre origem e destino...")
        
        resultado = self.calcular_distancia(origem, destino)
        
        if resultado:
            # Adicionar coordenadas do destino ao resultado (para salvar no banco)
            resultado['coords_destino_lat'] = destino[1]  # latitude
            resultado['coords_destino_lon'] = destino[0]  # longitude
            metodo = resultado.get('metodo', 'desconhecido')
            print(f"[DEBUG] ✓ Pedido {pedido_id or '?'}: {resultado['distancia_km']} km (método: {metodo})")
        else:
            erro_msg = f"Falha no cálculo de rota. Todas as tentativas (GraphHopper, OpenRouteService, Haversine) falharam."
            print(f"[ERRO] ✗ Pedido {pedido_id or '?'}: {erro_msg}")
            if self.DEBUG:
                print(f"[DEBUG] Origem: {origem}")
                print(f"[DEBUG] Destino: {destino}")
        
        return resultado
    
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

