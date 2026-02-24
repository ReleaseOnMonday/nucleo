"""Configuration management with lazy loading."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """Lightweight configuration manager with lazy loading."""

    _instance: Optional["Config"] = None
    _config: Optional[Dict[str, Any]] = None

    def __new__(cls):
        """Singleton pattern for memory efficiency."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize config loader."""
        if self._config is None:
            self._config = {}

    def load(self, config_path: Optional[str] = None) -> "Config":
        """Load configuration from file.

        Args:
            config_path: Path to config file. Defaults to ./config.json

        Returns:
            Self for chaining
        """
        if config_path is None:
            config_path = os.getenv("NEUCLO_CONFIG", "config.json")

        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, "r", encoding="utf-8") as f:
            self._config = json.load(f)

        return self

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with dot notation.

        Args:
            key: Configuration key (supports dot notation like 'agent.model')
            default: Default value if key not found

        Returns:
            Configuration value

        Examples:
            >>> config.get('agent.model')
            'claude-3-5-sonnet-20241022'
        """
        if self._config is None:
            return default

        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value.

        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        if self._config is None:
            self._config = {}

        keys = key.split(".")
        target = self._config

        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]

        target[keys[-1]] = value

    def save(self, config_path: Optional[str] = None) -> None:
        """Save configuration to file.

        Args:
            config_path: Path to save config. Defaults to ./config.json
        """
        if config_path is None:
            config_path = "config.json"

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2)

    @property
    def data(self) -> Dict[str, Any]:
        """Get raw configuration data."""
        return self._config or {}
