"""Base client for API integrations with common functionality."""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import httpx
from datetime import datetime, timedelta
import json

from ...config.config import config


logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base exception for API-related errors."""
    pass


class RateLimitError(APIError):
    """Exception raised when API rate limit is exceeded."""
    pass


class DataNotFoundError(APIError):
    """Exception raised when requested data is not found."""
    pass


class BaseAPIClient(ABC):
    """Base class for API clients with common functionality."""
    
    def __init__(self, base_url: str, timeout: int = 10, retry_attempts: int = 3):
        """Initialize the API client."""
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.cache: Dict[str, Dict[str, Any]] = {}
        
        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
    
    def _get_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate cache key for request."""
        cache_data = {
            'endpoint': endpoint,
            'params': sorted(params.items()) if params else []
        }
        return json.dumps(cache_data, sort_keys=True)
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any], ttl_days: int) -> bool:
        """Check if cache entry is still valid."""
        if not cache_entry:
            return False
        
        cached_at = datetime.fromisoformat(cache_entry['timestamp'])
        expiry = cached_at + timedelta(days=ttl_days)
        return datetime.now() < expiry
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_cache: bool = True,
        cache_ttl_days: int = 7
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic and caching."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Check cache first
        if use_cache:
            cache_key = self._get_cache_key(endpoint, params or {})
            if cache_key in self.cache:
                cache_entry = self.cache[cache_key]
                if self._is_cache_valid(cache_entry, cache_ttl_days):
                    logger.debug(f"Cache hit for {url}")
                    return cache_entry['data']
        
        # Make request with retry logic
        last_exception = None
        for attempt in range(self.retry_attempts):
            try:
                logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                response = await self.client.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=headers
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                    continue
                
                # Handle other HTTP errors
                response.raise_for_status()
                
                data = response.json()
                
                # Cache successful response
                if use_cache:
                    self.cache[cache_key] = {
                        'data': data,
                        'timestamp': datetime.now().isoformat()
                    }
                
                return data
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise DataNotFoundError(f"Data not found for {url}")
                elif e.response.status_code == 429:
                    raise RateLimitError(f"Rate limit exceeded for {url}")
                else:
                    last_exception = e
                    logger.warning(f"HTTP error {e.response.status_code} on attempt {attempt + 1}")
            
            except httpx.RequestError as e:
                last_exception = e
                logger.warning(f"Request error on attempt {attempt + 1}: {e}")
            
            # Exponential backoff
            if attempt < self.retry_attempts - 1:
                wait_time = 2 ** attempt
                logger.debug(f"Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
        
        # If all retries failed
        if last_exception:
            raise APIError(f"Failed to make request to {url} after {self.retry_attempts} attempts") from last_exception
        else:
            raise APIError(f"Failed to make request to {url} for unknown reason")
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Make GET request."""
        return await self._make_request('GET', endpoint, params, **kwargs)
    
    async def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Make POST request."""
        headers = kwargs.get('headers', {})
        headers['Content-Type'] = 'application/json'
        kwargs['headers'] = headers
        
        return await self._make_request('POST', endpoint, params=data, **kwargs)
    
    @abstractmethod
    async def fetch_data(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch data for given coordinates. Must be implemented by subclasses."""
        pass
    
    def clear_cache(self):
        """Clear all cached data."""
        self.cache.clear()
        logger.info("Cache cleared")
