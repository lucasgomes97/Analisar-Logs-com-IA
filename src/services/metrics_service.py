"""
Metrics service for analyzing log analysis data and generating dashboard metrics.
Provides aggregated statistics and insights from InfluxDB data.
Enhanced with connection pooling and caching for improved performance.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient, QueryApi
from influxdb_client.client.exceptions import InfluxDBError
from src.utils.logging_config import (
    get_logger, log_operation, log_database_operation, 
    performance_monitor, metrics_collector
)
# Connection pool removido - usando PostgreSQL com SQLAlchemy
from src.services.cache_service import get_cache_service, cached

# Configure enhanced logging
logger = get_logger(__name__)


class MetricsService:
    """
    Service class for generating metrics and analytics from log analysis data.
    Provides methods for dashboard statistics and performance insights.
    """
    
    def __init__(self, url: str, token: str, org: str, bucket: str, use_pool: bool = True):
        """
        Initialize MetricsService.
        
        Args:
            url: InfluxDB URL
            token: Authentication token
            org: Organization name
            bucket: Bucket name
            use_pool: Whether to use connection pooling (default: True)
        """
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self.use_pool = use_pool
        self.client = None
        self.query_api = None
        
        if not use_pool:
            self._connect()
        else:
            logger.info("✅ MetricsService configurado para usar connection pool")
    
    @log_operation("metrics_service_connection")
    def _connect(self):
        """Establish connection to InfluxDB."""
        try:
            with performance_monitor("metrics_service_connection_setup"):
                self.client = InfluxDBClient(
                    url=self.url,
                    token=self.token,
                    org=self.org
                )
                self.query_api = self.client.query_api()
            
            # Log successful connection
            log_database_operation(
                "connection",
                success=True,
                service="MetricsService",
                url=self.url,
                org=self.org,
                bucket=self.bucket
            )
            logger.info("✅ Conexão MetricsService com InfluxDB estabelecida")
            
        except Exception as e:
            # Log connection failure with detailed context
            log_database_operation(
                "connection",
                success=False,
                service="MetricsService",
                error_details={
                    'type': type(e).__name__,
                    'message': str(e),
                    'url': self.url,
                    'org': self.org
                }
            )
            logger.error(f"❌ Erro ao conectar MetricsService com InfluxDB: {e}", exc_info=True)
            raise
    
    def _ensure_connection(self):
        """Ensure direct connection is available when not using pool."""
        if not self.client:
            self._connect()
    
    def _execute_query(self, query: str):
        """Execute query using direct connection."""
        # Connection pool removido - usando conexão direta
        self._ensure_connection()
        return self.query_api.query(org=self.org, query=query)
    
    @cached(key_func=lambda self, period_days=30: f"error_count_by_criticality:{period_days}", ttl=300)
    def get_error_count_by_criticality(self, period_days: int = 30) -> Dict[str, int]:
        """
        Get count of errors grouped by criticality level.
        
        Args:
            period_days: Number of days to look back (default: 30)
            
        Returns:
            Dict with criticality levels as keys and counts as values
            
        Requirements: 6.1 - Dashboard should show number of errors by criticality
        """
        try:
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: -{period_days}d)
              |> filter(fn: (r) => r._measurement == "tb_analise_logs")
              |> filter(fn: (r) => r._field == "erro")
              |> group(columns: ["criticidade"])
              |> count()
              |> yield(name: "error_count_by_criticality")
            '''
            
            result = self._execute_query(query)
            
            # Initialize counts for all criticality levels
            counts = {
                "baixa": 0,
                "media": 0,
                "alta": 0
            }
            
            # Process query results
            for table in result:
                for record in table.records:
                    criticidade = record.get("criticidade", "").lower()
                    count = record.get_value()
                    
                    if criticidade in counts:
                        counts[criticidade] = count
            
            logger.info(f"✅ Contagem por criticidade obtida: {counts}")
            return counts
            
        except InfluxDBError as e:
            logger.error(f"❌ Erro InfluxDB ao obter contagem por criticidade: {e}")
            return {"baixa": 0, "media": 0, "alta": 0}
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao obter contagem por criticidade: {e}")
            return {"baixa": 0, "media": 0, "alta": 0}
    
    @cached(key_func=lambda self, period_days=30: f"ai_accuracy_rate:{period_days}", ttl=300)
    def get_ai_accuracy_rate(self, period_days: int = 30) -> float:
        """
        Calculate AI accuracy rate based on user feedback.
        
        Args:
            period_days: Number of days to look back (default: 30)
            
        Returns:
            Float representing accuracy rate (0.0 to 1.0)
            
        Requirements: 6.2 - Dashboard should show AI solution accuracy rate
        """
        try:
            # Query for total classified solutions
            total_query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: -{period_days}d)
              |> filter(fn: (r) => r._measurement == "tb_analise_logs")
              |> filter(fn: (r) => r._field == "solucao_valida")
              |> filter(fn: (r) => r._value != "null" and r._value != "")
              |> count()
              |> yield(name: "total_classified")
            '''
            
            # Query for valid solutions
            valid_query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: -{period_days}d)
              |> filter(fn: (r) => r._measurement == "tb_analise_logs")
              |> filter(fn: (r) => r._field == "solucao_valida")
              |> filter(fn: (r) => r._value == "true")
              |> count()
              |> yield(name: "valid_solutions")
            '''
            
            # Execute queries
            total_result = self._execute_query(total_query)
            valid_result = self._execute_query(valid_query)
            
            total_classified = 0
            valid_solutions = 0
            
            # Process total classified results
            for table in total_result:
                for record in table.records:
                    total_classified = record.get_value()
                    break
            
            # Process valid solutions results
            for table in valid_result:
                for record in table.records:
                    valid_solutions = record.get_value()
                    break
            
            # Calculate accuracy rate
            if total_classified == 0:
                accuracy_rate = 0.0
                logger.info("⚠️ Nenhuma solução classificada encontrada")
            else:
                accuracy_rate = valid_solutions / total_classified
                logger.info(f"✅ Taxa de acerto da IA: {accuracy_rate:.2%} ({valid_solutions}/{total_classified})")
            
            return accuracy_rate
            
        except InfluxDBError as e:
            logger.error(f"❌ Erro InfluxDB ao calcular taxa de acerto: {e}")
            return 0.0
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao calcular taxa de acerto: {e}")
            return 0.0
    
    @cached(key_func=lambda self, period_days=30: f"avg_resolution_time:{period_days}", ttl=300)
    def get_average_resolution_time(self, period_days: int = 30) -> float:
        """
        Calculate average time between incident and solution classification.
        
        Args:
            period_days: Number of days to look back (default: 30)
            
        Returns:
            Float representing average resolution time in hours
            
        Requirements: 6.3 - Dashboard should show average time between incident and solution
        """
        try:
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: -{period_days}d)
              |> filter(fn: (r) => r._measurement == "tb_analise_logs")
              |> filter(fn: (r) => r._field == "solucao_valida")
              |> filter(fn: (r) => r._value != "null" and r._value != "")
              |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
              |> filter(fn: (r) => exists r.timestamp_analise)
              |> map(fn: (r) => ({{
                  r with
                  resolution_time_hours: (float(v: r._time) - float(v: time(v: r.timestamp_analise))) / 3600000000000.0
              }}))
              |> mean(column: "resolution_time_hours")
              |> yield(name: "avg_resolution_time")
            '''
            
            result = self._execute_query(query)
            
            avg_resolution_time = 0.0
            
            # Process query results
            for table in result:
                for record in table.records:
                    avg_resolution_time = record.get_value() or 0.0
                    break
            
            # Ensure non-negative result
            avg_resolution_time = max(0.0, avg_resolution_time)
            
            logger.info(f"✅ Tempo médio de resolução: {avg_resolution_time:.2f} horas")
            return avg_resolution_time
            
        except InfluxDBError as e:
            logger.error(f"❌ Erro InfluxDB ao calcular tempo médio de resolução: {e}")
            return 0.0
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao calcular tempo médio de resolução: {e}")
            return 0.0
    
    @cached(key_func=lambda self, period_days=30, limit=10: f"top_error_sources:{period_days}:{limit}", ttl=300)
    def get_top_error_sources(self, period_days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most frequent error sources (origins).
        
        Args:
            period_days: Number of days to look back (default: 30)
            limit: Maximum number of sources to return (default: 10)
            
        Returns:
            List of dictionaries with 'origem' and 'count' keys, sorted by count descending
            
        Requirements: 6.4 - Dashboard should show most recurring error origins
        """
        try:
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: -{period_days}d)
              |> filter(fn: (r) => r._measurement == "tb_analise_logs")
              |> filter(fn: (r) => r._field == "erro")
              |> group(columns: ["origem"])
              |> count()
              |> sort(columns: ["_value"], desc: true)
              |> limit(n: {limit})
              |> yield(name: "top_error_sources")
            '''
            
            result = self._execute_query(query)
            
            sources = []
            
            # Process query results
            for table in result:
                for record in table.records:
                    origem = record.get("origem", "Desconhecido")
                    count = record.get_value()
                    
                    sources.append({
                        "origem": origem,
                        "count": count
                    })
            
            logger.info(f"✅ Top {len(sources)} origens de erro obtidas")
            return sources
            
        except InfluxDBError as e:
            logger.error(f"❌ Erro InfluxDB ao obter top origens de erro: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao obter top origens de erro: {e}")
            return []
    
    @log_operation("get_comprehensive_metrics")
    def get_comprehensive_metrics(self, period_days: int = 30) -> Dict[str, Any]:
        """
        Get all metrics in a single call for dashboard efficiency.
        
        Args:
            period_days: Number of days to look back (default: 30)
            
        Returns:
            Dictionary containing all metrics
            
        Requirements: 7.1, 7.4 - Log metrics operations with detailed context
        """
        start_time = datetime.now()
        
        try:
            with performance_monitor("comprehensive_metrics_calculation", period_days=period_days):
                logger.info(f"📊 Obtendo métricas abrangentes para {period_days} dias")
                
                metrics = {
                    "period_days": period_days,
                    "error_count_by_criticality": self.get_error_count_by_criticality(period_days),
                    "ai_accuracy_rate": self.get_ai_accuracy_rate(period_days),
                    "average_resolution_time_hours": self.get_average_resolution_time(period_days),
                    "top_error_sources": self.get_top_error_sources(period_days),
                    "generated_at": datetime.now().isoformat()
                }
                
                # Calculate total errors
                total_errors = sum(metrics["error_count_by_criticality"].values())
                metrics["total_errors"] = total_errors
            
            # Log successful metrics calculation with context
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            log_database_operation(
                "metrics_calculation",
                success=True,
                metrics_type="comprehensive",
                period_days=period_days,
                total_errors=total_errors,
                accuracy_rate=metrics["ai_accuracy_rate"],
                duration_ms=duration_ms
            )
            
            logger.info(f"✅ Métricas abrangentes obtidas com sucesso - {total_errors} erros, {metrics['ai_accuracy_rate']:.2%} precisão")
            metrics_collector.record_operation("metrics_comprehensive", duration_ms, success=True)
            return metrics
            
        except Exception as e:
            # Log detailed error for debugging (Requirement 7.4)
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            log_database_operation(
                "metrics_calculation",
                success=False,
                metrics_type="comprehensive",
                period_days=period_days,
                error_details={
                    'type': type(e).__name__,
                    'message': str(e),
                    'bucket': self.bucket,
                    'org': self.org
                },
                duration_ms=duration_ms
            )
            
            logger.error(f"❌ Erro ao obter métricas abrangentes: {e}",
                        extra={'operation': 'get_comprehensive_metrics', 'period_days': period_days}, exc_info=True)
            metrics_collector.record_operation("metrics_comprehensive", duration_ms, success=False)
            
            return {
                "period_days": period_days,
                "error_count_by_criticality": {"baixa": 0, "media": 0, "alta": 0},
                "ai_accuracy_rate": 0.0,
                "average_resolution_time_hours": 0.0,
                "top_error_sources": [],
                "total_errors": 0,
                "generated_at": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def health_check(self) -> bool:
        """
        Check if MetricsService connection is healthy.
        
        Returns:
            bool: True if connection is healthy
        """
        try:
            # Simple query to test connection
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: -1m)
              |> limit(n: 1)
            '''
            
            self.query_api.query(org=self.org, query=query)
            logger.info("✅ MetricsService health check passou")
            return True
            
        except Exception as e:
            logger.error(f"❌ MetricsService health check falhou: {e}")
            return False
    
    def close(self):
        """Close InfluxDB connection."""
        try:
            if self.client:
                self.client.close()
                logger.info("✅ Conexão MetricsService InfluxDB fechada")
        except Exception as e:
            logger.error(f"❌ Erro ao fechar conexão MetricsService InfluxDB: {e}")