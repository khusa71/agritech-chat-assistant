"""Configuration management for the AgriTech system."""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """Configuration manager for the application."""
    
    def __init__(self, config_file: str = "config.yaml", env_file: str = ".env"):
        """Initialize configuration from files."""
        self.config_file = config_file
        self.env_file = env_file
        
        # Load environment variables
        load_dotenv(env_file)
        
        # Load YAML configuration
        self._config = self._load_yaml_config()
    
    def _load_yaml_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        config_path = Path(self.config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key (supports dot notation)."""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_env(self, key: str, default: Any = None) -> Any:
        """Get environment variable."""
        return os.getenv(key, default)
    
    def get_database_url(self) -> str:
        """Get database URL from environment."""
        return self.get_env('DATABASE_URL', 'postgresql://user:password@localhost:5432/agri_tech')
    
    def get_openmeteo_api_key(self) -> str:
        """Get Open-Meteo API key (not required - free service)."""
        # Open-Meteo is free and doesn't require an API key
        return ""
    
    def get_log_level(self) -> str:
        """Get log level from configuration."""
        return self.get_env('LOG_LEVEL', self.get('logging.level', 'INFO'))
    
    def get_cache_ttl_days(self) -> int:
        """Get cache TTL in days."""
        return int(self.get_env('CACHE_TTL_DAYS', self.get('apis.soilgrids.cache_ttl_days', 7)))
    
    def get_request_timeout(self) -> int:
        """Get request timeout in seconds."""
        return int(self.get_env('REQUEST_TIMEOUT_SECONDS', 10))
    
    def get_api_config(self, api_name: str) -> Dict[str, Any]:
        """Get API configuration by name."""
        return self.get(f'apis.{api_name}', {})
    
    def get_crop_recommendation_config(self) -> Dict[str, Any]:
        """Get crop recommendation configuration."""
        return self.get('crop_recommendation', {})


# Global configuration instance
config = Config()
