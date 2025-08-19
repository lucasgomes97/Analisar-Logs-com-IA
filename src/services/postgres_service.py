"""
PostgreSQL service for managing log analysis data.
Substitui o InfluxDBService com funcionalidades equivalentes usando PostgreSQL.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_

from src.models.postgres_models import LogAnalysis, DatabaseManager
from src.models.models import Analysis, Classification
from src.utils.logging_config import (
    get_logger, log_operation, log_database_operation, 
    performance_monitor, metrics_collector
)
from src.utils.error_handling import ErrorHandler

# Configure enhanced logging
logger = get_logger(__name__)


class PostgreSQLService:
    """
    Service class for PostgreSQL operations.
    Substitui o InfluxDBService com interface compatível.
    """
    
    def __init__(self, database_url: str):
        """
        Initialize PostgreSQL service.
        
        Args:
            database_url: PostgreSQL connection URL
        """
        self.database_url = database_url
        self.db_manager = DatabaseManager(database_url)
        
        # Criar tabelas se não existirem
        try:
            self.db_manager.create_tables()
            logger.info("✅ PostgreSQLService inicializado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar PostgreSQLService: {e}")
            logger.warning("⚠️ Continuando sem conexão com PostgreSQL (modo desenvolvimento)")
            # Em desenvolvimento, não falha se não conseguir conectar
            self.db_manager = None
    
    @log_operation("postgres_insert_analysis")
    @ErrorHandler.with_retry('postgres_write', reraise_exceptions=[ValueError])
    def insert_analysis(self, analysis: Analysis) -> str:
        """
        Insert a complete analysis into PostgreSQL.
        
        Args:
            analysis: Analysis object to insert
            
        Returns:
            str: Analysis ID if successful
            
        Raises:
            SQLAlchemyError: If insertion fails
        """
        start_time = datetime.now()
        
        try:
            if not self.db_manager:
                logger.warning("⚠️ PostgreSQL não disponível - simulando inserção")
                return analysis.id
                
            with performance_monitor("postgres_insert", analysis_id=analysis.id):
                with self.db_manager.get_session() as session:
                    # Converter Analysis para LogAnalysis
                    log_analysis = LogAnalysis.from_analysis(analysis)
                    
                    # Inserir no banco
                    session.add(log_analysis)
                    session.commit()
                    
                    # Refresh para obter dados atualizados
                    session.refresh(log_analysis)
            
            # Log successful insertion
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            log_database_operation(
                "insert",
                analysis_id=analysis.id,
                success=True,
                table="tb_analise_logs",
                duration_ms=duration_ms
            )
            
            logger.info(f"✅ Análise salva no PostgreSQL com ID: {analysis.id}")
            metrics_collector.record_operation("postgres_insert", duration_ms, success=True)
            return analysis.id
            
        except Exception as e:
            # Handle insertion error
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            error_details = {
                'type': type(e).__name__,
                'message': str(e),
                'analysis_id': analysis.id,
                'table': 'tb_analise_logs'
            }
            
            log_database_operation(
                "insert",
                analysis_id=analysis.id,
                success=False,
                error_details=error_details,
                duration_ms=duration_ms
            )
            
            metrics_collector.record_operation("postgres_insert", duration_ms, success=False)
            logger.error(f"❌ Erro ao inserir análise no PostgreSQL: {e}")
            raise SQLAlchemyError(f"Erro ao inserir análise: {e}")
    
    @log_operation("postgres_get_analysis_by_id")
    @ErrorHandler.with_retry('postgres_read', fallback_value=None)
    def get_analysis_by_id(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve analysis by ID from PostgreSQL.
        
        Args:
            analysis_id: Unique analysis identifier
            
        Returns:
            Dict with analysis data or None if not found
        """
        start_time = datetime.now()
        
        try:
            if not self.db_manager:
                logger.warning("⚠️ PostgreSQL não disponível - retornando None")
                return None
                
            with performance_monitor("postgres_query", analysis_id=analysis_id):
                with self.db_manager.get_session() as session:
                    log_analysis = session.query(LogAnalysis).filter(
                        LogAnalysis.id_analise == analysis_id
                    ).first()
                    
                    if log_analysis:
                        result = log_analysis.to_dict()
                    else:
                        result = None
            
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log successful query
            log_database_operation(
                "query",
                analysis_id=analysis_id,
                success=True,
                query_type="get_by_id",
                found=result is not None,
                duration_ms=duration_ms
            )
            
            if result:
                logger.info(f"✅ Análise {analysis_id} encontrada no PostgreSQL")
            else:
                logger.warning(f"⚠️ Análise {analysis_id} não encontrada no PostgreSQL")
            
            metrics_collector.record_operation("postgres_query", duration_ms, success=True)
            return result
            
        except Exception as e:
            # Handle query error
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            error_details = {
                'type': type(e).__name__,
                'message': str(e),
                'analysis_id': analysis_id,
                'query_type': 'get_by_id'
            }
            
            log_database_operation(
                "query",
                analysis_id=analysis_id,
                success=False,
                error_details=error_details,
                duration_ms=duration_ms
            )
            
            metrics_collector.record_operation("postgres_query", duration_ms, success=False)
            logger.warning(f"⚠️ Retornando None devido a erro na consulta: {e}")
            return None
    
    @log_operation("postgres_update_classification")
    @ErrorHandler.with_retry('postgres_write')
    def update_classification(self, analysis_id: str, classification: Classification) -> bool:
        """
        Update analysis classification in PostgreSQL.
        
        Args:
            analysis_id: Analysis ID to update
            classification: Classification data
            
        Returns:
            bool: True if successful, False otherwise
        """
        start_time = datetime.now()
        
        try:
            if not self.db_manager:
                logger.warning("⚠️ PostgreSQL não disponível - simulando atualização")
                return True
                
            with performance_monitor("postgres_update", analysis_id=analysis_id):
                with self.db_manager.get_session() as session:
                    # Buscar análise existente
                    log_analysis = session.query(LogAnalysis).filter(
                        LogAnalysis.id_analise == analysis_id
                    ).first()
                    
                    if not log_analysis:
                        logger.error(f"❌ Análise {analysis_id} não encontrada para atualização")
                        return False
                    
                    # Rastrear campos modificados
                    fields_modified = []
                    
                    # Atualizar campos de classificação
                    if hasattr(classification, 'solucao_valida') and classification.solucao_valida is not None:
                        old_value = log_analysis.solucao_valida
                        log_analysis.solucao_valida = classification.solucao_valida
                        if old_value != classification.solucao_valida:
                            fields_modified.append({
                                'field': 'solucao_valida',
                                'old_value': old_value,
                                'new_value': classification.solucao_valida
                            })
                    
                    if hasattr(classification, 'solucao_editada') and classification.solucao_editada:
                        old_value = log_analysis.solucao_editada
                        log_analysis.solucao_editada = classification.solucao_editada
                        if old_value != classification.solucao_editada:
                            fields_modified.append({
                                'field': 'solucao_editada',
                                'old_value': old_value,
                                'new_value': classification.solucao_editada
                            })
                    
                    # Atualizar timestamp
                    log_analysis.updated_at = datetime.now(timezone.utc)
                    
                    # Commit das alterações
                    session.commit()
            
            # Log successful update
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            log_database_operation(
                "update",
                analysis_id=analysis_id,
                success=True,
                fields_modified=fields_modified,
                update_type="classification",
                duration_ms=duration_ms
            )
            
            logger.info(f"✅ Classificação da análise {analysis_id} atualizada com sucesso")
            metrics_collector.record_operation("postgres_update", duration_ms, success=True)
            return True
            
        except Exception as e:
            # Handle update error
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            error_details = {
                'type': type(e).__name__,
                'message': str(e),
                'analysis_id': analysis_id,
                'update_type': 'classification'
            }
            
            log_database_operation(
                "update",
                analysis_id=analysis_id,
                success=False,
                error_details=error_details,
                duration_ms=duration_ms
            )
            
            metrics_collector.record_operation("postgres_update", duration_ms, success=False)
            logger.error(f"❌ Erro ao atualizar classificação: {e}")
            return False
    
    @log_operation("postgres_health_check")
    def health_check(self) -> bool:
        """
        Check if PostgreSQL connection is healthy.
        
        Returns:
            bool: True if connection is healthy
        """
        start_time = datetime.now()
        
        try:
            if not self.db_manager:
                logger.warning("⚠️ PostgreSQL não disponível")
                return False
                
            with performance_monitor("postgres_health_check"):
                result = self.db_manager.health_check()
            
            # Log health check result
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            log_database_operation(
                "health_check",
                success=result,
                duration_ms=duration_ms,
                database="postgresql"
            )
            
            if result:
                logger.info("✅ PostgreSQL health check passou")
            else:
                logger.error("❌ PostgreSQL health check falhou")
            
            metrics_collector.record_operation("postgres_health_check", duration_ms, success=result)
            return result
            
        except Exception as e:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            log_database_operation(
                "health_check",
                success=False,
                error_details={
                    'type': type(e).__name__,
                    'message': str(e),
                    'database': 'postgresql'
                },
                duration_ms=duration_ms
            )
            
            logger.error(f"❌ PostgreSQL health check falhou: {e}")
            metrics_collector.record_operation("postgres_health_check", duration_ms, success=False)
            return False
    
    def get_recent_analyses(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get recent analyses for dashboard.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of analysis dictionaries
        """
        try:
            if not self.db_manager:
                logger.warning("⚠️ PostgreSQL não disponível - retornando lista vazia")
                return []
                
            with self.db_manager.get_session() as session:
                analyses = session.query(LogAnalysis).order_by(
                    desc(LogAnalysis.timestamp_analise)
                ).limit(limit).offset(offset).all()
                
                return [analysis.to_dict() for analysis in analyses]
                
        except Exception as e:
            logger.error(f"❌ Erro ao buscar análises recentes: {e}")
            return []
    
    def close(self):
        """Close PostgreSQL connections."""
        try:
            self.db_manager.close()
            logger.info("✅ Conexões PostgreSQL fechadas")
        except Exception as e:
            logger.error(f"❌ Erro ao fechar conexões PostgreSQL: {e}")