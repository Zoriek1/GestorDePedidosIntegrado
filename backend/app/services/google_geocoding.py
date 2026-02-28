# -*- coding: utf-8 -*-
"""
Serviço de Geocodificação e Validação de Endereço via Google Maps Platform

Usa:
  - Google Geocoding API (lat/lng + location_type + place_id)
  - Google Address Validation API (verdict + componentes corrigidos)

Requer GOOGLE_MAPS_API_KEY configurada no .env.
"""
import os
from typing import Any, Dict, List, Optional

import requests

# Constantes
GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
ADDRESS_VALIDATION_URL = "https://addressvalidation.googleapis.com/v1:validateAddress"

# Limites de Goiás (para rejeitar resultados fora da área operacional)
GOIAS_LAT_MIN, GOIAS_LAT_MAX = -19.5, -12.5
GOIAS_LON_MIN, GOIAS_LON_MAX = -53.5, -45.5


class GoogleGeocodingService:
    """Geocodificação e validação de endereço via Google Maps Platform."""

    DEBUG = True

    def __init__(self):
        self.api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")

    # ------------------------------------------------------------------
    # Geocoding API
    # ------------------------------------------------------------------

    def geocode(self, address_canonical: str) -> Optional[Dict[str, Any]]:
        """
        Geocodifica um endereço canônico usando Google Geocoding API.

        Args:
            address_canonical: String canônica
                ex: "Rua 132, 289 - Setor Sul, Goiânia - GO, 74093-210, Brasil"

        Returns:
            dict com lat, lng, location_type, place_id, formatted_address
            ou None se falhar
        """
        if not self.api_key:
            if self.DEBUG:
                print("[GoogleGeocode] GOOGLE_MAPS_API_KEY não configurada")
            return None

        if not address_canonical or not address_canonical.strip():
            return None

        try:
            params = {
                "address": address_canonical,
                "key": self.api_key,
                "language": "pt-BR",
                "region": "br",
            }

            if self.DEBUG:
                print(f"[GoogleGeocode] Geocodificando: {address_canonical[:80]}...")

            resp = requests.get(GEOCODING_URL, params=params, timeout=10)
            data = resp.json()

            if data.get("status") != "OK" or not data.get("results"):
                if self.DEBUG:
                    print(
                        f"[GoogleGeocode] Status: {data.get('status')} — "
                        f"{data.get('error_message', 'sem resultados')}"
                    )
                return None

            result = data["results"][0]
            location = result["geometry"]["location"]
            lat = location["lat"]
            lng = location["lng"]

            # Validar se está em Goiás
            if not self._is_within_goias(lat, lng):
                if self.DEBUG:
                    print(f"[GoogleGeocode] FORA de Goiás: lat={lat}, lng={lng}")
                return None

            location_type = result["geometry"].get("location_type", "APPROXIMATE")
            place_id = result.get("place_id", "")
            formatted = result.get("formatted_address", "")

            if self.DEBUG:
                print(f"[GoogleGeocode] OK: {formatted}")
                print(
                    f"[GoogleGeocode]   lat={lat}, lng={lng}, "
                    f"type={location_type}, place_id={place_id[:20]}..."
                )

            return {
                "lat": lat,
                "lng": lng,
                "location_type": location_type,
                "place_id": place_id,
                "formatted_address": formatted,
            }

        except requests.exceptions.Timeout:
            print(f"[GoogleGeocode] Timeout: {address_canonical[:60]}")
        except Exception as e:
            print(f"[GoogleGeocode] Erro: {e}")
        return None

    # ------------------------------------------------------------------
    # Address Validation API
    # ------------------------------------------------------------------

    def validate_address(
        self,
        rua: str = "",
        numero: str = "",
        bairro: str = "",
        cidade: str = "",
        estado: str = "GO",
        cep: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Valida endereço via Google Address Validation API.

        Returns:
            dict com:
              - verdict: str (CONFIRMED, UNCONFIRMED_BUT_PLAUSIBLE, etc.)
              - has_inferred_components: bool
              - corrected_address: str (endereço corrigido)
              - geocode: dict (lat, lng, place_id) se disponível
            ou None se falhar
        """
        if not self.api_key:
            return None

        try:
            body: Dict[str, Any] = {
                "address": {
                    "regionCode": "BR",
                    "languageCode": "pt-BR",
                    "addressLines": [
                        self._build_address_line(rua, numero, bairro, cidade, estado, cep)
                    ],
                },
            }

            resp = requests.post(
                ADDRESS_VALIDATION_URL,
                json=body,
                params={"key": self.api_key},
                timeout=10,
            )

            if resp.status_code != 200:
                if self.DEBUG:
                    print(f"[AddressValidation] HTTP {resp.status_code}: " f"{resp.text[:200]}")
                return None

            data = resp.json()
            result = data.get("result", {})
            verdict = result.get("verdict", {})
            geocode_info = result.get("geocode", {})
            address_obj = result.get("address", {})

            # Extrair verdict granularity
            verdict_str = verdict.get("validationGranularity", "OTHER")
            has_inferred = verdict.get("hasInferredComponents", False)
            has_replaced = verdict.get("hasReplacedComponents", False)

            # Geocode do resultado
            geo_location = geocode_info.get("location", {})
            geo_lat = geo_location.get("latitude")
            geo_lng = geo_location.get("longitude")
            geo_place_id = geocode_info.get("placeId", "")

            corrected = address_obj.get("formattedAddress", "")

            if self.DEBUG:
                print(
                    f"[AddressValidation] verdict={verdict_str}, "
                    f"inferred={has_inferred}, replaced={has_replaced}"
                )
                if corrected:
                    print(f"[AddressValidation] Corrigido: {corrected}")

            return {
                "verdict": verdict_str,
                "has_inferred_components": has_inferred,
                "has_replaced_components": has_replaced,
                "corrected_address": corrected,
                "geocode": {
                    "lat": geo_lat,
                    "lng": geo_lng,
                    "place_id": geo_place_id,
                }
                if geo_lat is not None
                else None,
            }

        except requests.exceptions.Timeout:
            print("[AddressValidation] Timeout")
        except Exception as e:
            print(f"[AddressValidation] Erro: {e}")
        return None

    # ------------------------------------------------------------------
    # Quality Gate (classificação de confiança)
    # ------------------------------------------------------------------

    @staticmethod
    def classify_confidence(
        location_type: str,
        has_numero: bool = False,
        has_cep: bool = False,
        has_inferred: bool = False,
    ) -> str:
        """
        Classifica a confiança da geocodificação.

        Returns:
            "AUTO_OK" | "OK_WITH_CAUTION" | "NEEDS_REVIEW"
        """
        if location_type == "ROOFTOP":
            return "AUTO_OK"

        if location_type == "RANGE_INTERPOLATED" and has_numero and has_cep:
            if not has_inferred:
                return "OK_WITH_CAUTION"

        # GEOMETRIC_CENTER, APPROXIMATE, ou inferência pesada
        return "NEEDS_REVIEW"

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    @staticmethod
    def _is_within_goias(lat: float, lng: float) -> bool:
        return GOIAS_LAT_MIN <= lat <= GOIAS_LAT_MAX and GOIAS_LON_MIN <= lng <= GOIAS_LON_MAX

    @staticmethod
    def _build_address_line(
        rua: str, numero: str, bairro: str, cidade: str, estado: str, cep: str
    ) -> str:
        """Monta uma linha de endereço para a Address Validation API."""
        parts: List[str] = []
        if rua:
            parts.append(rua.strip())
        if numero and numero.strip():
            parts.append(numero.strip())
        if bairro:
            parts.append(bairro.strip())
        cidade_final = (cidade or "Goiânia").strip()
        estado_final = (estado or "GO").strip()
        parts.append(f"{cidade_final} - {estado_final}")
        if cep:
            import re

            cep_limpo = re.sub(r"\D", "", cep)
            if len(cep_limpo) == 8:
                parts.append(f"{cep_limpo[:5]}-{cep_limpo[5:]}")
        parts.append("Brasil")
        return ", ".join(parts)


# Instância global
google_geocoding_service = GoogleGeocodingService()
