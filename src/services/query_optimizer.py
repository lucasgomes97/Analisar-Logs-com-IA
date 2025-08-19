"""
Query optimizer for InfluxDB queries to improve performance.
Provides optimized query patterns and filters.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class QueryOptimizer:
    """
    Optimizes InfluxDB queries for better performance.
    Provides query templates and optimization strategies.
    """
    
    def __init__(self, bucket: str):
        """
        Initialize query optimizer.
        
        Args:
            bucket: InfluxDB bucket name
        """
        self.bucket = bucket
        logger.info(f"✅ QueryOptimizer inicializado para bucket: {bucket}")
    
    def build_time_range_filter(self, period_days: int = 30, 
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> str:
        """
        Build optimized time range filter.
        
        Args:
            period_days: Number of days to look back (if start_date not provided)
            start_date: Specific start date
            end_date: Specific end date
            
        Returns:
            str: Optimized time range filter
        """
        if start_date and end_date:
            start_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_str = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            return f'|> range(start: {start_str}, stop: {end_str})'
        elif start_date:
            start_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            return f'|> range(start: {start_str})'
        else:
            return f'|> range(start: -{period_days}d)'
    
    def build_measurement_filter(self, measurement: str = "tb_analise_logs") -> str:
        """Build measurement filter."""
        return f'|> filter(fn: (r) => r._measurement == "{measurement}")'
    
    def build_field_filter(self, field: str) -> str:
        """Build field filter."""
        return f'|> filter(fn: (r) => r._field == "{field}")'
    
    def build_tag_filter(self, tag_key: str, tag_value: str) -> str:
        """Build tag filter."""
        return f'|> filter(fn: (r) => r.{tag_key} == "{tag_value}")'
    
    def build_multiple_tag_filter(self, tag_filters: Dict[str, str]) -> str:
        """
        Build multiple tag filters.
        
        Args:
            tag_filters: Dictionary of tag_key: tag_value pairs
            
        Returns:
            str: Combined tag filters
        """
        filters = []
        for tag_key, tag_value in tag_filters.items():
            filters.append(f'r.{tag_key} == "{tag_value}"')
        
        if len(filters) == 1:
            return f'|> filter(fn: (r) => {filters[0]})'
        else:
            combined = ' and '.join(filters)
            return f'|> filter(fn: (r) => {combined})'
    
    def get_error_count_by_criticality_query(self, period_days: int = 30,
                                           criticality_filter: Optional[str] = None) -> str:
        """
        Get optimized query for error count by criticality.
        
        Args:
            period_days: Number of days to look back
            criticality_filter: Optional criticality filter
            
        Returns:
            str: Optimized query
        """
        filters = [
            f'from(bucket: "{self.bucket}")',
            self.build_time_range_filter(period_days),
            self.build_measurement_filter(),
            self.build_field_filter("erro")
        ]
        
        if criticality_filter:
            filters.append(self.build_tag_filter("criticidade", criticality_filter))
        
        filters.extend([
            '|> group(columns: ["criticidade"])',
            '|> count()',
            '|> yield(name: "error_count_by_criticality")'
        ])
        
        return '\n  '.join(filters)
    
    def get_ai_accuracy_query(self, period_days: int = 30) -> tuple:
        """
        Get optimized queries for AI accuracy calculation.
        
        Args:
            period_days: Number of days to look back
            
        Returns:
            tuple: (total_query, valid_query)
        """
        base_filters = [
            f'from(bucket: "{self.bucket}")',
            self.build_time_range_filter(period_days),
            self.build_measurement_filter(),
            self.build_field_filter("solucao_valida"),
            '|> filter(fn: (r) => r._value != "null" and r._value != "")'
        ]
        
        total_query = '\n  '.join(base_filters + [
            '|> count()',
            '|> yield(name: "total_classified")'
        ])
        
        valid_query = '\n  '.join(base_filters + [
            '|> filter(fn: (r) => r._value == "true")',
            '|> count()',
            '|> yield(name: "valid_solutions")'
        ])
        
        return total_query, valid_query
    
    def get_resolution_time_query(self, period_days: int = 30) -> str:
        """
        Get optimized query for average resolution time.
        
        Args:
            period_days: Number of days to look back
            
        Returns:
            str: Optimized query
        """
        filters = [
            f'from(bucket: "{self.bucket}")',
            self.build_time_range_filter(period_days),
            self.build_measurement_filter(),
            self.build_field_filter("solucao_valida"),
            '|> filter(fn: (r) => r._value != "null" and r._value != "")',
            '|> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")',
            '|> filter(fn: (r) => exists r.timestamp_analise)',
            '|> map(fn: (r) => ({',
            '    r with',
            '    resolution_time_hours: (float(v: r._time) - float(v: time(v: r.timestamp_analise))) / 3600000000000.0',
            '  }))',
            '|> mean(column: "resolution_time_hours")',
            '|> yield(name: "avg_resolution_time")'
        ]
        
        return '\n  '.join(filters)
    
    def get_top_error_sources_query(self, period_days: int = 30, limit: int = 10) -> str:
        """
        Get optimized query for top error sources.
        
        Args:
            period_days: Number of days to look back
            limit: Maximum number of sources to return
            
        Returns:
            str: Optimized query
        """
        filters = [
            f'from(bucket: "{self.bucket}")',
            self.build_time_range_filter(period_days),
            self.build_measurement_filter(),
            self.build_field_filter("erro"),
            '|> group(columns: ["origem"])',
            '|> count()',
            '|> sort(columns: ["_value"], desc: true)',
            f'|> limit(n: {limit})',
            '|> yield(name: "top_error_sources")'
        ]
        
        return '\n  '.join(filters)
    
    def get_analysis_history_query(self, page: int = 1, limit: int = 20,
                                 period_days: int = 90,
                                 criticality_filter: Optional[str] = None,
                                 start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> tuple:
        """
        Get optimized queries for analysis history with pagination.
        
        Args:
            page: Page number (1-based)
            limit: Items per page
            period_days: Number of days to look back
            criticality_filter: Optional criticality filter
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            tuple: (data_query, count_query)
        """
        offset = (page - 1) * limit
        
        # Base filters
        base_filters = [
            f'from(bucket: "{self.bucket}")',
            self.build_time_range_filter(period_days, start_date, end_date),
            self.build_measurement_filter()
        ]
        
        # Add criticality filter if specified
        if criticality_filter:
            base_filters.append(self.build_tag_filter("criticidade", criticality_filter))
        
        # Data query with pagination
        data_filters = base_filters + [
            '|> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")',
            '|> sort(columns: ["_time"], desc: true)',
            f'|> limit(n: {limit}, offset: {offset})',
            '|> yield(name: "analysis_history")'
        ]
        
        # Count query for total
        count_filters = base_filters + [
            self.build_field_filter("erro"),
            '|> count()',
            '|> yield(name: "total_count")'
        ]
        
        data_query = '\n  '.join(data_filters)
        count_query = '\n  '.join(count_filters)
        
        return data_query, count_query
    
    def get_health_check_query(self) -> str:
        """Get simple health check query."""
        return f'''
        from(bucket: "{self.bucket}")
          |> range(start: -1m)
          |> limit(n: 1)
        '''
    
    def optimize_query_performance(self, query: str) -> str:
        """
        Apply general performance optimizations to a query.
        
        Args:
            query: Original query
            
        Returns:
            str: Optimized query
        """
        # Add common optimizations
        optimizations = []
        
        # Ensure measurement filter comes early
        if '|> filter(fn: (r) => r._measurement ==' not in query:
            logger.warning("⚠️ Query sem filtro de measurement - pode ser lento")
        
        # Ensure time range is specified
        if '|> range(' not in query:
            logger.warning("⚠️ Query sem range de tempo - pode ser muito lento")
            optimizations.append("Adicionar range de tempo apropriado")
        
        # Check for unnecessary operations
        if '|> pivot(' in query and '|> group(' in query:
            logger.warning("⚠️ Query com pivot e group - verificar se ambos são necessários")
            optimizations.append("Revisar uso de pivot e group")
        
        if optimizations:
            logger.info(f"💡 Sugestões de otimização: {', '.join(optimizations)}")
        
        return query
    
    def get_query_stats(self, query: str) -> Dict[str, Any]:
        """
        Analyze query for performance characteristics.
        
        Args:
            query: Query to analyze
            
        Returns:
            Dict with query statistics
        """
        stats = {
            'has_time_range': '|> range(' in query,
            'has_measurement_filter': '|> filter(fn: (r) => r._measurement ==' in query,
            'has_field_filter': '|> filter(fn: (r) => r._field ==' in query,
            'has_tag_filter': any(f'r.{tag} ==' in query for tag in ['criticidade', 'origem', 'id_analise']),
            'has_limit': '|> limit(' in query,
            'has_sort': '|> sort(' in query,
            'has_group': '|> group(' in query,
            'has_pivot': '|> pivot(' in query,
            'estimated_performance': 'unknown'
        }
        
        # Estimate performance
        if stats['has_time_range'] and stats['has_measurement_filter']:
            if stats['has_field_filter'] or stats['has_tag_filter']:
                stats['estimated_performance'] = 'good'
            else:
                stats['estimated_performance'] = 'fair'
        else:
            stats['estimated_performance'] = 'poor'
        
        return stats


# Global query optimizer instance
_query_optimizer: Optional[QueryOptimizer] = None


def initialize_query_optimizer(bucket: str) -> QueryOptimizer:
    """
    Initialize global query optimizer.
    
    Args:
        bucket: InfluxDB bucket name
        
    Returns:
        QueryOptimizer: Initialized optimizer
    """
    global _query_optimizer
    
    _query_optimizer = QueryOptimizer(bucket)
    logger.info(f"✅ Query optimizer global inicializado para bucket: {bucket}")
    return _query_optimizer


def get_query_optimizer() -> Optional[QueryOptimizer]:
    """Get the global query optimizer instance."""
    return _query_optimizer