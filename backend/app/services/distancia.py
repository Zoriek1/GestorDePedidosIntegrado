# -*- coding: utf-8 -*-
"""
Serviço de Cálculo de Distância usando OpenRouteService
Geocodifica endereços e calcula distância de rota (dirigindo)
"""
import os
import re

from app.config import Config
from app.integrations import geocoding
from app.utils.http_client import HttpClient
from app.utils.logger import get_logger


def _get_config_value(config, key, default=None):
    if config is None:
        return default
    if hasattr(config, "get"):
        return config.get(key, default)
    return getattr(config, key, default)


def _resolve_debug(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on", "debug"}

class DistanciaService:
    """Serviço para cálculo de distância usando OpenRouteService + Nominatim"""
    
    # URLs das APIs
    GEOCODE_URL = "https://api.openrouteservice.org/geocode/search"
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"  # Geocoding gratuito
    DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"
    VIACEP_URL = "https://viacep.com.br/ws"  # API ViaCEP para validação de CEP
    
    # Cache de endereços que falharam (evita requisições repetidas)
    _enderecos_invalidos = set()
    
    # Coordenadas centrais de Goiânia para focus.point
    GOIANIA_LAT = -16.6869
    GOIANIA_LON = -49.2648
    
    # Debug mode - ativar logs detalhados
    DEBUG = True

    def __init__(self, http_client=None, config=None):
        self.config = config or Config
        self.logger = get_logger(__name__)
        self.http_client = http_client or HttpClient(timeout=10)
        debug_value = _get_config_value(self.config, "DEBUG", os.environ.get("DEBUG", False))
        self.DEBUG = _resolve_debug(debug_value)

        self.api_key = _get_config_value(self.config, "OPENROUTE_API_KEY", os.environ.get("OPENROUTE_API_KEY", ""))
        self.endereco_floricultura = _get_config_value(
            self.config,
            "ENDERECO_FLORICULTURA",
            os.environ.get("ENDERECO_FLORICULTURA", ""),
        )
        self._coords_floricultura = None

        if not self.api_key:
            self.logger.warning("OPENROUTE_API_KEY não configurada no .env")
        if not self.endereco_floricultura:
            self.logger.warning("ENDERECO_FLORICULTURA não configurado no .env")
        else:
            self.logger.debug("Endereço floricultura: %s", self.endereco_floricultura)
    
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
    
    def buscar_endereco_por_cep(self, cep):
        """
        Busca o endereço completo usando a API ViaCEP.
        Retorna endereço formatado pronto para geocodificação.
        
        Args:
            cep: CEP com ou sem formatação (XXXXX-XXX ou XXXXXXXX)
            
        Returns:
            String com endereço formatado ou None se CEP inválido
        """
        import re
        
        if not cep:
            return None
        
        # Limpar CEP (remover caracteres não numéricos)
        cep_limpo = re.sub(r'\D', '', str(cep))
        
        if len(cep_limpo) != 8:
            self.logger.debug("CEP inválido (deve ter 8 dígitos): %s", cep)
            return None
        
        self.logger.debug("Consultando ViaCEP: %s/%s/json/", self.VIACEP_URL, cep_limpo)
        return geocoding.buscar_endereco_por_cep(
            cep_limpo,
            http_client=self.http_client,
            logger=self.logger,
        )
    
    def validar_coords_goias(self, coords):
        """
        Valida se as coordenadas estão dentro da região de Goiás.
        Isso evita que geocodificadores retornem locais errados de outras regiões do Brasil.
        
        Args:
            coords: Tuple (longitude, latitude)
            
        Returns:
            bool - True se as coordenadas estão em Goiás/região metropolitana
        """
        if not coords or len(coords) < 2:
            return False
        
        lon, lat = coords[0], coords[1]
        
        # Limites aproximados de Goiás e região metropolitana de Goiânia
        # Latitude: de -19.5 (sul de GO) até -12.5 (norte de GO)
        # Longitude: de -53.5 (oeste de GO) até -45.5 (leste de GO)
        # Incluindo margem para cidades próximas como Aparecida de Goiânia
        
        if not (-19.5 <= lat <= -12.5):
            self.logger.warning(
                "Latitude %s está FORA de Goiás (esperado: -19.5 a -12.5)", lat
            )
            return False

        if not (-53.5 <= lon <= -45.5):
            self.logger.warning(
                "Longitude %s está FORA de Goiás (esperado: -53.5 a -45.5)", lon
            )
            return False
        
        return True
    
    def validar_campos_endereco(self, rua=None, bairro=None, cep=None):
        """
        Valida se os campos mínimos para geocodificação estão presentes e são válidos.
        
        Args:
            rua: Rua/Logradouro
            bairro: Bairro
            cep: CEP (opcional, mas se fornecido deve ser válido)
            
        Returns:
            Tuple (valido: bool, mensagem_erro: str)
        """
        # Validar rua (obrigatório)
        if not rua or not rua.strip():
            return False, "Campo 'Rua' é obrigatório para calcular distância"
        
        # Validar bairro (obrigatório)
        if not bairro or not bairro.strip():
            return False, "Campo 'Bairro' é obrigatório para calcular distância"
        
        # Validar CEP se fornecido (deve ter 8 dígitos)
        if cep and cep.strip():
            cep_limpo = re.sub(r'\D', '', cep)
            if len(cep_limpo) != 8:
                return False, f"CEP inválido: deve ter 8 dígitos (recebido: '{cep}')"
        
        return True, ""
    
    @property
    def coords_floricultura(self):
        """Retorna coordenadas da floricultura (com cache)"""
        if self._coords_floricultura is None and self.endereco_floricultura:
            self.logger.debug("========== GEOCODIFICANDO FLORICULTURA ==========")
            self.logger.debug("Endereço configurado: %s", self.endereco_floricultura)
            
            # Melhorar formatação do endereço da floricultura que vem do .env
            # Ex: "Rua 132,289,Setor Sul,Goiânia,GO,74093-210" -> "Rua 132, 289, Setor Sul, Goiânia, GO, 74093-210"
            endereco_formatado = self.endereco_floricultura
            
            # Adicionar espaço após vírgulas (mas não dentro de CEPs)
            if ',' in endereco_formatado and ', ' not in endereco_formatado:
                # Proteger CEPs antes
                import re
                cep_pattern = r'(\d{5})-(\d{3})'
                ceps_encontrados = re.findall(cep_pattern, endereco_formatado)
                endereco_temp = re.sub(cep_pattern, '__CEP__', endereco_formatado)
                
                # Adicionar espaço após vírgulas
                endereco_temp = re.sub(r',(?!\s)', ', ', endereco_temp)
                
                # Restaurar CEPs
                for cep_parte1, cep_parte2 in ceps_encontrados:
                    endereco_temp = endereco_temp.replace('__CEP__', f'{cep_parte1}-{cep_parte2}', 1)
                
                endereco_formatado = endereco_temp
                self.logger.debug("Endereço formatado: %s", endereco_formatado)
            
            # Limpar o endereço
            endereco_limpo = self.limpar_endereco(endereco_formatado)
            self.logger.debug("Endereço limpo para geocode: %s", endereco_limpo)
            
            resultado_geocode = self.geocodificar(endereco_limpo, normalizar=False)
            
            # Extrair coordenadas (pode ser tupla ou dict)
            if isinstance(resultado_geocode, dict):
                self._coords_floricultura = resultado_geocode['coords']
            else:
                self._coords_floricultura = resultado_geocode
            
            if self._coords_floricultura:
                self.logger.debug(
                    "✓ Coordenadas da floricultura: lon=%s, lat=%s",
                    self._coords_floricultura[0],
                    self._coords_floricultura[1],
                )
            else:
                self.logger.error("✗ Falha ao geocodificar endereço da floricultura!")
        return self._coords_floricultura
    
    def construir_endereco_para_geocode(self, rua=None, numero=None, bairro=None, cidade=None, cep=None):
        """
        Constrói um endereço limpo e otimizado para geocodificação usando APENAS campos separados.
        NÃO usa o campo 'endereco' completo pois contém complementos que confundem a geocodificação.
        
        Args:
            rua: Rua/Logradouro (OBRIGATÓRIO)
            numero: Número
            bairro: Bairro (OBRIGATÓRIO)
            cidade: Cidade
            cep: CEP (opcional, mas se fornecido deve ser válido)
            
        Returns:
            String com endereço formatado para geocodificação, ou None se dados mínimos não presentes
        """
        import re
        
        # Validar campos mínimos obrigatórios
        valido, mensagem_erro = self.validar_campos_endereco(rua=rua, bairro=bairro, cep=cep)
        if not valido:
            self.logger.debug("Validação falhou: %s", mensagem_erro)
            return None
        
        # Construir endereço limpo apenas com campos separados
        partes = []
        
        # Rua (obrigatória, já validada)
        rua_limpa = rua.strip()
        partes.append(rua_limpa)
        
        # Número (opcional)
        if numero and numero.strip():
            numero_limpo = re.split(r'[,\s]+', numero.strip())[0]
            # Ignorar número "0" ou "S/N" (sem número)
            if numero_limpo and numero_limpo not in ['0', 's/n', 'sn', 'S/N', 'SN']:
                partes.append(numero_limpo)
        
        # Bairro (obrigatório, já validado)
        partes.append(bairro.strip())
        
        # Cidade (padrão: Goiânia)
        cidade_final = cidade.strip() if cidade and cidade.strip() else 'Goiânia'
        partes.append(cidade_final)
        
        # Estado e País
        partes.append('GO')
        partes.append('Brasil')
        
        # Formato final: "Rua X, Número, Bairro, Cidade, GO, Brasil"
        endereco_geocode = ', '.join(partes)
        
        self.logger.debug("Endereço construído dos campos separados: %s", endereco_geocode)
        
        return endereco_geocode
    
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
        
        # Proteger CEPs antes de fazer substituições
        # CEP formato: XXXXX-XXX
        cep_pattern = r'(\d{5})-(\d{3})'
        ceps_encontrados = re.findall(cep_pattern, endereco)
        # Substituir temporariamente CEPs por placeholder
        endereco_temp = re.sub(cep_pattern, '__CEP__', endereco)
        
        # Substituir múltiplos hífens/vírgulas por vírgula simples (mas não em CEPs)
        endereco_temp = re.sub(r'\s*-\s*', ', ', endereco_temp)  # "0 -Capuava" -> "0, Capuava"
        endereco_temp = re.sub(r',\s*,+', ', ', endereco_temp)  # Remover vírgulas duplicadas
        
        # Restaurar CEPs
        for cep_parte1, cep_parte2 in ceps_encontrados:
            endereco_temp = endereco_temp.replace('__CEP__', f'{cep_parte1}-{cep_parte2}', 1)
        
        endereco = endereco_temp
        
        # Remover número "0" no início (geralmente significa sem número)
        endereco = re.sub(r',\s*0\s*,', ', ', endereco)  # ", 0," -> ", "
        endereco = re.sub(r',\s*0\s+-', ', ', endereco)  # ", 0 -" -> ", "
        
        # Remover complementos que confundem geocodificação
        complementos_remover = [
            r'\bresidencial\s+\w+\b',     # Residencial Privê, Residencial X
            r'\bcondomínio\s+\w+\b',      # Condomínio X
            r'\bedifício\s+\w+\b',        # Edifício X
            r'\bprédio\s+\w+\b',          # Prédio X
            r'\btorre\s+\w+\b',           # Torre X
        ]
        
        for padrao in complementos_remover:
            endereco = re.sub(padrao, '', endereco, flags=re.IGNORECASE)
        
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
        endereco = re.sub(r',\s*,+', ', ', endereco)  # Vírgulas duplicadas
        endereco = re.sub(r'\s+', ' ', endereco)  # Espaços múltiplos
        endereco = endereco.strip(' -,')  # Remover no início/fim
        
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
        coords = geocoding.geocodificar_nominatim(
            endereco,
            http_client=self.http_client,
            logger=self.logger,
        )
        if not coords:
            return None
        if not self.validar_coords_goias(coords):
            self.logger.warning(
                "Nominatim retornou local FORA de Goiás: lon=%s lat=%s",
                coords[0],
                coords[1],
            )
            return None
        return coords
    
    def geocodificar(self, endereco, normalizar=True, cep_separado=None):
        """
        Converte endereço em coordenadas (latitude, longitude)
        Usa Nominatim (OpenStreetMap) como principal, OpenRouteService como backup
        
        Args:
            endereco: String com o endereço completo
            normalizar: Se True, adiciona cidade/estado se não presente
            cep_separado: CEP fornecido separadamente (usado como fallback)
            
        Returns:
            Tuple (longitude, latitude) para endereços exatos
            OU Dict {'coords': (lon, lat), 'aproximado': True, 'nivel_aproximacao': str, 'aviso': str}
            OU None se falhar
        """
        if not endereco:
            return None

        endereco_original = endereco
        if normalizar:
            endereco = self.normalizar_endereco(endereco)

        self.logger.debug("--- Geocodificando ---")
        self.logger.debug("Endereço original: %s", endereco_original)
        self.logger.debug("Endereço para API: %s", endereco)

        self.logger.debug("Tentando Nominatim com variações do endereço...")

        coords = self.geocodificar_nominatim(endereco)
        if coords and self.validar_coords_goias(coords):
            return coords

        if "," in endereco:
            partes = [p.strip() for p in endereco.split(",")]
            if len(partes) >= 3:
                endereco_sem_numero = ", ".join([partes[0]] + partes[2:])
                self.logger.debug("Tentando sem número: %s", endereco_sem_numero)
                coords = self.geocodificar_nominatim(endereco_sem_numero)
                if coords and self.validar_coords_goias(coords):
                    return coords

        if "," in endereco:
            partes = [p.strip() for p in endereco.split(",")]
            if len(partes) >= 4:
                endereco_simplificado = ", ".join([partes[0], partes[2], partes[3], "GO", "Brasil"])
                self.logger.debug("Tentando simplificado: %s", endereco_simplificado)
                coords = self.geocodificar_nominatim(endereco_simplificado)
                if coords and self.validar_coords_goias(coords):
                    return coords

        import re
        cep = None
        cep_match = re.search(r"(\d{5})-?(\d{3})", endereco)
        if cep_match:
            cep = f"{cep_match.group(1)}{cep_match.group(2)}"
        elif cep_separado:
            cep = re.sub(r"\D", "", str(cep_separado))

        if cep and len(cep) == 8:
            self.logger.debug("Tentando obter endereço do CEP via ViaCEP...")
            endereco_viacep = self.buscar_endereco_por_cep(cep)
            if endereco_viacep:
                self.logger.debug("Geocodificando endereço do ViaCEP: %s", endereco_viacep)
                coords = self.geocodificar_nominatim(endereco_viacep)
                if coords and self.validar_coords_goias(coords):
                    self.logger.info("✓ Endereço encontrado via ViaCEP + Nominatim")
                    return coords

            cep_formatado = f"{cep[:5]}-{cep[5:]}"
            endereco_cep = f"{cep_formatado}, Brasil"
            self.logger.debug("Tentando apenas com CEP no Nominatim: %s", endereco_cep)
            coords = self.geocodificar_nominatim(endereco_cep)
            if coords and self.validar_coords_goias(coords):
                self.logger.info("✓ Endereço encontrado usando apenas CEP: %s", cep_formatado)
                return coords

            self.logger.debug("CEP %s não encontrou resultado válido em Goiás", cep_formatado)

        if cep_separado:
            endereco_viacep = self.buscar_endereco_por_cep(cep_separado)
            if endereco_viacep:
                partes = [p.strip() for p in endereco_viacep.split(",")]
                if len(partes) >= 3:
                    bairro_cidade = ", ".join(partes[1:])
                    self.logger.debug("Tentando geocodificação aproximada (bairro): %s", bairro_cidade)
                    coords = self.geocodificar_nominatim(bairro_cidade)
                    if coords and self.validar_coords_goias(coords):
                        self.logger.info("⚠️ Usando localização APROXIMADA do bairro")
                        return {
                            "coords": coords,
                            "aproximado": True,
                            "nivel_aproximacao": "bairro",
                            "aviso": "Distância aproximada - endereço fora da área de mapeamento",
                        }

                if len(partes) >= 2:
                    cidade_uf = ", ".join(partes[-2:])
                    self.logger.debug("Tentando geocodificação aproximada (cidade): %s", cidade_uf)
                    coords = self.geocodificar_nominatim(cidade_uf)
                    if coords and self.validar_coords_goias(coords):
                        self.logger.info("⚠️ Usando localização APROXIMADA da cidade")
                        return {
                            "coords": coords,
                            "aproximado": True,
                            "nivel_aproximacao": "cidade",
                            "aviso": "Distância muito aproximada - endereço não encontrado",
                        }

        self.logger.debug("Nominatim falhou, tentando OpenRouteService...")

        if not self.api_key:
            return None

        resultado_openroute = geocoding.geocodificar_openroute(
            endereco,
            api_key=self.api_key,
            focus_lat=self.GOIANIA_LAT,
            focus_lon=self.GOIANIA_LON,
            http_client=self.http_client,
            logger=self.logger,
        )
        if not resultado_openroute:
            return None

        coords = resultado_openroute["coords"]
        properties = resultado_openroute.get("properties", {})
        label = properties.get("label", "N/A")
        confidence = properties.get("confidence", 0)
        accuracy = properties.get("accuracy", "N/A")

        if accuracy == "centroid" and confidence < 0.7:
            self.logger.debug("Resultado rejeitado (centroid com baixa confiança)")
            return None

        self.logger.debug("OpenRouteService encontrou:")
        self.logger.debug("  Label: %s", label)
        self.logger.debug("  Confidence: %s", confidence)
        self.logger.debug("  Coordenadas: lon=%s, lat=%s", coords[0], coords[1])

        if not self.validar_coords_goias(coords):
            self.logger.warning("OpenRouteService retornou local FORA de Goiás: %s", label)
            self.logger.warning("Coordenadas rejeitadas: lon=%s, lat=%s", coords[0], coords[1])
            self.logger.warning("O endereço pode estar incorreto ou incompleto")
            return None

        return coords

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
            
            self.logger.debug("Distância Haversine (linha reta): %.2f km", distancia_km)
            self.logger.debug("Duração estimada: %.1f min", duracao_min)
            
            return {
                'distancia_km': round(distancia_km, 2),
                'duracao_min': round(duracao_min, 1),
                'coords_origem': coords_origem,
                'coords_destino': coords_destino,
                'metodo': 'haversine'
            }
        except Exception as e:
            self.logger.error("Erro ao calcular distância Haversine: %s", e)
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
            self.logger.error("Coordenadas de origem ou destino não fornecidas")
            return None
        
        # Validar coordenadas
        if not self._validar_coordenadas(coords_origem):
            self.logger.error("Coordenadas de origem inválidas: %s", coords_origem)
            return None
        
        if not self._validar_coordenadas(coords_destino):
            self.logger.error("Coordenadas de destino inválidas: %s", coords_destino)
            return None
        
        self.logger.debug("========== CALCULANDO DISTÂNCIA ==========")
        self.logger.debug("Origem:  lon=%s, lat=%s", coords_origem[0], coords_origem[1])
        self.logger.debug("Destino: lon=%s, lat=%s", coords_destino[0], coords_destino[1])
        
        # TENTATIVA 1: GraphHopper (preferido)
        self.logger.debug("Tentativa 1: GraphHopper...")
        
        try:
            from app.services.graphhopper import graphhopper_service
            
            # GraphHopper usa (lat, lon), mas recebemos (lon, lat)
            origem_gh = (coords_origem[1], coords_origem[0])  # Converter para (lat, lon)
            destino_gh = (coords_destino[1], coords_destino[0])
            
            resultado_gh = graphhopper_service.calcular_rota(origem_gh, destino_gh)
            
            if resultado_gh:
                self.logger.debug(
                    "✓ Sucesso com GraphHopper: %s km", resultado_gh["distancia_km"]
                )
                # Converter de volta para (lon, lat) para manter compatibilidade
                return {
                    'distancia_km': resultado_gh['distancia_km'],
                    'duracao_min': resultado_gh['duracao_min'],
                    'coords_origem': coords_origem,
                    'coords_destino': coords_destino,
                    'metodo': 'graphhopper'
                }
            else:
                self.logger.debug("✗ GraphHopper retornou None")
        except ImportError as e:
            self.logger.debug("GraphHopper não disponível: %s", e)
        except Exception as e:
            self.logger.debug("✗ GraphHopper falhou: %s: %s", type(e).__name__, e)
            import traceback
            traceback.print_exc()
        
        # TENTATIVA 2: OpenRouteService (fallback)
        self.logger.debug("Tentativa 2: OpenRouteService...")
        
        if not self.api_key:
            self.logger.debug("✗ OPENROUTE_API_KEY não configurada, pulando OpenRouteService")
        else:
            self.logger.debug("Enviando requisição para OpenRouteService...")
            try:
                rota = geocoding.calcular_rota_openroute(
                    coords_origem,
                    coords_destino,
                    api_key=self.api_key,
                    http_client=self.http_client,
                    logger=self.logger,
                )
            except Exception as e:
                self.logger.error(
                    "Erro ao calcular rota com OpenRouteService: %s: %s", type(e).__name__, e
                )
                rota = None

            if rota:
                summary = rota.get("summary", {})
                distancia_metros = summary.get("distance", 0)
                duracao_segundos = summary.get("duration", 0)

                distancia_km = round(distancia_metros / 1000, 2)
                duracao_min = round(duracao_segundos / 60, 0)

                self.logger.debug(
                    "✓ Sucesso com OpenRouteService: %s km, %s min",
                    distancia_km,
                    duracao_min,
                )

                return {
                    "distancia_km": distancia_km,
                    "duracao_min": duracao_min,
                    "coords_origem": coords_origem,
                    "coords_destino": coords_destino,
                    "metodo": "openrouteservice",
                }

            self.logger.debug("✗ OpenRouteService não retornou rotas")
        
        # TENTATIVA 3: Haversine (último recurso - distância em linha reta)
        self.logger.debug("Tentativa 3: Haversine (distância em linha reta)...")
        
        resultado_haversine = self._calcular_distancia_haversine(coords_origem, coords_destino)
        if resultado_haversine:
            self.logger.debug("✓ Usando distância Haversine como último recurso")
            return resultado_haversine
        
        self.logger.error("✗ Todas as tentativas falharam ao calcular distância")
        
        return None
    
    def calcular_distancia_pedido(self, pedido_id=None, rua=None, numero=None, bairro=None, cidade=None, cep=None):
        """
        Calcula a distância da floricultura até o endereço do pedido usando APENAS campos separados.
        
        Args obrigatórios:
            rua: Rua/Logradouro (OBRIGATÓRIO)
            bairro: Bairro (OBRIGATÓRIO)
        
        Args opcionais:
            numero: Número do endereço
            cidade: Cidade (padrão: Goiânia)
            cep: CEP (opcional, mas se fornecido deve ser válido)
            pedido_id: ID do pedido (opcional, para logs)
            
        Returns:
            Dict com distancia_km, duracao_min e coordenadas
            OU Dict com 'error' e 'detalhes' se validação falhar
        """
        self.logger.debug(
            "========== CALCULANDO DISTÂNCIA PEDIDO %s ==========", pedido_id or "?"
        )
        self.logger.debug(
            "Campos recebidos: rua=%s, num=%s, bairro=%s, cidade=%s, cep=%s",
            rua,
            numero,
            bairro,
            cidade,
            cep,
        )
        
        # Validar campos mínimos ANTES de tentar construir endereço
        valido, mensagem_erro = self.validar_campos_endereco(rua=rua, bairro=bairro, cep=cep)
        if not valido:
            self.logger.error("Validação de campos falhou: %s", mensagem_erro)
            return {
                'error': mensagem_erro,
                'detalhes': 'Campos obrigatórios: Rua e Bairro. CEP (se fornecido) deve ter 8 dígitos.',
                'campos_recebidos': {
                    'rua': rua or '',
                    'numero': numero or '',
                    'bairro': bairro or '',
                    'cidade': cidade or '',
                    'cep': cep or ''
                }
            }
        
        # Construir endereço otimizado para geocodificação (apenas campos separados)
        endereco_geocode = self.construir_endereco_para_geocode(
            rua=rua,
            numero=numero,
            bairro=bairro,
            cidade=cidade,
            cep=cep
        )
        
        if not endereco_geocode:
            erro_msg = "Não foi possível construir endereço para geocodificação"
            self.logger.error("%s", erro_msg)
            return {
                'error': erro_msg,
                'detalhes': 'Verifique se os campos Rua e Bairro estão preenchidos corretamente.'
            }
        
        self.logger.debug("Endereço para geocode: %s", endereco_geocode)
        
        # Obter coordenadas da floricultura
        self.logger.debug("Obtendo coordenadas da floricultura...")
        
        origem = self.coords_floricultura
        if not origem:
            erro_msg = "Não foi possível obter coordenadas da floricultura. Verifique se ENDERECO_FLORICULTURA está configurado corretamente no .env"
            self.logger.error("%s", erro_msg)
            self.logger.debug("Endereço configurado: %s", self.endereco_floricultura)
            return {
                'error': erro_msg,
                'detalhes': 'Configure a variável ENDERECO_FLORICULTURA no arquivo .env'
            }
        
        self.logger.debug(
            "✓ Coordenadas da floricultura obtidas: lon=%s, lat=%s", origem[0], origem[1]
        )
        
        # Geocodificar endereço do pedido
        self.logger.debug("Geocodificando endereço do pedido...")
        
        # Passar CEP separado para usar como fallback se endereço completo falhar
        resultado_geocode = self.geocodificar(endereco_geocode, normalizar=False, cep_separado=cep)
        if not resultado_geocode:
            # Marcar como inválido para não tentar novamente
            self.marcar_endereco_invalido(endereco_geocode)
            erro_msg = f"Não foi possível geocodificar o endereço: {endereco_geocode[:80]}..."
            self.logger.error("%s", erro_msg)
            return {
                'error': erro_msg,
                'detalhes': 'As APIs de geocodificação (Nominatim, OpenRouteService) não conseguiram encontrar este endereço. Verifique se Rua, Bairro e Cidade estão corretos.',
                'endereco_tentado': endereco_geocode
            }
        
        # Extrair coordenadas e flags de aproximação
        aproximado = False
        nivel_aproximacao = 'exato'
        aviso_aproximacao = None
        
        if isinstance(resultado_geocode, dict):
            # Retorno com flags de aproximação
            destino = resultado_geocode['coords']
            aproximado = resultado_geocode.get('aproximado', False)
            nivel_aproximacao = resultado_geocode.get('nivel_aproximacao', 'exato')
            aviso_aproximacao = resultado_geocode.get('aviso')
        else:
            # Retorno normal (tupla)
            destino = resultado_geocode
        
        self.logger.debug(
            "✓ Endereço geocodificado: lon=%s, lat=%s", destino[0], destino[1]
        )
        if aproximado:
            self.logger.info("⚠️ Coordenadas aproximadas (nível: %s)", nivel_aproximacao)
        
        # Calcular distância
        self.logger.debug("Calculando distância entre origem e destino...")
        
        resultado = self.calcular_distancia(origem, destino)
        
        if resultado:
            # Adicionar coordenadas do destino ao resultado (para salvar no banco)
            resultado['coords_destino_lat'] = destino[1]  # latitude
            resultado['coords_destino_lon'] = destino[0]  # longitude
            
            # Adicionar flags de aproximação
            resultado['aproximado'] = aproximado
            resultado['nivel_aproximacao'] = nivel_aproximacao
            if aviso_aproximacao:
                resultado['aviso'] = aviso_aproximacao
            
            metodo = resultado.get('metodo', 'desconhecido')
            self.logger.debug(
                "✓ Pedido %s: %s km (método: %s, aproximado: %s)",
                pedido_id or "?",
                resultado['distancia_km'],
                metodo,
                aproximado,
            )
            return resultado
        else:
            erro_msg = "Falha no cálculo de rota. Todas as tentativas (GraphHopper, OpenRouteService, Haversine) falharam."
            self.logger.error("✗ Pedido %s: %s", pedido_id or "?", erro_msg)
            self.logger.debug("Origem: %s", origem)
            self.logger.debug("Destino: %s", destino)
            return {
                'error': erro_msg,
                'detalhes': 'As APIs de cálculo de rota não estão respondendo ou a rota não pôde ser calculada.',
                'coords_origem': origem,
                'coords_destino': destino
            }
    
    def calcular_distancias_lote(self, pedidos):
        """
        Calcula distâncias para múltiplos pedidos usando campos separados
        
        Args:
            pedidos: Lista de dicts com 'id', 'rua', 'numero', 'bairro', 'cidade', 'cep'
            
        Returns:
            Dict com id do pedido como chave e resultado (distância ou erro) como valor
        """
        resultados = {}
        
        for pedido in pedidos:
            pedido_id = pedido.get('id')
            rua = pedido.get('rua', '')
            numero = pedido.get('numero', '')
            bairro = pedido.get('bairro', '')
            cidade = pedido.get('cidade', '')
            cep = pedido.get('cep', '')
            
            # Validar campos mínimos
            if not rua or not bairro:
                resultados[pedido_id] = {
                    'error': 'Campos obrigatórios ausentes',
                    'detalhes': 'Rua e Bairro são obrigatórios para calcular distância'
                }
                continue
            
            resultado = self.calcular_distancia_pedido(
                pedido_id=pedido_id,
                rua=rua,
                numero=numero,
                bairro=bairro,
                cidade=cidade,
                cep=cep
            )
            resultados[pedido_id] = resultado
        
        return resultados


# Instância global do serviço
distancia_service = DistanciaService()
