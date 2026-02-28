# -*- coding: utf-8 -*-
"""
Serviço de Cálculo de Distância

Geocodifica endereços e calcula distância de rota (dirigindo).
Provider primário: Google Geocoding API (com cache em EnderecoCliente).
Fallback:          Nominatim (OpenStreetMap) + OpenRouteService.
"""
import os
import re

import requests


class DistanciaService:
    """Serviço para cálculo de distância com Google Geocoding + cache."""

    # URLs das APIs (fallback)
    GEOCODE_URL = "https://api.openrouteservice.org/geocode/search"
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"
    VIACEP_URL = "https://viacep.com.br/ws"

    # Cache de endereços que falharam (evita requisições repetidas)
    _enderecos_invalidos = set()

    # Coordenadas centrais de Goiânia para focus.point
    GOIANIA_LAT = -16.6869
    GOIANIA_LON = -49.2648

    # Debug mode - ativar logs detalhados
    DEBUG = True

    def __init__(self):
        self.api_key = os.environ.get("OPENROUTE_API_KEY", "")
        self.endereco_floricultura = os.environ.get("ENDERECO_FLORICULTURA", "")
        self._coords_floricultura = None

        if self.endereco_floricultura and self.DEBUG:
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
            r"\d+",  # Contém número
            r"rua|av\.|avenida|alameda|praça|travessa|rod\.|rodovia",  # Tipo de logradouro
            r"bairro|setor|centro|jardim|parque|vila",  # Tipo de região
            r"\d{5}-?\d{3}",  # CEP
        ]

        endereco_lower = endereco.lower()
        tem_padrao_valido = any(re.search(padrao, endereco_lower) for padrao in padroes_validos)

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
        cep_limpo = re.sub(r"\D", "", str(cep))

        if len(cep_limpo) != 8:
            if self.DEBUG:
                print(f"[DEBUG] CEP inválido (deve ter 8 dígitos): {cep}")
            return None

        try:
            url = f"{self.VIACEP_URL}/{cep_limpo}/json/"

            if self.DEBUG:
                print(f"[DEBUG] Consultando ViaCEP: {url}")

            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # ViaCEP retorna {"erro": true} quando CEP não existe
                if "erro" in data and data["erro"]:
                    if self.DEBUG:
                        print(f"[DEBUG] ViaCEP: CEP {cep_limpo} não encontrado")
                    return None

                # Extrair dados do endereço
                logradouro = data.get("logradouro", "")
                bairro = data.get("bairro", "")
                localidade = data.get("localidade", "")  # Cidade
                uf = data.get("uf", "")

                if self.DEBUG:
                    print("[DEBUG] ViaCEP encontrou:")
                    print(f"[DEBUG]   Logradouro: {logradouro}")
                    print(f"[DEBUG]   Bairro: {bairro}")
                    print(f"[DEBUG]   Cidade: {localidade}/{uf}")

                # Montar endereço formatado
                partes = []
                if logradouro:
                    partes.append(logradouro)
                if bairro:
                    partes.append(bairro)
                if localidade:
                    partes.append(localidade)
                if uf:
                    partes.append(uf)
                partes.append("Brasil")

                endereco_formatado = ", ".join(partes)

                if self.DEBUG:
                    print(f"[DEBUG] ✓ Endereço do CEP: {endereco_formatado}")

                return endereco_formatado
            else:
                if self.DEBUG:
                    print(f"[DEBUG] ViaCEP erro HTTP: {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            print(f"[ERRO] ViaCEP timeout para CEP: {cep_limpo}")
            return None
        except Exception as e:
            if self.DEBUG:
                print(f"[ERRO] Erro ao consultar ViaCEP: {e}")
            return None

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
            if self.DEBUG:
                print(f"[ALERTA] Latitude {lat} está FORA de Goiás (esperado: -19.5 a -12.5)")
            return False

        if not (-53.5 <= lon <= -45.5):
            if self.DEBUG:
                print(f"[ALERTA] Longitude {lon} está FORA de Goiás (esperado: -53.5 a -45.5)")
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
            cep_limpo = re.sub(r"\D", "", cep)
            if len(cep_limpo) != 8:
                return False, f"CEP inválido: deve ter 8 dígitos (recebido: '{cep}')"

        return True, ""

    @property
    def coords_floricultura(self):
        """Retorna coordenadas da floricultura (com cache)"""
        if self._coords_floricultura is None and self.endereco_floricultura:
            print("\n[DEBUG] ========== GEOCODIFICANDO FLORICULTURA ==========")
            print(f"[DEBUG] Endereço configurado: {self.endereco_floricultura}")

            # Melhorar formatação do endereço da floricultura que vem do .env
            # Ex: "Rua 132,289,Setor Sul,Goiânia,GO,74093-210" -> "Rua 132, 289, Setor Sul, Goiânia, GO, 74093-210"
            endereco_formatado = self.endereco_floricultura

            # Adicionar espaço após vírgulas (mas não dentro de CEPs)
            if "," in endereco_formatado and ", " not in endereco_formatado:
                # Proteger CEPs antes
                import re

                cep_pattern = r"(\d{5})-(\d{3})"
                ceps_encontrados = re.findall(cep_pattern, endereco_formatado)
                endereco_temp = re.sub(cep_pattern, "__CEP__", endereco_formatado)

                # Adicionar espaço após vírgulas
                endereco_temp = re.sub(r",(?!\s)", ", ", endereco_temp)

                # Restaurar CEPs
                for cep_parte1, cep_parte2 in ceps_encontrados:
                    endereco_temp = endereco_temp.replace(
                        "__CEP__", f"{cep_parte1}-{cep_parte2}", 1
                    )

                endereco_formatado = endereco_temp
                print(f"[DEBUG] Endereço formatado: {endereco_formatado}")

            # Limpar o endereço
            endereco_limpo = self.limpar_endereco(endereco_formatado)
            print(f"[DEBUG] Endereço limpo para geocode: {endereco_limpo}")

            resultado_geocode = self.geocodificar(endereco_limpo, normalizar=False)

            # Extrair coordenadas (pode ser tupla ou dict)
            if isinstance(resultado_geocode, dict):
                self._coords_floricultura = resultado_geocode["coords"]
            else:
                self._coords_floricultura = resultado_geocode

            if self._coords_floricultura:
                print(
                    f"[DEBUG] ✓ Coordenadas da floricultura: lon={self._coords_floricultura[0]}, lat={self._coords_floricultura[1]}"
                )
            else:
                print("[ERRO] ✗ Falha ao geocodificar endereço da floricultura!")
        return self._coords_floricultura

    def construir_endereco_para_geocode(
        self, rua=None, numero=None, bairro=None, cidade=None, cep=None
    ):
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
            if self.DEBUG:
                print(f"[DEBUG] Validação falhou: {mensagem_erro}")
            return None

        # Construir endereço limpo apenas com campos separados
        partes = []

        # Rua (obrigatória, já validada)
        rua_limpa = rua.strip()
        partes.append(rua_limpa)

        # Número (opcional)
        if numero and numero.strip():
            numero_limpo = re.split(r"[,\s]+", numero.strip())[0]
            # Ignorar número "0" ou "S/N" (sem número)
            if numero_limpo and numero_limpo not in ["0", "s/n", "sn", "S/N", "SN"]:
                partes.append(numero_limpo)

        # Bairro (obrigatório, já validado)
        partes.append(bairro.strip())

        # Cidade (padrão: Goiânia)
        cidade_final = cidade.strip() if cidade and cidade.strip() else "Goiânia"
        partes.append(cidade_final)

        # Estado e País
        partes.append("GO")
        partes.append("Brasil")

        # Formato final: "Rua X, Número, Bairro, Cidade, GO, Brasil"
        endereco_geocode = ", ".join(partes)

        if self.DEBUG:
            print(f"[DEBUG] Endereço construído dos campos separados: {endereco_geocode}")

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
        cep_pattern = r"(\d{5})-(\d{3})"
        ceps_encontrados = re.findall(cep_pattern, endereco)
        # Substituir temporariamente CEPs por placeholder
        endereco_temp = re.sub(cep_pattern, "__CEP__", endereco)

        # Substituir múltiplos hífens/vírgulas por vírgula simples (mas não em CEPs)
        endereco_temp = re.sub(r"\s*-\s*", ", ", endereco_temp)  # "0 -Capuava" -> "0, Capuava"
        endereco_temp = re.sub(r",\s*,+", ", ", endereco_temp)  # Remover vírgulas duplicadas

        # Restaurar CEPs
        for cep_parte1, cep_parte2 in ceps_encontrados:
            endereco_temp = endereco_temp.replace("__CEP__", f"{cep_parte1}-{cep_parte2}", 1)

        endereco = endereco_temp

        # Remover número "0" no início (geralmente significa sem número)
        endereco = re.sub(r",\s*0\s*,", ", ", endereco)  # ", 0," -> ", "
        endereco = re.sub(r",\s*0\s+-", ", ", endereco)  # ", 0 -" -> ", "

        # Remover complementos que confundem geocodificação
        complementos_remover = [
            r"\bresidencial\s+\w+\b",  # Residencial Privê, Residencial X
            r"\bcondomínio\s+\w+\b",  # Condomínio X
            r"\bedifício\s+\w+\b",  # Edifício X
            r"\bprédio\s+\w+\b",  # Prédio X
            r"\btorre\s+\w+\b",  # Torre X
        ]

        for padrao in complementos_remover:
            endereco = re.sub(padrao, "", endereco, flags=re.IGNORECASE)

        # Remover padrões que confundem a geocodificação
        # QD (quadra), LT (lote), BL (bloco), AP (apartamento), etc
        padroes_remover = [
            r"\bQD\s*\d+\b",  # QD 54
            r"\bLT\s*\d+\b",  # LT 6
            r"\bBL\s*\d+\b",  # BL 3
            r"\bAP\s*\d+\b",  # AP 101
            r"\bLOTE\s*\d+\b",  # LOTE 6
            r"\bQUADRA\s*\d+\b",  # QUADRA 54
            r"\bBLOCO\s*\d+\b",  # BLOCO 3
            r"\b0\s+\d+\b",  # 0 14 (número estranho)
            r"\bN[°º]?\s*\d+\b",  # Nº 123, N 123
        ]

        for padrao in padroes_remover:
            endereco = re.sub(padrao, "", endereco, flags=re.IGNORECASE)

        # Limpar separadores duplicados e espaços extras
        endereco = re.sub(r",\s*,+", ", ", endereco)  # Vírgulas duplicadas
        endereco = re.sub(r"\s+", " ", endereco)  # Espaços múltiplos
        endereco = endereco.strip(" -,")  # Remover no início/fim

        # Garantir que tem cidade/estado
        endereco_lower = endereco.lower()
        cidades_go = [
            "goiânia",
            "goiania",
            "aparecida",
            "anápolis",
            "anapolis",
            "trindade",
            "senador canedo",
        ]

        tem_cidade = any(cidade in endereco_lower for cidade in cidades_go)
        if not tem_cidade:
            endereco = f"{endereco}, Goiânia, GO, Brasil"
        elif "brasil" not in endereco_lower:
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
                "User-Agent": "PlanteumaFlor-GestorPedidos/1.0 (contato@planteumaflor.com.br)",
                "Accept": "application/json",
                "Accept-Language": "pt-BR,pt;q=0.9",
            }

            params = {
                "q": endereco,
                "format": "json",
                "limit": 1,
                "countrycodes": "br",
                "addressdetails": 1,
            }

            if self.DEBUG:
                print(f"[DEBUG] Nominatim request: {self.NOMINATIM_URL}")
                print(f"[DEBUG] Params: {params}")

            response = requests.get(self.NOMINATIM_URL, headers=headers, params=params, timeout=15)

            if self.DEBUG:
                print(f"[DEBUG] Nominatim status: {response.status_code}")

            if response.status_code == 200:
                results = response.json()

                if self.DEBUG:
                    print(f"[DEBUG] Nominatim resultados: {len(results)}")

                if results and len(results) > 0:
                    result = results[0]
                    lat = float(result["lat"])
                    lon = float(result["lon"])
                    display_name = result.get("display_name", "N/A")

                    if self.DEBUG:
                        print("[DEBUG] Nominatim encontrou:")
                        print(f"[DEBUG]   Display: {display_name[:100]}...")
                        print(f"[DEBUG]   Coordenadas: lon={lon}, lat={lat}")

                    # Validar se coordenadas estão em Goiás
                    coords = (lon, lat)
                    if not self.validar_coords_goias(coords):
                        print(f"[ALERTA] Nominatim retornou local FORA de Goiás: {display_name}")
                        print(f"[ALERTA] Coordenadas rejeitadas: lon={lon}, lat={lat}")
                        return None

                    return coords
                else:
                    if self.DEBUG:
                        print(f"[DEBUG] Nominatim: nenhum resultado para '{endereco}'")
            else:
                if self.DEBUG:
                    print(
                        f"[DEBUG] Nominatim erro HTTP: {response.status_code} - {response.text[:200]}"
                    )

        except requests.exceptions.Timeout:
            print(f"[ERRO] Nominatim timeout para: {endereco}")
        except requests.exceptions.ConnectionError as e:
            print(f"[ERRO] Nominatim conexão falhou: {e}")
        except Exception as e:
            print(f"[ERRO] Nominatim erro: {e}")

        return None

    def geocodificar(self, endereco, normalizar=True, cep_separado=None):
        """
        Converte endereço em coordenadas (latitude, longitude).

        Ordem de tentativas:
          1) Google Geocoding API (provider primário)
          2) Nominatim (OpenStreetMap) com variações
          3) ViaCEP + Nominatim (por CEP)
          4) OpenRouteService (fallback)

        Args:
            endereco: String com o endereço completo
            normalizar: Se True, adiciona cidade/estado se não presente
            cep_separado: CEP fornecido separadamente (usado como fallback)

        Returns:
            Tuple (longitude, latitude) para endereços exatos
            OU Dict {'coords': (lon, lat), 'aproximado': True, ...}
            OU None se falhar
        """
        if not endereco:
            return None

        endereco_original = endereco
        if normalizar:
            endereco = self.normalizar_endereco(endereco)

        if self.DEBUG:
            print("\n[DEBUG] --- Geocodificando ---")
            print(f"[DEBUG] Endereço original: {endereco_original}")
            print(f"[DEBUG] Endereço para API: {endereco}")

        # -----------------------------------------------------------------
        # TENTATIVA 0: Google Geocoding API (provider primário)
        # -----------------------------------------------------------------
        result = self._geocodificar_google(endereco)
        if result:
            if self.DEBUG:
                print("[DEBUG] ✓ Geocodificação via Google (provider primário)")
            return result

        # -----------------------------------------------------------------
        # TENTATIVA 1: Nominatim com variações (fallback)
        # -----------------------------------------------------------------
        if self.DEBUG:
            print("[DEBUG] ⚠ Google falhou/indisponível → fallback Nominatim")

        coords = self.geocodificar_nominatim(endereco)
        if coords and self.validar_coords_goias(coords):
            if self.DEBUG:
                print("[DEBUG] ✓ Geocodificação via Nominatim (fallback 1)")
            return coords

        # Sem número
        if "," in endereco:
            partes = [p.strip() for p in endereco.split(",")]
            if len(partes) >= 3:
                endereco_sem_numero = ", ".join([partes[0]] + partes[2:])
                if self.DEBUG:
                    print(f"[DEBUG] Tentando sem número: {endereco_sem_numero}")
                coords = self.geocodificar_nominatim(endereco_sem_numero)
                if coords and self.validar_coords_goias(coords):
                    return coords

        # Simplificado (rua + bairro + cidade)
        if "," in endereco:
            partes = [p.strip() for p in endereco.split(",")]
            if len(partes) >= 4:
                endereco_simplificado = ", ".join([partes[0], partes[2], partes[3], "GO", "Brasil"])
                if self.DEBUG:
                    print(f"[DEBUG] Tentando simplificado: {endereco_simplificado}")
                coords = self.geocodificar_nominatim(endereco_simplificado)
                if coords and self.validar_coords_goias(coords):
                    return coords

        # -----------------------------------------------------------------
        # TENTATIVA 2: ViaCEP + Nominatim (por CEP)
        # -----------------------------------------------------------------
        cep = None
        cep_match = re.search(r"(\d{5})-?(\d{3})", endereco)
        if cep_match:
            cep = f"{cep_match.group(1)}{cep_match.group(2)}"
        elif cep_separado:
            cep = re.sub(r"\D", "", str(cep_separado))

        if cep and len(cep) == 8:
            if self.DEBUG:
                print("[DEBUG] Tentando ViaCEP...")
            endereco_viacep = self.buscar_endereco_por_cep(cep)
            if endereco_viacep:
                coords = self.geocodificar_nominatim(endereco_viacep)
                if coords and self.validar_coords_goias(coords):
                    print("[INFO] ✓ Endereço encontrado via ViaCEP + Nominatim")
                    return coords

            cep_formatado = f"{cep[:5]}-{cep[5:]}"
            coords = self.geocodificar_nominatim(f"{cep_formatado}, Brasil")
            if coords and self.validar_coords_goias(coords):
                print(f"[INFO] ✓ Endereço encontrado usando apenas CEP: {cep_formatado}")
                return coords

        # Geocodificação aproximada por bairro/cidade
        if cep_separado:
            endereco_viacep = self.buscar_endereco_por_cep(cep_separado)
            if endereco_viacep:
                partes = [p.strip() for p in endereco_viacep.split(",")]
                if len(partes) >= 3:
                    bairro_cidade = ", ".join(partes[1:])
                    coords = self.geocodificar_nominatim(bairro_cidade)
                    if coords and self.validar_coords_goias(coords):
                        return {
                            "coords": coords,
                            "aproximado": True,
                            "nivel_aproximacao": "bairro",
                            "aviso": "Distância aproximada - endereço fora da área de mapeamento",
                        }
                if len(partes) >= 2:
                    cidade_uf = ", ".join(partes[-2:])
                    coords = self.geocodificar_nominatim(cidade_uf)
                    if coords and self.validar_coords_goias(coords):
                        return {
                            "coords": coords,
                            "aproximado": True,
                            "nivel_aproximacao": "cidade",
                            "aviso": "Distância muito aproximada - endereço não encontrado",
                        }

        # -----------------------------------------------------------------
        # TENTATIVA 3: OpenRouteService (fallback final de geocoding)
        # -----------------------------------------------------------------
        if self.DEBUG:
            print("[DEBUG] ⚠ Nominatim/ViaCEP falharam → fallback OpenRouteService")
        if not self.api_key:
            return None

        try:
            headers = {
                "Authorization": self.api_key,
                "Content-Type": "application/json",
            }
            params = {
                "api_key": self.api_key,
                "text": endereco,
                "boundary.country": "BR",
                "size": 1,
                "focus.point.lat": self.GOIANIA_LAT,
                "focus.point.lon": self.GOIANIA_LON,
            }
            response = requests.get(self.GEOCODE_URL, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                features = data.get("features", [])
                if features:
                    feature = features[0]
                    coords = feature["geometry"]["coordinates"]
                    properties = feature.get("properties", {})
                    accuracy = properties.get("accuracy", "N/A")
                    confidence = properties.get("confidence", 0)
                    if accuracy == "centroid" and confidence < 0.7:
                        return None
                    coords_tupla = (coords[0], coords[1])
                    if self.validar_coords_goias(coords_tupla):
                        if self.DEBUG:
                            print("[DEBUG] ✓ Geocodificação via OpenRouteService (fallback final)")
                        return coords_tupla
        except requests.exceptions.Timeout:
            print(f"[ERRO] Timeout ao geocodificar (ORS): {endereco[:60]}")
        except Exception as e:
            print(f"[ERRO] Erro ao geocodificar (ORS): {e}")

        return None

    # ------------------------------------------------------------------
    # Google Geocoding (provider primário)
    # ------------------------------------------------------------------

    def _geocodificar_google(self, endereco):
        """
        Tenta geocodificar via Google Geocoding API.
        Retorna tuple (lon, lat) ou None.
        """
        try:
            from app.services.google_geocoding import google_geocoding_service

            result = google_geocoding_service.geocode(endereco)
            if result:
                lat = result["lat"]
                lng = result["lng"]
                if self.DEBUG:
                    print(f"[DEBUG] ✓ Google Geocoding: lat={lat}, lng={lng}")
                # Retornar no formato (lon, lat) para manter compatibilidade
                return (lng, lat)
        except ImportError:
            if self.DEBUG:
                print("[DEBUG] google_geocoding_service não disponível")
        except Exception as e:
            if self.DEBUG:
                print(f"[DEBUG] Google Geocoding falhou: {e}")
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

        if not self._validar_coordenadas(coords_origem) or not self._validar_coordenadas(
            coords_destino
        ):
            return None

        try:
            lat1, lon1 = math.radians(coords_origem[1]), math.radians(coords_origem[0])
            lat2, lon2 = math.radians(coords_destino[1]), math.radians(coords_destino[0])

            # Raio da Terra em km
            R = 6371.0

            dlat = lat2 - lat1
            dlon = lon2 - lon1

            a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
            c = 2 * math.asin(math.sqrt(a))

            distancia_km = R * c

            # Estimar duração: média de 40 km/h em cidade
            duracao_min = (distancia_km / 40) * 60

            if self.DEBUG:
                print(f"[DEBUG] Distância Haversine (linha reta): {distancia_km:.2f} km")
                print(f"[DEBUG] Duração estimada: {duracao_min:.1f} min")

            return {
                "distancia_km": round(distancia_km, 2),
                "duracao_min": round(duracao_min, 1),
                "coords_origem": coords_origem,
                "coords_destino": coords_destino,
                "metodo": "haversine",
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
            print("\n[DEBUG] ========== CALCULANDO DISTÂNCIA ==========")
            print(f"[DEBUG] Origem:  lon={coords_origem[0]}, lat={coords_origem[1]}")
            print(f"[DEBUG] Destino: lon={coords_destino[0]}, lat={coords_destino[1]}")

        # TENTATIVA 1: Google Directions API (primário)
        if self.DEBUG:
            print("[DEBUG] Tentativa 1: Google Directions...")

        try:
            from app.services.google_routes import google_routes_service

            # Google usa (lat, lon), mas recebemos (lon, lat)
            origem_g = (coords_origem[1], coords_origem[0])
            destino_g = (coords_destino[1], coords_destino[0])

            resultado_g = google_routes_service.calcular_rota(origem_g, destino_g)

            if resultado_g:
                if self.DEBUG:
                    print(f"[DEBUG] ✓ Sucesso com Google Directions: {resultado_g['distancia_km']} km")
                return {
                    "distancia_km": resultado_g["distancia_km"],
                    "duracao_min": resultado_g["duracao_min"],
                    "coords_origem": coords_origem,
                    "coords_destino": coords_destino,
                    "metodo": "google_directions",
                }
            else:
                if self.DEBUG:
                    print("[DEBUG] ✗ Google Directions retornou None")
        except ImportError as e:
            if self.DEBUG:
                print(f"[DEBUG] Google Routes não disponível: {e}")
        except Exception as e:
            if self.DEBUG:
                print(f"[DEBUG] ✗ Google Directions falhou: {type(e).__name__}: {e}")

        # TENTATIVA 2: GraphHopper (fallback)
        if self.DEBUG:
            print("[DEBUG] Tentativa 2: GraphHopper...")

        try:
            from app.services.graphhopper import graphhopper_service

            origem_gh = (coords_origem[1], coords_origem[0])
            destino_gh = (coords_destino[1], coords_destino[0])

            resultado_gh = graphhopper_service.calcular_rota(origem_gh, destino_gh)

            if resultado_gh:
                if self.DEBUG:
                    print(f"[DEBUG] ✓ Sucesso com GraphHopper: {resultado_gh['distancia_km']} km")
                return {
                    "distancia_km": resultado_gh["distancia_km"],
                    "duracao_min": resultado_gh["duracao_min"],
                    "coords_origem": coords_origem,
                    "coords_destino": coords_destino,
                    "metodo": "graphhopper",
                }
            else:
                if self.DEBUG:
                    print("[DEBUG] ✗ GraphHopper retornou None")
        except ImportError as e:
            if self.DEBUG:
                print(f"[DEBUG] GraphHopper não disponível: {e}")
        except Exception as e:
            if self.DEBUG:
                print(f"[DEBUG] ✗ GraphHopper falhou: {type(e).__name__}: {e}")

        # TENTATIVA 3: OpenRouteService (fallback)
        if self.DEBUG:
            print("[DEBUG] Tentativa 2: OpenRouteService...")

        if not self.api_key:
            # OPENROUTE_API_KEY é opcional - usar fallback silenciosamente
            pass
        else:
            try:
                headers = {
                    "Authorization": self.api_key,
                    "Content-Type": "application/json",
                }

                body = {
                    "coordinates": [
                        list(coords_origem),  # [longitude, latitude]
                        list(coords_destino),
                    ]
                }

                if self.DEBUG:
                    print("[DEBUG] Enviando requisição para OpenRouteService...")

                response = requests.post(
                    self.DIRECTIONS_URL, headers=headers, json=body, timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    routes = data.get("routes", [])

                    if routes:
                        summary = routes[0].get("summary", {})
                        distancia_metros = summary.get("distance", 0)
                        duracao_segundos = summary.get("duration", 0)

                        distancia_km = round(distancia_metros / 1000, 2)
                        duracao_min = round(duracao_segundos / 60, 0)

                        if self.DEBUG:
                            print(
                                f"[DEBUG] ✓ Sucesso com OpenRouteService: {distancia_km} km, {duracao_min} min"
                            )

                        return {
                            "distancia_km": distancia_km,
                            "duracao_min": duracao_min,
                            "coords_origem": coords_origem,
                            "coords_destino": coords_destino,
                            "metodo": "openrouteservice",
                        }
                    else:
                        if self.DEBUG:
                            print("[DEBUG] ✗ OpenRouteService não retornou rotas")
                else:
                    if self.DEBUG:
                        print(
                            f"[ERRO] OpenRouteService retornou status {response.status_code}: {response.text[:200]}"
                        )

            except requests.exceptions.Timeout:
                if self.DEBUG:
                    print("[ERRO] Timeout ao calcular rota com OpenRouteService")
            except Exception as e:
                if self.DEBUG:
                    print(
                        f"[ERRO] Erro ao calcular rota com OpenRouteService: {type(e).__name__}: {e}"
                    )
                    import traceback

                    traceback.print_exc()

        # TENTATIVA 4: Haversine (último recurso - distância em linha reta)
        if self.DEBUG:
            print("[DEBUG] Tentativa 4: Haversine (distância em linha reta)...")

        resultado_haversine = self._calcular_distancia_haversine(coords_origem, coords_destino)
        if resultado_haversine:
            if self.DEBUG:
                print("[DEBUG] ✓ Usando distância Haversine como último recurso")
            return resultado_haversine

        if self.DEBUG:
            print("[ERRO] ✗ Todas as tentativas falharam ao calcular distância")

        return None

    def calcular_distancia_pedido(
        self,
        pedido_id=None,
        rua=None,
        numero=None,
        bairro=None,
        cidade=None,
        cep=None,
        cliente_id=None,
    ):
        """
        Calcula a distância da floricultura até o endereço do pedido.

        Fluxo:
          1) Checar cache em EnderecoCliente (via address_hash).
          2) Se cache miss → geocodificar (Google → Nominatim → ORS).
          3) Salvar resultado de volta no EnderecoCliente (se houver cliente_id).
          4) Calcular distância rota (GraphHopper → ORS → Haversine).

        Args obrigatórios:
            rua, bairro

        Args opcionais:
            numero, cidade, cep, pedido_id, cliente_id

        Returns:
            Dict com distancia_km, duracao_min e coordenadas
            OU Dict com 'error' e 'detalhes' se validação falhar
        """
        print(f"\n[DEBUG] ========== CALCULANDO DISTÂNCIA PEDIDO {pedido_id or '?'} ==========")
        print(
            f"[DEBUG] Campos: rua={rua}, num={numero}, bairro={bairro}, "
            f"cidade={cidade}, cep={cep}, cliente_id={cliente_id}"
        )

        # Validar campos mínimos
        valido, mensagem_erro = self.validar_campos_endereco(rua=rua, bairro=bairro, cep=cep)
        if not valido:
            print(f"[ERRO] Validação de campos falhou: {mensagem_erro}")
            return {
                "error": mensagem_erro,
                "detalhes": "Campos obrigatórios: Rua e Bairro. CEP (se fornecido) deve ter 8 dígitos.",
                "campos_recebidos": {
                    "rua": rua or "",
                    "numero": numero or "",
                    "bairro": bairro or "",
                    "cidade": cidade or "",
                    "cep": cep or "",
                },
            }

        # Construir endereço para geocode
        endereco_geocode = self.construir_endereco_para_geocode(
            rua=rua, numero=numero, bairro=bairro, cidade=cidade, cep=cep
        )
        if not endereco_geocode:
            return {
                "error": "Não foi possível construir endereço para geocodificação",
                "detalhes": "Verifique se os campos Rua e Bairro estão preenchidos corretamente.",
            }

        # ----- Cache check via EnderecoCliente -----
        cached = self._check_endereco_cache(
            cliente_id,
            rua=rua,
            numero=numero,
            bairro=bairro,
            cidade=cidade,
            cep=cep,
        )
        destino = None
        aproximado = False
        nivel_aproximacao = "exato"
        aviso_aproximacao = None
        confidence_status = None

        if cached:
            destino = (cached["lng"], cached["lat"])  # (lon, lat)
            confidence_status = cached.get("confidence_status")
            if self.DEBUG:
                print(
                    f"[DEBUG] ✓ Cache hit EnderecoCliente: lon={destino[0]}, lat={destino[1]}, "
                    f"confidence={confidence_status}"
                )

        # ----- Geocodificar se cache miss -----
        if not destino:
            # Obter coordenadas via geocodificação
            resultado_geocode = self.geocodificar(
                endereco_geocode, normalizar=False, cep_separado=cep
            )
            if not resultado_geocode:
                self.marcar_endereco_invalido(endereco_geocode)
                return {
                    "error": f"Não foi possível geocodificar: {endereco_geocode[:80]}...",
                    "detalhes": "Verifique se Rua, Bairro e Cidade estão corretos.",
                    "endereco_tentado": endereco_geocode,
                }

            if isinstance(resultado_geocode, dict):
                destino = resultado_geocode["coords"]
                aproximado = resultado_geocode.get("aproximado", False)
                nivel_aproximacao = resultado_geocode.get("nivel_aproximacao", "exato")
                aviso_aproximacao = resultado_geocode.get("aviso")
            else:
                destino = resultado_geocode

            # ----- Salvar no cache EnderecoCliente -----
            self._save_endereco_cache(
                cliente_id,
                lat=destino[1],
                lng=destino[0],
                rua=rua,
                numero=numero,
                bairro=bairro,
                cidade=cidade,
                cep=cep,
            )

        if self.DEBUG:
            print(f"[DEBUG] ✓ Endereço geocodificado: lon={destino[0]}, lat={destino[1]}")

        # ----- Obter coordenadas da floricultura -----
        origem = self.coords_floricultura
        if not origem:
            return {
                "error": "Não foi possível obter coordenadas da floricultura.",
                "detalhes": "Configure ENDERECO_FLORICULTURA no .env",
            }

        # ----- Calcular distância -----
        resultado = self.calcular_distancia(origem, destino)

        if resultado:
            resultado["coords_destino_lat"] = destino[1]
            resultado["coords_destino_lon"] = destino[0]
            resultado["aproximado"] = aproximado
            resultado["nivel_aproximacao"] = nivel_aproximacao
            resultado["confidence_status"] = confidence_status
            if aviso_aproximacao:
                resultado["aviso"] = aviso_aproximacao
            metodo = resultado.get("metodo", "desconhecido")
            print(
                f"[DEBUG] ✓ Pedido {pedido_id or '?'}: {resultado['distancia_km']} km "
                f"(método: {metodo}, aproximado: {aproximado})"
            )
            return resultado

        return {
            "error": "Falha no cálculo de rota (GraphHopper/ORS/Haversine).",
            "detalhes": "As APIs de rota não responderam.",
            "coords_origem": origem,
            "coords_destino": destino,
        }

    # ------------------------------------------------------------------
    # EnderecoCliente cache helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_endereco_cache(cliente_id, **addr_fields):
        """Busca coordenadas cacheadas no EnderecoCliente via address_hash."""
        if not cliente_id:
            return None
        try:
            from app.models.endereco_cliente import EnderecoCliente

            # Construir canonical e hash para comparação
            ec_dummy = EnderecoCliente(
                rua=addr_fields.get("rua"),
                numero=addr_fields.get("numero"),
                bairro=addr_fields.get("bairro"),
                cidade=addr_fields.get("cidade"),
                cep=addr_fields.get("cep"),
            )
            target_hash = ec_dummy.compute_address_hash()

            # Buscar endereço cacheado com mesmo hash e coordenadas
            cached = (
                EnderecoCliente.query.filter_by(cliente_id=cliente_id, address_hash=target_hash)
                .filter(EnderecoCliente.lat.isnot(None))
                .first()
            )
            if cached:
                return {
                    "lat": cached.lat,
                    "lng": cached.lng,
                    "confidence_status": cached.confidence_status,
                }
        except Exception as e:
            print(f"[DEBUG] Cache check falhou: {e}")
            try:
                from app import db
                db.session.rollback()
            except Exception:
                pass
        return None

    @staticmethod
    def _save_endereco_cache(cliente_id, lat, lng, **addr_fields):
        """Salva resultado de geocodificação no EnderecoCliente (se cliente_id)."""
        if not cliente_id or lat is None or lng is None:
            return
        try:
            from app import db
            from app.models.endereco_cliente import EnderecoCliente
            from app.services.google_geocoding import GoogleGeocodingService

            # Encontrar endereço do cliente que melhor combina
            enderecos = EnderecoCliente.query.filter_by(cliente_id=cliente_id).all()

            # Criar hash do endereço atual para comparação
            ec_dummy = EnderecoCliente(
                rua=addr_fields.get("rua"),
                numero=addr_fields.get("numero"),
                bairro=addr_fields.get("bairro"),
                cidade=addr_fields.get("cidade"),
                cep=addr_fields.get("cep"),
            )
            target_hash = ec_dummy.compute_address_hash()

            # Procurar endereço existente para atualizar
            target = None
            for ec in enderecos:
                if ec.address_hash == target_hash:
                    target = ec
                    break
                # Fallback: comparar campos individuais
                if ec.rua == addr_fields.get("rua") and ec.bairro == addr_fields.get("bairro"):
                    target = ec
                    break

            if not target and enderecos:
                # Usar endereço principal ou primeiro
                target = next((e for e in enderecos if e.principal), enderecos[0])

            if target:
                has_numero = bool(addr_fields.get("numero", "").strip())
                has_cep = bool(addr_fields.get("cep", "").strip())
                confidence = GoogleGeocodingService.classify_confidence(
                    location_type="ROOFTOP",  # Google default if we got a result
                    has_numero=has_numero,
                    has_cep=has_cep,
                )
                target.update_geocode_cache(
                    lat=lat,
                    lng=lng,
                    confidence_status=confidence,
                    provider="google",
                )
                db.session.commit()
                print(f"[DEBUG] ✓ Cache salvo em EnderecoCliente #{target.id}")
        except Exception as e:
            print(f"[DEBUG] Cache save falhou: {e}")
            try:
                db.session.rollback()
            except Exception:
                pass

    def calcular_distancias_lote(self, pedidos):
        """
        Calcula distâncias para múltiplos pedidos usando campos separados.

        Args:
            pedidos: Lista de dicts com 'id', 'rua', 'numero', 'bairro', 'cidade', 'cep',
                     e opcionalmente 'cliente_id'

        Returns:
            Dict com id do pedido como chave e resultado (distância ou erro) como valor
        """
        resultados = {}

        for pedido in pedidos:
            pedido_id = pedido.get("id")
            rua = pedido.get("rua", "")
            numero = pedido.get("numero", "")
            bairro = pedido.get("bairro", "")
            cidade = pedido.get("cidade", "")
            cep = pedido.get("cep", "")
            cliente_id = pedido.get("cliente_id")

            if not rua or not bairro:
                resultados[pedido_id] = {
                    "error": "Campos obrigatórios ausentes",
                    "detalhes": "Rua e Bairro são obrigatórios para calcular distância",
                }
                continue

            resultado = self.calcular_distancia_pedido(
                pedido_id=pedido_id,
                rua=rua,
                numero=numero,
                bairro=bairro,
                cidade=cidade,
                cep=cep,
                cliente_id=cliente_id,
            )
            resultados[pedido_id] = resultado

        return resultados


# Instância global do serviço
distancia_service = DistanciaService()
