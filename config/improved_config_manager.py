"""
Configuration Management - CodeScene ACE Improvement
Centralized configuration handling with better error management
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class AppSettings:
    """Application settings data class."""
    last_folder: str
    theme: str = "light"
    auto_save: bool = True
    log_level: str = "INFO"
    max_workers: int = 4
    backup_enabled: bool = True
    
    @classmethod
    def default(cls) -> 'AppSettings':
        """Create default settings."""
        return cls(
            last_folder=str(Path.cwd()),
            theme="light",
            auto_save=True,
            log_level="INFO",
            max_workers=4,
            backup_enabled=True
        )


class ConfigurationManager:
    """
    Improved configuration management following CodeScene ACE principles.
    - Single responsibility: Only handles configuration
    - Better error handling
    - Type safety with dataclasses
    - Clear separation of concerns
    """
    
    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path("config.json")
        self._settings: Optional[AppSettings] = None
        self._load_configuration()
    
    def _load_configuration(self) -> None:
        """Load configuration from file or create default."""
        try:
            if self.config_file.exists():
                self._settings = self._load_from_file()
                logger.info(f"Configuration loaded from {self.config_file}")
            else:
                self._settings = AppSettings.default()
                self._save_configuration()
                logger.info("Default configuration created")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            self._settings = AppSettings.default()
    
    def _load_from_file(self) -> AppSettings:
        """Load settings from JSON file."""
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                return AppSettings(**data)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Invalid configuration file: {e}")
            return AppSettings.default()
    
    def _save_configuration(self) -> None:
        """Save current settings to file."""
        try:
            if self._settings is not None:
                with open(self.config_file, 'w') as f:
                    json.dump(asdict(self._settings), f, indent=4)
                logger.debug(f"Configuration saved to {self.config_file}")
            else:
                logger.error("No settings to save: self._settings is None")
                return
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
    
    @property
    def settings(self) -> AppSettings:
        """Get current settings."""
        if self._settings is None:
            self._settings = AppSettings.default()
        return self._settings
    
    def update_setting(self, key: str, value: Any) -> bool:
        """Update a single setting."""
        try:
            if hasattr(self._settings, key):
                setattr(self._settings, key, value)
                self._save_configuration()
                logger.info(f"Setting updated: {key} = {value}")
                return True
            else:
                logger.warning(f"Unknown setting: {key}")
                return False
        except Exception as e:
            logger.error(f"Failed to update setting {key}: {e}")
            return False
    
    def update_settings(self, **kwargs) -> bool:
        """Update multiple settings."""
        try:
            for key, value in kwargs.items():
                if not hasattr(self._settings, key):
                    logger.warning(f"Unknown setting: {key}")
                    continue
                setattr(self._settings, key, value)
            
            self._save_configuration()
            logger.info(f"Settings updated: {list(kwargs.keys())}")
            return True
        except Exception as e:
            logger.error(f"Failed to update settings: {e}")
            return False
    
    def reset_to_defaults(self) -> None:
        """Reset settings to defaults."""
        self._settings = AppSettings.default()
        self._save_configuration()
        logger.info("Settings reset to defaults")
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific setting value."""
        return getattr(self._settings, key, default)


# Usage example for improved app.py
class ImprovedConfigManager(ConfigurationManager):
    """
    Backwards compatible configuration manager.
    Maintains the same interface as the original while providing improvements.
    """
    
    def __init__(self):
        super().__init__(Path("config.json"))
        # Maintain backwards compatibility
        self.config = self._get_legacy_config()
    
    def _get_legacy_config(self) -> Dict[str, Any]:
        """Get configuration in legacy format."""
        return {
            "last_folder": self.settings.last_folder,
            "theme": self.settings.theme,
            "auto_save": self.settings.auto_save,
            "log_level": self.settings.log_level,
            "max_workers": self.settings.max_workers,
            "backup_enabled": self.settings.backup_enabled
        }
    
    def save_default(self) -> None:
        """Legacy method for saving defaults."""
        self.reset_to_defaults()
        self.config = self._get_legacy_config()
    
    def load(self) -> None:
        """Legacy method for loading configuration."""
        self._load_configuration()
        self.config = self._get_legacy_config()
    
    def save(self) -> None:
        """Legacy method for saving configuration."""
        self._save_configuration()


# Example usage in app_improved.py
def example_usage():
    """Example of how to use the improved configuration manager."""
    
    # Create configuration manager
    config_manager = ImprovedConfigManager()
    
    # Access settings
    print(f"Last folder: {config_manager.settings.last_folder}")
    print(f"Theme: {config_manager.settings.theme}")
    
    # Update settings
    config_manager.update_setting("last_folder", "/new/path")
    config_manager.update_settings(theme="dark", auto_save=False)
    
    # Use in app initialization
    app_settings = config_manager.settings
    print(f"Starting app with theme: {app_settings.theme}")
    print(f"Auto-save enabled: {app_settings.auto_save}")


if __name__ == "__main__":
    example_usage()
