# -*- coding: utf-8 -*-
"""
Model de Endereço do Cliente
Permite múltiplos endereços por cliente, com cache de geocodificação
"""
import hashlib
import re
from datetime import datetime

from app import db
from app.services.tenant_scope import TenantScoped


class EnderecoCliente(TenantScoped, db.Model):
    """
    Model de Endereço vinculado a um Cliente
    Um cliente pode ter múltiplos endereços (casa, trabalho, etc)
    """

    __tablename__ = "enderecos_clientes"

    # Campos principais
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identificação do endereço
    apelido = db.Column(db.String(50), nullable=True)  # "Casa", "Trabalho", etc
    principal = db.Column(db.Boolean, default=False)  # Endereço padrão

    # Dados do endereço
    cep = db.Column(db.String(10), nullable=True)
    rua = db.Column(db.String(200), nullable=True)
    numero = db.Column(db.String(20), nullable=True)
    complemento = db.Column(db.String(100), nullable=True)
    bairro = db.Column(db.String(100), nullable=True)
    cidade = db.Column(db.String(100), nullable=True)
    estado = db.Column(db.String(2), nullable=True, default="GO")

    # Geocodificação (cache)
    lat = db.Column(db.Float, nullable=True, comment="Latitude geocodificada")
    lng = db.Column(db.Float, nullable=True, comment="Longitude geocodificada")
    location_type = db.Column(
        db.String(30),
        nullable=True,
        comment="ROOFTOP, RANGE_INTERPOLATED, GEOMETRIC_CENTER, APPROXIMATE",
    )
    place_id = db.Column(db.String(255), nullable=True, comment="Google Place ID")
    confidence_status = db.Column(
        db.String(20),
        nullable=True,
        comment="AUTO_OK, OK_WITH_CAUTION, NEEDS_REVIEW",
    )
    geocode_provider = db.Column(db.String(20), nullable=True, comment="Provider usado (google)")
    address_canonical = db.Column(
        db.String(500),
        nullable=True,
        comment="String canônica para geocodificação",
    )
    address_hash = db.Column(
        db.String(64),
        nullable=True,
        index=True,
        comment="SHA-256 da address_canonical (detectar mudança)",
    )
    last_geocoded_at = db.Column(
        db.DateTime, nullable=True, comment="Timestamp da última geocodificação"
    )

    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        apelido_str = f" ({self.apelido})" if self.apelido else ""
        return f"<EnderecoCliente #{self.id}{apelido_str} - Cliente {self.cliente_id}>"

    def to_dict(self):
        """
        Converte endereço para dicionário (para API JSON)

        Returns:
            dict: Dados do endereço
        """
        return {
            "id": self.id,
            "cliente_id": self.cliente_id,
            "apelido": self.apelido or "",
            "principal": self.principal,
            "cep": self.cep or "",
            "rua": self.rua or "",
            "numero": self.numero or "",
            "complemento": self.complemento or "",
            "bairro": self.bairro or "",
            "cidade": self.cidade or "",
            "estado": self.estado or "GO",
            "endereco_completo": self.get_endereco_completo(),
            "lat": self.lat,
            "lng": self.lng,
            "confidence_status": self.confidence_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def get_endereco_completo(self):
        """
        Retorna endereço formatado como string

        Returns:
            str: Endereço completo formatado
        """
        partes = []

        if self.rua:
            partes.append(self.rua)
        if self.numero:
            partes.append(self.numero)
        if self.complemento:
            partes.append(self.complemento)
        if self.bairro:
            partes.append(self.bairro)
        if self.cidade:
            partes.append(self.cidade)
        if self.estado:
            partes.append(self.estado)
        if self.cep:
            partes.append(f"CEP: {self.cep}")

        return ", ".join(partes)

    def build_address_canonical(self):
        """
        Constrói string canônica do endereço para geocodificação e cache.
        Formato: "Logradouro, Número - Bairro, Cidade - UF, CEP, Brasil"

        Returns:
            str: Endereço canônico normalizado
        """
        partes = []
        if self.rua:
            partes.append(self.rua.strip())
        if self.numero and self.numero.strip():
            partes.append(self.numero.strip())

        bairro_cidade = []
        if self.bairro:
            bairro_cidade.append(self.bairro.strip())
        cidade = (self.cidade or "Goiânia").strip()
        estado = (self.estado or "GO").strip().upper()
        bairro_cidade.append(f"{cidade} - {estado}")

        if partes:
            canonical = ", ".join(partes) + " - " + ", ".join(bairro_cidade)
        else:
            canonical = ", ".join(bairro_cidade)

        if self.cep:
            cep_limpo = re.sub(r"\D", "", self.cep)
            if len(cep_limpo) == 8:
                canonical += f", {cep_limpo[:5]}-{cep_limpo[5:]}"

        canonical += ", Brasil"
        return canonical

    def compute_address_hash(self):
        """
        Calcula SHA-256 da address_canonical para detectar mudanças.

        Returns:
            str: Hash hexadecimal de 64 caracteres
        """
        canonical = self.build_address_canonical()
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def update_geocode_cache(
        self, lat, lng, location_type=None, place_id=None, confidence_status=None, provider="google"
    ):
        """Atualiza campos de geocodificação em lote."""
        self.lat = lat
        self.lng = lng
        self.location_type = location_type
        self.place_id = place_id
        self.confidence_status = confidence_status
        self.geocode_provider = provider
        self.address_canonical = self.build_address_canonical()
        self.address_hash = self.compute_address_hash()
        self.last_geocoded_at = datetime.utcnow()

    def needs_geocoding(self):
        """Retorna True se o endereço precisa ser (re)geocodificado."""
        current_hash = self.compute_address_hash()
        return self.address_hash != current_hash or self.lat is None

    def marcar_como_principal(self):
        """
        Marca este endereço como principal e desmarca os outros do mesmo cliente
        """
        # Desmarcar todos os endereços do cliente
        EnderecoCliente.query.filter_by(
            cliente_id=self.cliente_id,
            store_ref_id=self.store_ref_id,
        ).update({"principal": False})

        # Marcar este como principal
        self.principal = True
        db.session.commit()
