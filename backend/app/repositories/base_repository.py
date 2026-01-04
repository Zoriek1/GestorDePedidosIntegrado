# -*- coding: utf-8 -*-
"""
Base Repository - Classe base para repositories
Fornece operações CRUD genéricas
"""
from typing import TypeVar, Generic, List, Optional, Type
from app import db

ModelType = TypeVar('ModelType')


class BaseRepository(Generic[ModelType]):
    """Classe base para repositories com operações CRUD genéricas"""
    
    def __init__(self, model: Type[ModelType]):
        """
        Inicializa o repository
        
        Args:
            model: Classe do modelo SQLAlchemy
        """
        self.model = model
    
    def get_by_id(self, id: int) -> Optional[ModelType]:
        """Busca entidade por ID"""
        return self.model.query.get(id)
    
    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[ModelType]:
        """Lista todas as entidades"""
        query = self.model.query
        if limit:
            query = query.limit(limit).offset(offset)
        return query.all()
    
    def create(self, **kwargs) -> ModelType:
        """Cria nova entidade"""
        entity = self.model(**kwargs)
        db.session.add(entity)
        db.session.commit()
        return entity
    
    def update(self, entity: ModelType, **kwargs) -> ModelType:
        """Atualiza entidade existente"""
        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        db.session.commit()
        return entity
    
    def delete(self, entity: ModelType) -> bool:
        """Remove entidade"""
        try:
            db.session.delete(entity)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            # Log do erro para diagnóstico
            print(f"[REPOSITORY] Erro ao deletar {type(entity).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def count(self) -> int:
        """Conta total de entidades"""
        return self.model.query.count()

