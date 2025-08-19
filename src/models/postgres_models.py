"""
Modelos SQLAlchemy para PostgreSQL.
Define a estrutura das tabelas e relacionamentos do banco de dados.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, Integer, 
    create_engine, MetaData, Table
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class LogAnalysis(Base):
    """
    Modelo para análises de logs no PostgreSQL.
    Tabela principal para armazenar análises de logs.
    """
    __tablename__ = 'tb_analise_logs'
    
    # Primary key composta - corresponde à estrutura real da tabela
    id_analise = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    data_incidente = Column(DateTime(timezone=True), primary_key=True, nullable=False,
                           default=lambda: datetime.now(timezone.utc),
                           comment="Data/hora do incidente original")
    
    # Campos principais da análise
    erro = Column(Text, nullable=False, comment="Descrição do erro identificado")
    causa = Column(Text, nullable=False, comment="Causa raiz do problema")
    solucao = Column(Text, nullable=False, comment="Solução sugerida pela IA")
    criticidade = Column(String(10), nullable=False, comment="Nível de criticidade: baixa, media, alta")
    origem = Column(String(255), nullable=False, comment="Sistema/serviço de origem do erro")
    
    # Log original
    log_original = Column(Text, nullable=False, comment="Log original analisado")
    
    # Campos de feedback
    solucao_valida = Column(Boolean, nullable=True, comment="Se a solução foi validada pelo usuário")
    solucao_editada = Column(Text, nullable=True, comment="Solução editada pelo usuário")
    
    # Timestamps
    timestamp_analise = Column(DateTime(timezone=True), nullable=False, 
                              default=lambda: datetime.now(timezone.utc),
                              comment="Timestamp da análise pela IA")
    
    def __repr__(self):
        return f"<LogAnalysis(id_analise='{self.id_analise}', criticidade='{self.criticidade}', origem='{self.origem}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte o modelo para dicionário.
        
        Returns:
            Dict com todos os campos do modelo
        """
        return {
            'id': self.id_analise,  # Mapeia id_analise para id para compatibilidade
            'erro': self.erro,
            'causa': self.causa,
            'solucao': self.solucao,
            'criticidade': self.criticidade,
            'origem': self.origem,
            'log_original': self.log_original,
            'solucao_valida': self.solucao_valida,
            'solucao_editada': self.solucao_editada,
            'timestamp_analise': self.timestamp_analise.isoformat() if self.timestamp_analise else None,
            'data_incidente': self.data_incidente.isoformat() if self.data_incidente else None
        }
    
    @classmethod
    def from_analysis(cls, analysis) -> 'LogAnalysis':
        """
        Cria uma instância LogAnalysis a partir de um objeto Analysis.
        
        Args:
            analysis: Objeto Analysis do modelo original
            
        Returns:
            Nova instância de LogAnalysis
        """
        return cls(
            id_analise=analysis.id,
            erro=analysis.erro,
            causa=analysis.causa,
            solucao=analysis.solucao,
            criticidade=analysis.criticidade,
            origem=analysis.origem,
            log_original=analysis.log_original,
            timestamp_analise=analysis.timestamp_analise,
            data_incidente=analysis.data_incidente
        )


class DatabaseManager:
    """
    Gerenciador de conexão e operações do banco PostgreSQL.
    """
    
    def __init__(self, database_url: str):
        """
        Inicializa o gerenciador de banco.
        
        Args:
            database_url: URL de conexão com o PostgreSQL
        """
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        self._setup_database()
    
    def _setup_database(self):
        """Configura engine e session factory."""
        self.engine = create_engine(
            self.database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False  # Set to True for SQL debugging
        )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    def create_tables(self):
        """Cria todas as tabelas no banco."""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self):
        """
        Retorna uma nova sessão do banco.
        
        Returns:
            Session do SQLAlchemy
        """
        return self.SessionLocal()
    
    def health_check(self) -> bool:
        """
        Verifica se a conexão com o banco está saudável.
        
        Returns:
            bool: True se a conexão está OK
        """
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
                return True
        except Exception:
            return False
    
    def close(self):
        """Fecha as conexões do pool."""
        if self.engine:
            self.engine.dispose()