"""
Enhanced logging configuration for the feedback system.
Provides structured logging with context and performance metrics.
"""

import logging
import logging.handlers
import json
import time
import functools
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import contextmanager


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs with context.
    """
    
    def format(self, record):
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra context if available
        if hasattr(record, 'analysis_id'):
            log_entry['analysis_id'] = record.analysis_id
        
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
        
        if hasattr(record, 'duration_ms'):
            log_entry['duration_ms'] = record.duration_ms
        
        if hasattr(record, 'error_details'):
            log_entry['error_details'] = record.error_details
        
        if hasattr(record, 'user_action'):
            log_entry['user_action'] = record.user_action
        
        if hasattr(record, 'fields_modified'):
            log_entry['fields_modified'] = record.fields_modified
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(log_level: str = "INFO", log_file: str = "feedback_system.log"):
    """
    Setup enhanced logging configuration for the feedback system.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
    """
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler with simple format for development
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    
    # Set encoding for Windows compatibility
    if hasattr(console_handler.stream, 'reconfigure'):
        try:
            console_handler.stream.reconfigure(encoding='utf-8')
        except:
            pass  # Fallback for older Python versions or systems without reconfigure
    
    logger.addHandler(console_handler)
    
    # File handler with structured JSON format for production
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(StructuredFormatter())
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    
    # Separate error log file
    error_handler = logging.handlers.RotatingFileHandler(
        "feedback_system_errors.log",
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    error_handler.setFormatter(StructuredFormatter())
    error_handler.setLevel(logging.ERROR)
    logger.addHandler(error_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_operation(operation_name: str):
    """
    Decorator to log function operations with timing and context.
    
    Args:
        operation_name: Name of the operation being logged
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()
            
            # Extract analysis_id if available in arguments
            analysis_id = None
            if args and hasattr(args[0], '__dict__'):
                # Check if first arg has analysis_id attribute
                if hasattr(args[0], 'analysis_id'):
                    analysis_id = args[0].analysis_id
            
            # Check kwargs for analysis_id
            if 'analysis_id' in kwargs:
                analysis_id = kwargs['analysis_id']
            
            # Log operation start
            extra = {
                'operation': operation_name,
                'analysis_id': analysis_id
            }
            logger.info(f"🚀 Iniciando operação: {operation_name}", extra=extra)
            
            try:
                result = func(*args, **kwargs)
                
                # Calculate duration
                duration_ms = round((time.time() - start_time) * 1000, 2)
                
                # Log successful completion
                extra['duration_ms'] = duration_ms
                logger.info(f"✅ Operação concluída: {operation_name} em {duration_ms}ms", extra=extra)
                
                return result
                
            except Exception as e:
                # Calculate duration even for errors
                duration_ms = round((time.time() - start_time) * 1000, 2)
                
                # Log error with context
                extra.update({
                    'duration_ms': duration_ms,
                    'error_details': {
                        'type': type(e).__name__,
                        'message': str(e),
                        'args': list(args) if args else [],
                        'kwargs': kwargs if kwargs else {}
                    }
                })
                logger.error(f"❌ Erro na operação: {operation_name} após {duration_ms}ms - {e}", extra=extra, exc_info=True)
                raise
        
        return wrapper
    return decorator


def log_user_action(action: str, analysis_id: Optional[str] = None, **context):
    """
    Log user actions with context for audit trail.
    
    Args:
        action: Description of user action
        analysis_id: Analysis ID if applicable
        **context: Additional context information
    """
    logger = get_logger('user_actions')
    
    extra = {
        'user_action': action,
        'analysis_id': analysis_id,
        **context
    }
    
    logger.info(f"👤 Ação do usuário: {action}", extra=extra)


def log_database_operation(operation: str, analysis_id: Optional[str] = None, success: bool = True, **context):
    """
    Log database operations with detailed context.
    
    Args:
        operation: Type of database operation (insert, update, query, etc.)
        analysis_id: Analysis ID if applicable
        success: Whether operation was successful
        **context: Additional context (fields_modified, query_params, etc.)
    """
    logger = get_logger('database_operations')
    
    extra = {
        'operation': f"database_{operation}",
        'analysis_id': analysis_id,
        **context
    }
    
    if success:
        logger.info(f"💾 Operação DB bem-sucedida: {operation}", extra=extra)
    else:
        logger.error(f"💥 Falha na operação DB: {operation}", extra=extra)


@contextmanager
def performance_monitor(operation_name: str, **context):
    """
    Context manager for monitoring operation performance.
    
    Args:
        operation_name: Name of the operation
        **context: Additional context information
    """
    logger = get_logger('performance')
    start_time = time.time()
    
    try:
        yield
        
        duration_ms = round((time.time() - start_time) * 1000, 2)
        extra = {
            'operation': operation_name,
            'duration_ms': duration_ms,
            **context
        }
        
        # Log performance warning if operation takes too long
        if duration_ms > 5000:  # 5 seconds
            logger.warning(f"⚠️ Operação lenta: {operation_name} levou {duration_ms}ms", extra=extra)
        else:
            logger.debug(f"⏱️ Performance: {operation_name} - {duration_ms}ms", extra=extra)
            
    except Exception as e:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        extra = {
            'operation': operation_name,
            'duration_ms': duration_ms,
            'error_details': {
                'type': type(e).__name__,
                'message': str(e)
            },
            **context
        }
        logger.error(f"💥 Erro em operação monitorada: {operation_name} após {duration_ms}ms", extra=extra, exc_info=True)
        raise


class MetricsCollector:
    """
    Simple metrics collector for basic performance monitoring.
    """
    
    def __init__(self):
        self.metrics = {
            'operations_count': {},
            'operation_durations': {},
            'error_counts': {},
            'last_reset': datetime.now()
        }
        self.logger = get_logger('metrics')
    
    def record_operation(self, operation: str, duration_ms: float, success: bool = True):
        """Record an operation metric."""
        # Count operations
        if operation not in self.metrics['operations_count']:
            self.metrics['operations_count'][operation] = 0
        self.metrics['operations_count'][operation] += 1
        
        # Track durations
        if operation not in self.metrics['operation_durations']:
            self.metrics['operation_durations'][operation] = []
        self.metrics['operation_durations'][operation].append(duration_ms)
        
        # Count errors
        if not success:
            if operation not in self.metrics['error_counts']:
                self.metrics['error_counts'][operation] = 0
            self.metrics['error_counts'][operation] += 1
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics."""
        summary = {
            'collection_period': {
                'start': self.metrics['last_reset'].isoformat(),
                'end': datetime.now().isoformat()
            },
            'operations': {}
        }
        
        for operation, count in self.metrics['operations_count'].items():
            durations = self.metrics['operation_durations'].get(operation, [])
            errors = self.metrics['error_counts'].get(operation, 0)
            
            summary['operations'][operation] = {
                'total_count': count,
                'error_count': errors,
                'success_rate': (count - errors) / count if count > 0 else 0,
                'avg_duration_ms': sum(durations) / len(durations) if durations else 0,
                'max_duration_ms': max(durations) if durations else 0,
                'min_duration_ms': min(durations) if durations else 0
            }
        
        return summary
    
    def log_metrics_summary(self):
        """Log current metrics summary."""
        summary = self.get_metrics_summary()
        self.logger.info("📊 Resumo de métricas de performance", extra={'metrics_summary': summary})
    
    def reset_metrics(self):
        """Reset all collected metrics."""
        self.metrics = {
            'operations_count': {},
            'operation_durations': {},
            'error_counts': {},
            'last_reset': datetime.now()
        }
        self.logger.info("🔄 Métricas resetadas")


# Global metrics collector instance
metrics_collector = MetricsCollector()