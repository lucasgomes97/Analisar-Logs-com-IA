"""
Cache service for dashboard metrics to improve performance.
Implements in-memory caching with TTL and background refresh.
"""

import threading
import time
import json
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from src.utils.logging_config import get_logger, log_operation, performance_monitor

logger = get_logger(__name__)


class CacheEntry:
    """Represents a cached entry with TTL and metadata."""
    
    def __init__(self, data: Any, ttl_seconds: int = 300):
        """
        Initialize cache entry.
        
        Args:
            data: Data to cache
            ttl_seconds: Time to live in seconds (default: 5 minutes)
        """
        self.data = data
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds
        self.access_count = 0
        self.last_accessed = time.time()
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return time.time() - self.created_at > self.ttl_seconds
    
    def is_stale(self, stale_threshold: int = 60) -> bool:
        """Check if cache entry is stale (older than threshold but not expired)."""
        age = time.time() - self.created_at
        return age > stale_threshold and not self.is_expired()
    
    def access(self) -> Any:
        """Access cached data and update statistics."""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.data
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache entry statistics."""
        return {
            'created_at': datetime.fromtimestamp(self.created_at).isoformat(),
            'age_seconds': time.time() - self.created_at,
            'ttl_seconds': self.ttl_seconds,
            'access_count': self.access_count,
            'last_accessed': datetime.fromtimestamp(self.last_accessed).isoformat(),
            'is_expired': self.is_expired(),
            'is_stale': self.is_stale()
        }


class MetricsCacheService:
    """
    Cache service for dashboard metrics with background refresh.
    Provides fast access to frequently requested metrics.
    """
    
    def __init__(self, default_ttl: int = 300, max_entries: int = 100):
        """
        Initialize cache service.
        
        Args:
            default_ttl: Default TTL for cache entries in seconds
            max_entries: Maximum number of cache entries
        """
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        
        # Cache storage and locks
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        
        # Background refresh configuration
        self._refresh_functions: Dict[str, Callable] = {}
        self._refresh_thread = None
        self._stop_refresh = threading.Event()
        
        # Cache statistics
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'refreshes': 0,
            'errors': 0
        }
        
        # Start background refresh thread
        self._start_refresh_thread()
        
        logger.info(f"✅ MetricsCacheService inicializado - TTL: {default_ttl}s, Max entries: {max_entries}")
    
    @log_operation("cache_get")
    def get(self, key: str) -> Optional[Any]:
        """
        Get data from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached data or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats['misses'] += 1
                logger.debug(f"🔍 Cache miss para chave: {key}")
                return None
            
            if entry.is_expired():
                # Remove expired entry
                del self._cache[key]
                self._stats['misses'] += 1
                logger.debug(f"⏰ Cache expirado para chave: {key}")
                return None
            
            # Cache hit
            self._stats['hits'] += 1
            data = entry.access()
            
            # Log stale data warning
            if entry.is_stale():
                logger.debug(f"⚠️ Cache stale para chave: {key} (idade: {entry.get_stats()['age_seconds']:.1f}s)")
            
            logger.debug(f"✅ Cache hit para chave: {key} (acessos: {entry.access_count})")
            return data
    
    @log_operation("cache_set")
    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """
        Set data in cache.
        
        Args:
            key: Cache key
            data: Data to cache
            ttl: Time to live in seconds (uses default if None)
            
        Returns:
            bool: True if successfully cached
        """
        try:
            with performance_monitor("cache_set", key=key):
                ttl = ttl or self.default_ttl
                
                with self._lock:
                    # Check if we need to evict entries
                    if len(self._cache) >= self.max_entries and key not in self._cache:
                        self._evict_lru()
                    
                    # Create cache entry
                    entry = CacheEntry(data, ttl)
                    self._cache[key] = entry
                    
                    logger.debug(f"💾 Dados cacheados para chave: {key} (TTL: {ttl}s)")
                    return True
                    
        except Exception as e:
            self._stats['errors'] += 1
            logger.error(f"❌ Erro ao cachear dados para chave {key}: {e}")
            return False
    
    def _evict_lru(self):
        """Evict least recently used entry."""
        if not self._cache:
            return
        
        # Find LRU entry
        lru_key = min(self._cache.keys(), 
                     key=lambda k: self._cache[k].last_accessed)
        
        del self._cache[lru_key]
        self._stats['evictions'] += 1
        
        logger.debug(f"🗑️ Cache LRU eviction para chave: {lru_key}")
    
    @log_operation("cache_invalidate")
    def invalidate(self, key: str) -> bool:
        """
        Invalidate cache entry.
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            bool: True if entry was found and removed
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"🗑️ Cache invalidado para chave: {key}")
                return True
            return False
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"🧹 Cache limpo - {count} entradas removidas")
    
    def register_refresh_function(self, key: str, refresh_func: Callable[[], Any]):
        """
        Register a function to refresh cache data in background.
        
        Args:
            key: Cache key to refresh
            refresh_func: Function that returns fresh data
        """
        self._refresh_functions[key] = refresh_func
        logger.debug(f"🔄 Função de refresh registrada para chave: {key}")
    
    def _start_refresh_thread(self):
        """Start background refresh thread."""
        if self._refresh_thread and self._refresh_thread.is_alive():
            return
        
        self._refresh_thread = threading.Thread(target=self._background_refresh, daemon=True)
        self._refresh_thread.start()
        logger.debug("🔄 Thread de refresh em background iniciada")
    
    def _background_refresh(self):
        """Background thread to refresh stale cache entries."""
        while not self._stop_refresh.wait(30):  # Check every 30 seconds
            try:
                self._refresh_stale_entries()
            except Exception as e:
                logger.error(f"❌ Erro no refresh em background: {e}")
    
    def _refresh_stale_entries(self):
        """Refresh stale cache entries using registered functions."""
        stale_keys = []
        
        # Find stale entries
        with self._lock:
            for key, entry in self._cache.items():
                if entry.is_stale() and key in self._refresh_functions:
                    stale_keys.append(key)
        
        # Refresh stale entries
        for key in stale_keys:
            try:
                refresh_func = self._refresh_functions[key]
                
                with performance_monitor("cache_background_refresh", key=key):
                    fresh_data = refresh_func()
                    
                    if fresh_data is not None:
                        self.set(key, fresh_data)
                        self._stats['refreshes'] += 1
                        logger.debug(f"🔄 Cache refreshed em background para chave: {key}")
                    
            except Exception as e:
                self._stats['errors'] += 1
                logger.error(f"❌ Erro ao refresh cache para chave {key}: {e}")
    
    def get_or_set(self, key: str, fetch_func: Callable[[], Any], 
                   ttl: Optional[int] = None) -> Any:
        """
        Get from cache or fetch and cache if not found.
        
        Args:
            key: Cache key
            fetch_func: Function to fetch data if not in cache
            ttl: Time to live for cached data
            
        Returns:
            Cached or freshly fetched data
        """
        # Try to get from cache first
        cached_data = self.get(key)
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        try:
            with performance_monitor("cache_fetch_and_set", key=key):
                fresh_data = fetch_func()
                
                if fresh_data is not None:
                    self.set(key, fresh_data, ttl)
                
                return fresh_data
                
        except Exception as e:
            self._stats['errors'] += 1
            logger.error(f"❌ Erro ao buscar dados para cache key {key}: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                **self._stats,
                'total_requests': total_requests,
                'hit_rate_percent': round(hit_rate, 2),
                'cache_size': len(self._cache),
                'max_entries': self.max_entries,
                'default_ttl': self.default_ttl,
                'refresh_functions_count': len(self._refresh_functions)
            }
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information."""
        with self._lock:
            entries_info = {}
            
            for key, entry in self._cache.items():
                entries_info[key] = entry.get_stats()
            
            return {
                'stats': self.get_stats(),
                'entries': entries_info
            }
    
    def stop(self):
        """Stop background refresh thread and clear cache."""
        logger.info("🛑 Parando MetricsCacheService")
        
        # Stop refresh thread
        self._stop_refresh.set()
        if self._refresh_thread and self._refresh_thread.is_alive():
            self._refresh_thread.join(timeout=5)
        
        # Clear cache
        self.clear()
        
        logger.info("✅ MetricsCacheService parado")


# Global cache service instance
_cache_service: Optional[MetricsCacheService] = None


def initialize_cache_service(default_ttl: int = 300, max_entries: int = 100) -> MetricsCacheService:
    """
    Initialize global cache service.
    
    Args:
        default_ttl: Default TTL for cache entries in seconds
        max_entries: Maximum number of cache entries
        
    Returns:
        MetricsCacheService: Initialized cache service
    """
    global _cache_service
    
    if _cache_service is not None:
        logger.warning("⚠️ Cache service já inicializado, parando anterior")
        _cache_service.stop()
    
    _cache_service = MetricsCacheService(
        default_ttl=default_ttl,
        max_entries=max_entries
    )
    
    logger.info(f"✅ Cache service global inicializado - TTL: {default_ttl}s, Max: {max_entries}")
    return _cache_service


def get_cache_service() -> Optional[MetricsCacheService]:
    """Get the global cache service instance."""
    return _cache_service


def close_cache_service():
    """Close the global cache service."""
    global _cache_service
    
    if _cache_service:
        _cache_service.stop()
        _cache_service = None
        logger.info("✅ Cache service global fechado")


# Cache decorators for easy use
def cached(key_func: Callable = None, ttl: int = 300):
    """
    Decorator to cache function results.
    
    Args:
        key_func: Function to generate cache key from args
        ttl: Time to live for cached result
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache = get_cache_service()
            if not cache:
                return func(*args, **kwargs)
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try cache first
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator