"""
Rate limiting service to prevent API abuse and improve system stability.
Implements token bucket and sliding window algorithms.
"""

import time
import threading
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque
from functools import wraps
from flask import request, jsonify
from src.utils.logging_config import get_logger, log_operation

logger = get_logger(__name__)


class TokenBucket:
    """
    Token bucket rate limiter implementation.
    Allows burst traffic up to bucket capacity.
    """
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens in bucket
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            bool: True if tokens were consumed, False if not enough tokens
        """
        with self.lock:
            now = time.time()
            
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    def get_status(self) -> Dict[str, float]:
        """Get current bucket status."""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            current_tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            
            return {
                'tokens': current_tokens,
                'capacity': self.capacity,
                'refill_rate': self.refill_rate,
                'fill_percentage': (current_tokens / self.capacity) * 100
            }


class SlidingWindowLimiter:
    """
    Sliding window rate limiter implementation.
    Tracks requests in a time window with precise timing.
    """
    
    def __init__(self, max_requests: int, window_seconds: int):
        """
        Initialize sliding window limiter.
        
        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
        self.lock = threading.Lock()
    
    def is_allowed(self) -> bool:
        """
        Check if request is allowed under rate limit.
        
        Returns:
            bool: True if request is allowed
        """
        with self.lock:
            now = time.time()
            
            # Remove old requests outside window
            while self.requests and self.requests[0] <= now - self.window_seconds:
                self.requests.popleft()
            
            # Check if under limit
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            
            return False
    
    def get_status(self) -> Dict[str, any]:
        """Get current limiter status."""
        with self.lock:
            now = time.time()
            
            # Clean old requests
            while self.requests and self.requests[0] <= now - self.window_seconds:
                self.requests.popleft()
            
            return {
                'current_requests': len(self.requests),
                'max_requests': self.max_requests,
                'window_seconds': self.window_seconds,
                'usage_percentage': (len(self.requests) / self.max_requests) * 100
            }


class RateLimiterService:
    """
    Comprehensive rate limiting service with multiple algorithms.
    Supports per-IP, per-endpoint, and global rate limiting.
    """
    
    def __init__(self):
        """Initialize rate limiter service."""
        self.limiters: Dict[str, Dict[str, any]] = defaultdict(dict)
        self.global_limiter = None
        self.lock = threading.RLock()
        
        # Rate limiting statistics
        self.stats = {
            'requests_allowed': 0,
            'requests_blocked': 0,
            'unique_ips': set(),
            'blocked_ips': defaultdict(int)
        }
        
        logger.info("✅ RateLimiterService inicializado")
    
    def configure_endpoint_limit(self, endpoint: str, max_requests: int, 
                                window_seconds: int, algorithm: str = "sliding_window"):
        """
        Configure rate limit for specific endpoint.
        
        Args:
            endpoint: Endpoint path (e.g., "/api/metrics")
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
            algorithm: "sliding_window" or "token_bucket"
        """
        with self.lock:
            if algorithm == "token_bucket":
                # For token bucket, treat max_requests as capacity and calculate refill rate
                refill_rate = max_requests / window_seconds
                self.limiters[endpoint]['config'] = {
                    'type': 'token_bucket',
                    'capacity': max_requests,
                    'refill_rate': refill_rate
                }
            else:
                self.limiters[endpoint]['config'] = {
                    'type': 'sliding_window',
                    'max_requests': max_requests,
                    'window_seconds': window_seconds
                }
        
        logger.info(f"✅ Rate limit configurado para {endpoint}: {max_requests} req/{window_seconds}s ({algorithm})")
    
    def configure_global_limit(self, max_requests: int, window_seconds: int):
        """
        Configure global rate limit across all endpoints.
        
        Args:
            max_requests: Maximum requests allowed globally
            window_seconds: Time window in seconds
        """
        self.global_limiter = SlidingWindowLimiter(max_requests, window_seconds)
        logger.info(f"✅ Rate limit global configurado: {max_requests} req/{window_seconds}s")
    
    def _get_client_id(self) -> str:
        """Get client identifier (IP address)."""
        # Try to get real IP from headers (for proxy/load balancer scenarios)
        client_ip = request.headers.get('X-Forwarded-For', 
                   request.headers.get('X-Real-IP', 
                   request.remote_addr))
        
        # Handle comma-separated IPs from X-Forwarded-For
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        
        return client_ip or 'unknown'
    
    @log_operation("rate_limit_check")
    def is_allowed(self, endpoint: str) -> Tuple[bool, Dict[str, any]]:
        """
        Check if request is allowed under rate limits.
        
        Args:
            endpoint: Endpoint being accessed
            
        Returns:
            Tuple of (is_allowed, limit_info)
        """
        client_id = self._get_client_id()
        
        # Track unique IPs
        self.stats['unique_ips'].add(client_id)
        
        # Check global limit first
        if self.global_limiter and not self.global_limiter.is_allowed():
            self.stats['requests_blocked'] += 1
            self.stats['blocked_ips'][client_id] += 1
            
            logger.warning(f"🚫 Rate limit global excedido para IP: {client_id}")
            
            return False, {
                'limit_type': 'global',
                'client_id': client_id,
                'global_status': self.global_limiter.get_status()
            }
        
        # Check endpoint-specific limit
        if endpoint in self.limiters:
            endpoint_config = self.limiters[endpoint]['config']
            
            # Get or create limiter for this client+endpoint
            limiter_key = f"{client_id}:{endpoint}"
            
            if limiter_key not in self.limiters[endpoint]:
                if endpoint_config['type'] == 'token_bucket':
                    self.limiters[endpoint][limiter_key] = TokenBucket(
                        endpoint_config['capacity'],
                        endpoint_config['refill_rate']
                    )
                else:
                    self.limiters[endpoint][limiter_key] = SlidingWindowLimiter(
                        endpoint_config['max_requests'],
                        endpoint_config['window_seconds']
                    )
            
            limiter = self.limiters[endpoint][limiter_key]
            
            # Check endpoint limit
            if endpoint_config['type'] == 'token_bucket':
                allowed = limiter.consume()
            else:
                allowed = limiter.is_allowed()
            
            if not allowed:
                self.stats['requests_blocked'] += 1
                self.stats['blocked_ips'][client_id] += 1
                
                logger.warning(f"🚫 Rate limit do endpoint {endpoint} excedido para IP: {client_id}")
                
                return False, {
                    'limit_type': 'endpoint',
                    'endpoint': endpoint,
                    'client_id': client_id,
                    'endpoint_status': limiter.get_status()
                }
        
        # Request is allowed
        self.stats['requests_allowed'] += 1
        
        logger.debug(f"✅ Request permitido para {endpoint} do IP: {client_id}")
        
        return True, {
            'limit_type': 'none',
            'client_id': client_id
        }
    
    def get_stats(self) -> Dict[str, any]:
        """Get rate limiting statistics."""
        total_requests = self.stats['requests_allowed'] + self.stats['requests_blocked']
        block_rate = (self.stats['requests_blocked'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'requests_allowed': self.stats['requests_allowed'],
            'requests_blocked': self.stats['requests_blocked'],
            'total_requests': total_requests,
            'block_rate_percent': round(block_rate, 2),
            'unique_ips_count': len(self.stats['unique_ips']),
            'top_blocked_ips': dict(sorted(
                self.stats['blocked_ips'].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10])
        }
    
    def get_client_status(self, client_id: str = None) -> Dict[str, any]:
        """
        Get rate limit status for specific client.
        
        Args:
            client_id: Client ID (uses current request IP if None)
            
        Returns:
            Dict with client's rate limit status
        """
        if client_id is None:
            client_id = self._get_client_id()
        
        status = {
            'client_id': client_id,
            'global_limit': None,
            'endpoint_limits': {}
        }
        
        # Global limit status
        if self.global_limiter:
            status['global_limit'] = self.global_limiter.get_status()
        
        # Endpoint limits status
        for endpoint, endpoint_data in self.limiters.items():
            if 'config' not in endpoint_data:
                continue
                
            limiter_key = f"{client_id}:{endpoint}"
            if limiter_key in endpoint_data:
                limiter = endpoint_data[limiter_key]
                status['endpoint_limits'][endpoint] = limiter.get_status()
        
        return status
    
    def reset_client_limits(self, client_id: str):
        """
        Reset rate limits for specific client.
        
        Args:
            client_id: Client ID to reset
        """
        with self.lock:
            for endpoint, endpoint_data in self.limiters.items():
                limiter_key = f"{client_id}:{endpoint}"
                if limiter_key in endpoint_data:
                    del endpoint_data[limiter_key]
        
        logger.info(f"🔄 Rate limits resetados para cliente: {client_id}")


# Global rate limiter instance
_rate_limiter: Optional[RateLimiterService] = None


def initialize_rate_limiter() -> RateLimiterService:
    """Initialize global rate limiter service."""
    global _rate_limiter
    
    if _rate_limiter is not None:
        logger.warning("⚠️ Rate limiter já inicializado")
        return _rate_limiter
    
    _rate_limiter = RateLimiterService()
    
    # Configure default limits
    _rate_limiter.configure_global_limit(max_requests=1000, window_seconds=60)  # 1000 req/min global
    _rate_limiter.configure_endpoint_limit("/api/metrics", max_requests=30, window_seconds=60)  # 30 req/min
    _rate_limiter.configure_endpoint_limit("/api/analysis-history", max_requests=20, window_seconds=60)  # 20 req/min
    _rate_limiter.configure_endpoint_limit("/analisar_logs", max_requests=10, window_seconds=60)  # 10 req/min
    _rate_limiter.configure_endpoint_limit("/classificar_solucao", max_requests=50, window_seconds=60)  # 50 req/min
    
    logger.info("✅ Rate limiter global inicializado com limites padrão")
    return _rate_limiter


def get_rate_limiter() -> Optional[RateLimiterService]:
    """Get the global rate limiter instance."""
    return _rate_limiter


# Flask decorator for rate limiting
def rate_limit(endpoint: str = None):
    """
    Decorator to apply rate limiting to Flask routes.
    
    Args:
        endpoint: Endpoint name (uses request path if None)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter = get_rate_limiter()
            if not limiter:
                return func(*args, **kwargs)
            
            # Determine endpoint
            endpoint_name = endpoint or request.endpoint or request.path
            
            # Check rate limit
            allowed, limit_info = limiter.is_allowed(endpoint_name)
            
            if not allowed:
                # Return rate limit exceeded response
                response_data = {
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "limit_info": {
                        "type": limit_info.get('limit_type'),
                        "client_id": limit_info.get('client_id')
                    }
                }
                
                # Add retry-after header for better client behavior
                if limit_info.get('endpoint_status'):
                    status = limit_info['endpoint_status']
                    if 'window_seconds' in status:
                        response = jsonify(response_data)
                        response.headers['Retry-After'] = str(status['window_seconds'])
                        return response, 429
                
                return jsonify(response_data), 429
            
            # Request is allowed, proceed
            return func(*args, **kwargs)
        
        return wrapper
    return decorator