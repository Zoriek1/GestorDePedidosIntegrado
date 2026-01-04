# -*- coding: utf-8 -*-
"""
Model de Endereço do Cliente
Permite múltiplos endereços por cliente
"""
from datetime import datetime

from app import db


class EnderecoCliente(db.Model):
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

    def marcar_como_principal(self):
        """
        Marca este endereço como principal e desmarca os outros do mesmo cliente
        """
        # Desmarcar todos os endereços do cliente
        EnderecoCliente.query.filter_by(cliente_id=self.cliente_id).update({"principal": False})

        # Marcar este como principal
        self.principal = True
        db.session.commit()
