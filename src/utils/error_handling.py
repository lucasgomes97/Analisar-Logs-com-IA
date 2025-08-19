"""
Robust error handling utilities for the feedback system.
Implements retry logic, fallbacks, validation, and sanitization.
"""

import time
import logging
import functools
import re
from typing import Any, Callable, Dict, Optional, Union, List
from datetime import datetime
# InfluxDB removido - usando PostgreSQL
from src.utils.logging_config import get_logger, log_operation

logger = get_logger(__name__)


class RetryConfig:
    """Configuration for retry logic."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class ErrorHandler:
    """Centralized error handling with retry logic and fallbacks."""
    
    # Default retry configurations for different operations
    RETRY_CONFIGS = {
        'influxdb_write': RetryConfig(max_attempts=3, base_delay=1.0, max_delay=10.0),
        'influxdb_read': RetryConfig(max_attempts=2, base_delay=0.5, max_delay=5.0),
        'api_request': RetryConfig(max_attempts=2, base_delay=0.5, max_delay=3.0),
        'default': RetryConfig(max_attempts=2, base_delay=1.0, max_delay=5.0)
    }
    
    @staticmethod
    def with_retry(
        operation_type: str = 'default',
        retry_config: Optional[RetryConfig] = None,
        fallback_value: Any = None,
        reraise_exceptions: Optional[List[type]] = None
    ):
        """
        Decorator for adding retry logic to operations.
        
        Args:
            operation_type: Type of operation for default config
            retry_config: Custom retry configuration
            fallback_value: Value to return if all retries fail
            reraise_exceptions: List of exception types to reraise immediately
            
        Requirements: 5.4, 5.5 - Retry logic for InfluxDB operations and fallbacks
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                config = retry_config or ErrorHandler.RETRY_CONFIGS.get(
                    operation_type, 
                    ErrorHandler.RETRY_CONFIGS['default']
                )
                
                last_exception = None
                
                for attempt in range(config.max_attempts):
                    try:
                        return func(*args, **kwargs)
                        
                    except Exception as e:
                        last_exception = e
                        
                        # Reraise certain exceptions immediately
                        if reraise_exceptions and type(e) in reraise_exceptions:
                            logger.error(f"❌ Reraising {type(e).__name__} immediately: {e}")
                            raise
                        
                        # Don't retry on the last attempt
                        if attempt == config.max_attempts - 1:
                            break
                        
                        # Calculate delay with exponential backoff
                        delay = min(
                            config.base_delay * (config.exponential_base ** attempt),
                            config.max_delay
                        )
                        
                        # Add jitter to prevent thundering herd
                        if config.jitter:
                            import random
                            delay *= (0.5 + random.random() * 0.5)
                        
                        logger.warning(
                            f"⚠️ Tentativa {attempt + 1}/{config.max_attempts} falhou para {func.__name__}: {e}. "
                            f"Tentando novamente em {delay:.2f}s..."
                        )
                        
                        time.sleep(delay)
                
                # All retries failed
                logger.error(
                    f"❌ Todas as {config.max_attempts} tentativas falharam para {func.__name__}: {last_exception}"
                )
                
                if fallback_value is not None:
                    logger.info(f"🔄 Usando valor de fallback para {func.__name__}")
                    return fallback_value
                
                raise last_exception
            
            return wrapper
        return decorator
    
    @staticmethod
    def handle_database_error(e: Exception, operation: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle database specific errors with appropriate responses.
        
        Args:
            e: Exception that occurred
            operation: Operation being performed
            context: Additional context information
            
        Returns:
            Dictionary with error details and user message
            
        Requirements: 8.4 - Clear error messages for users
        """
        context = context or {}
        
        error_details = {
            'type': type(e).__name__,
            'message': str(e),
            'operation': operation,
            'timestamp': datetime.now().isoformat(),
            'context': context
        }
        
        # Determine user-friendly message based on error type
        if "timeout" in str(e).lower():
            user_message = "O sistema está temporariamente lento. Tente novamente em alguns segundos."
        elif "unauthorized" in str(e).lower() or "authentication" in str(e).lower():
            user_message = "Erro de autenticação com o banco de dados. Contate o administrador."
        elif "not found" in str(e).lower():
            user_message = "Dados não encontrados. Verifique se o ID está correto."
        elif "connection" in str(e).lower():
            user_message = "Erro de conexão com o banco de dados. Tente novamente."
        else:
            user_message = "Erro temporário no banco de dados. Tente novamente."
        
        error_details['user_message'] = user_message
        
        # Log detailed error for debugging (Requirement 7.4)
        logger.error(
            f"❌ Erro {operation}: {e}",
            extra={
                'operation': operation,
                'error_type': type(e).__name__,
                'context': context
            },
            exc_info=True
        )
        
        return error_details
    
    @staticmethod
    def handle_database_error(e: Exception, operation: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle generic database errors with appropriate responses.
        Works with both InfluxDB and PostgreSQL errors.
        
        Args:
            e: Exception that occurred
            operation: Operation being performed
            context: Additional context information
            
        Returns:
            Dictionary with error details and user message
        """
        context = context or {}
        
        error_details = {
            'type': type(e).__name__,
            'message': str(e),
            'operation': operation,
            'timestamp': datetime.now().isoformat(),
            'context': context
        }
        
        # Determine user-friendly message based on error type and message
        error_msg_lower = str(e).lower()
        
        if "timeout" in error_msg_lower or "connection" in error_msg_lower:
            user_message = "O sistema está temporariamente lento. Tente novamente em alguns segundos."
        elif "unauthorized" in error_msg_lower or "authentication" in error_msg_lower or "permission" in error_msg_lower:
            user_message = "Erro de autenticação com o banco de dados. Contate o administrador."
        elif "not found" in error_msg_lower or "does not exist" in error_msg_lower:
            user_message = "Dados não encontrados. Verifique se o ID está correto."
        elif "duplicate" in error_msg_lower or "already exists" in error_msg_lower:
            user_message = "Registro já existe no sistema."
        elif "constraint" in error_msg_lower or "foreign key" in error_msg_lower:
            user_message = "Erro de integridade dos dados. Verifique as informações fornecidas."
        else:
            user_message = "Erro temporário no banco de dados. Tente novamente."
        
        error_details['user_message'] = user_message
        
        # Log detailed error for debugging
        logger.error(
            f"❌ Erro {operation}: {e}",
            extra={
                'operation': operation,
                'error_type': type(e).__name__,
                'context': context
            },
            exc_info=True
        )
        
        return error_details
    
    @staticmethod
    def handle_api_error(e: Exception, endpoint: str, request_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle API specific errors with appropriate HTTP responses.
        
        Args:
            e: Exception that occurred
            endpoint: API endpoint where error occurred
            request_data: Request data (sanitized)
            
        Returns:
            Dictionary with error details and HTTP status
            
        Requirements: 5.4, 5.5 - Appropriate HTTP error responses
        """
        request_data = request_data or {}
        
        # Sanitize request data before logging
        sanitized_data = DataSanitizer.sanitize_dict(request_data)
        
        error_details = {
            'type': type(e).__name__,
            'message': str(e),
            'endpoint': endpoint,
            'timestamp': datetime.now().isoformat(),
            'request_data': sanitized_data
        }
        
        # Determine HTTP status and user message
        if isinstance(e, ValueError):
            status_code = 400
            user_message = f"Dados inválidos: {str(e)}"
        elif isinstance(e, KeyError):
            status_code = 400
            user_message = "Parâmetros obrigatórios ausentes na requisição."
        elif "database" in str(type(e)).lower() or "sql" in str(type(e)).lower():
            if "not found" in str(e).lower():
                status_code = 404
                user_message = "Recurso não encontrado."
            else:
                status_code = 503
                user_message = "Serviço temporariamente indisponível. Tente novamente."
        else:
            status_code = 500
            user_message = "Erro interno do servidor. Tente novamente."
        
        error_details.update({
            'status_code': status_code,
            'user_message': user_message
        })
        
        # Log API error with context
        logger.error(
            f"❌ Erro API {endpoint}: {e}",
            extra={
                'endpoint': endpoint,
                'status_code': status_code,
                'error_type': type(e).__name__,
                'request_data': sanitized_data
            },
            exc_info=True
        )
        
        return error_details


class InputValidator:
    """Input validation utilities with comprehensive checks."""
    
    # Validation patterns
    UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    
    @staticmethod
    def validate_analysis_id(analysis_id: str) -> str:
        """
        Validate analysis ID format.
        
        Args:
            analysis_id: ID to validate
            
        Returns:
            Validated and cleaned ID
            
        Raises:
            ValueError: If ID is invalid
            
        Requirements: 5.4 - Input validation for all endpoints
        """
        if not analysis_id:
            raise ValueError("ID da análise é obrigatório")
        
        # Clean and validate
        cleaned_id = str(analysis_id).strip()
        
        if not InputValidator.UUID_PATTERN.match(cleaned_id):
            raise ValueError("ID da análise deve ser um UUID válido")
        
        return cleaned_id
    
    @staticmethod
    def validate_classification_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate classification request data.
        
        Args:
            data: Request data to validate
            
        Returns:
            Validated and cleaned data
            
        Raises:
            ValueError: If data is invalid
            
        Requirements: 5.4 - Input validation for classification endpoint
        """
        if not isinstance(data, dict):
            raise ValueError("Dados devem ser um objeto JSON válido")
        
        # Required fields
        required_fields = ['id', 'solucao_valida']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Campo '{field}' é obrigatório")
        
        validated_data = {}
        
        # Validate analysis ID
        validated_data['id'] = InputValidator.validate_analysis_id(data['id'])
        
        # Validate solution validity
        solucao_valida = data['solucao_valida']
        if isinstance(solucao_valida, str):
            if solucao_valida.lower() in ['true', '1', 'yes', 'sim']:
                validated_data['solucao_valida'] = True
            elif solucao_valida.lower() in ['false', '0', 'no', 'nao', 'não']:
                validated_data['solucao_valida'] = False
            else:
                raise ValueError("Campo 'solucao_valida' deve ser true ou false")
        elif isinstance(solucao_valida, bool):
            validated_data['solucao_valida'] = solucao_valida
        else:
            raise ValueError("Campo 'solucao_valida' deve ser boolean ou string")
        
        # Validate edited solution (optional)
        if 'solucao_editada' in data:
            solucao_editada = data['solucao_editada']
            if solucao_editada is not None:
                if not isinstance(solucao_editada, str):
                    raise ValueError("Campo 'solucao_editada' deve ser string")
                
                # Clean and validate length
                cleaned_solution = str(solucao_editada).strip()
                if len(cleaned_solution) > 5000:  # Reasonable limit
                    raise ValueError("Solução editada muito longa (máximo 5000 caracteres)")
                
                validated_data['solucao_editada'] = cleaned_solution if cleaned_solution else None
            else:
                validated_data['solucao_editada'] = None
        
        return validated_data
    
    @staticmethod
    def validate_log_text(log_text: str) -> str:
        """
        Validate and clean log text input.
        
        Args:
            log_text: Log text to validate
            
        Returns:
            Cleaned log text
            
        Raises:
            ValueError: If log text is invalid
            
        Requirements: 5.4 - Input validation for log analysis
        """
        if not log_text:
            raise ValueError("Texto do log é obrigatório")
        
        # Clean and validate
        cleaned_log = str(log_text).strip()
        
        if len(cleaned_log) < 10:
            raise ValueError("Log muito curto (mínimo 10 caracteres)")
        
        if len(cleaned_log) > 50000:  # Reasonable limit
            raise ValueError("Log muito longo (máximo 50.000 caracteres)")
        
        return cleaned_log
    
    @staticmethod
    def validate_dashboard_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate dashboard filter parameters.
        
        Args:
            filters: Filter parameters to validate
            
        Returns:
            Validated filters
            
        Raises:
            ValueError: If filters are invalid
            
        Requirements: 5.4 - Input validation for dashboard endpoints
        """
        validated_filters = {}
        
        # Validate period
        if 'period' in filters:
            period = filters['period']
            try:
                period_int = int(period)
                if period_int not in [1, 7, 30, 90, 365]:
                    raise ValueError("Período deve ser 1, 7, 30, 90 ou 365 dias")
                validated_filters['period'] = period_int
            except (ValueError, TypeError):
                raise ValueError("Período deve ser um número inteiro válido")
        
        # Validate criticality
        if 'criticality' in filters:
            criticality = str(filters['criticality']).lower().strip()
            if criticality and criticality not in ['baixa', 'media', 'alta']:
                raise ValueError("Criticidade deve ser 'baixa', 'media' ou 'alta'")
            validated_filters['criticality'] = criticality if criticality else None
        
        # Validate pagination
        if 'page' in filters:
            try:
                page = int(filters['page'])
                if page < 1:
                    raise ValueError("Página deve ser maior que 0")
                validated_filters['page'] = page
            except (ValueError, TypeError):
                raise ValueError("Página deve ser um número inteiro válido")
        
        if 'limit' in filters:
            try:
                limit = int(filters['limit'])
                if limit < 1 or limit > 100:
                    raise ValueError("Limite deve ser entre 1 e 100")
                validated_filters['limit'] = limit
            except (ValueError, TypeError):
                raise ValueError("Limite deve ser um número inteiro válido")
        
        return validated_filters


class DataSanitizer:
    """Data sanitization utilities for secure logging and storage."""
    
    # Patterns for sensitive data detection
    SENSITIVE_PATTERNS = {
        'password': re.compile(r'(password|senha|pwd)["\s]*[:=]["\s]*([^"\s,}]+)', re.IGNORECASE),
        'token': re.compile(r'(token|key|secret)["\s]*[:=]["\s]*([^"\s,}]+)', re.IGNORECASE),
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'ip_address': re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
        'phone': re.compile(r'\b(?:\+?55\s?)?(?:\(?[1-9]{2}\)?\s?)?(?:9\s?)?[0-9]{4}[-\s]?[0-9]{4}\b'),
        'cpf': re.compile(r'\b[0-9]{3}\.?[0-9]{3}\.?[0-9]{3}[-]?[0-9]{2}\b'),
        'cnpj': re.compile(r'\b[0-9]{2}\.?[0-9]{3}\.?[0-9]{3}/?[0-9]{4}[-]?[0-9]{2}\b')
    }
    
    @staticmethod
    def sanitize_text(text: str, mask_char: str = '*') -> str:
        """
        Sanitize text by masking sensitive information.
        
        Args:
            text: Text to sanitize
            mask_char: Character to use for masking
            
        Returns:
            Sanitized text
            
        Requirements: 7.4 - Sanitize sensitive data in logs
        """
        if not text:
            return text
        
        sanitized = str(text)
        
        # Replace sensitive patterns
        for pattern_name, pattern in DataSanitizer.SENSITIVE_PATTERNS.items():
            if pattern_name in ['password', 'token']:
                # For key-value patterns, mask the value
                sanitized = pattern.sub(
                    lambda m: f"{m.group(1)}:{mask_char * 8}",
                    sanitized
                )
            else:
                # For direct patterns, mask the entire match
                sanitized = pattern.sub(
                    lambda m: mask_char * len(m.group(0)),
                    sanitized
                )
        
        return sanitized
    
    @staticmethod
    def sanitize_dict(data: Dict[str, Any], mask_char: str = '*') -> Dict[str, Any]:
        """
        Sanitize dictionary by masking sensitive values.
        
        Args:
            data: Dictionary to sanitize
            mask_char: Character to use for masking
            
        Returns:
            Sanitized dictionary
            
        Requirements: 7.4 - Sanitize sensitive data in logs
        """
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        
        # Sensitive keys to mask completely
        sensitive_keys = {
            'password', 'senha', 'pwd', 'token', 'key', 'secret',
            'authorization', 'auth', 'credential', 'api_key'
        }
        
        for key, value in data.items():
            key_lower = str(key).lower()
            
            if key_lower in sensitive_keys:
                # Mask sensitive keys completely
                sanitized[key] = mask_char * 8
            elif isinstance(value, str):
                # Sanitize string values
                sanitized[key] = DataSanitizer.sanitize_text(value, mask_char)
            elif isinstance(value, dict):
                # Recursively sanitize nested dictionaries
                sanitized[key] = DataSanitizer.sanitize_dict(value, mask_char)
            elif isinstance(value, list):
                # Sanitize list items
                sanitized[key] = [
                    DataSanitizer.sanitize_text(str(item), mask_char) if isinstance(item, str)
                    else DataSanitizer.sanitize_dict(item, mask_char) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                # Keep other types as-is
                sanitized[key] = value
        
        return sanitized
    
    @staticmethod
    def sanitize_log_message(message: str) -> str:
        """
        Sanitize log message for safe logging.
        
        Args:
            message: Log message to sanitize
            
        Returns:
            Sanitized log message
            
        Requirements: 7.4 - Sanitize sensitive data in logs
        """
        return DataSanitizer.sanitize_text(message)


class ConnectionFallback:
    """Fallback mechanisms for connection failures."""
    
    @staticmethod
    def get_cached_metrics() -> Dict[str, Any]:
        """
        Get cached metrics when InfluxDB is unavailable.
        
        Returns:
            Dictionary with fallback metrics
            
        Requirements: 5.5 - Fallbacks for connection failures
        """
        return {
            'error_count_by_criticality': {
                'baixa': 0,
                'media': 0,
                'alta': 0
            },
            'ai_accuracy_rate': 0.0,
            'average_resolution_time': 0.0,
            'top_error_sources': [],
            'total_analyses': 0,
            'cache_notice': 'Dados em cache - serviço temporariamente indisponível'
        }
    
    @staticmethod
    def get_cached_history() -> Dict[str, Any]:
        """
        Get cached history when InfluxDB is unavailable.
        
        Returns:
            Dictionary with fallback history
            
        Requirements: 5.5 - Fallbacks for connection failures
        """
        return {
            'analyses': [],
            'total_count': 0,
            'page': 1,
            'total_pages': 0,
            'cache_notice': 'Histórico indisponível - serviço temporariamente indisponível'
        }


# Convenience decorators for common operations
def with_database_retry(func):
    """Decorator for database operations with retry logic."""
    return ErrorHandler.with_retry('postgres_write')(func)


def with_api_retry(func):
    """Decorator for API operations with retry logic."""
    return ErrorHandler.with_retry('api_request')(func)


def with_fallback(fallback_value):
    """Decorator to provide fallback value on failure."""
    def decorator(func):
        return ErrorHandler.with_retry(fallback_value=fallback_value)(func)
    return decorator