"""Configuration loader for UniFi MCP Server.

This module handles loading configuration from YAML files and environment variables,
with validation and fail-fast behavior for missing required credentials.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv


class ConfigurationError(Exception):
    """Raised when configuration is invalid or incomplete."""
    pass


@dataclass
class ServerConfig:
    """Server configuration."""
    name: str = "unifi-network-mcp"
    log_level: str = "INFO"
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    performance: Dict[str, Any] = field(default_factory=dict)
    logging: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UniFiConfig:
    """UniFi controller configuration."""
    host: str
    port: int = 443
    username: str = ""
    password: str = ""
    api_key: str = ""
    site: str = "default"
    verify_ssl: bool = False
    retry: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolsConfig:
    """Tools configuration."""
    network_discovery: Dict[str, Any] = field(default_factory=dict)
    security: Dict[str, Any] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)
    migration: Dict[str, Any] = field(default_factory=dict)
    write_operations: Dict[str, Any] = field(default_factory=dict)
    firewall: Dict[str, Any] = field(default_factory=dict)
    acl: Dict[str, Any] = field(default_factory=dict)
    dns: Dict[str, Any] = field(default_factory=dict)
    resources: Dict[str, Any] = field(default_factory=dict)
    resources: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    """Main configuration object."""
    server: ServerConfig
    unifi: UniFiConfig
    tools: ToolsConfig


def _expand_env_vars(value: Any) -> Any:
    """Recursively expand environment variables in configuration values.
    
    Supports ${VAR_NAME} and ${VAR_NAME:default_value} syntax.
    
    Args:
        value: Configuration value (can be str, dict, list, or other)
    
    Returns:
        Value with environment variables expanded
    """
    if isinstance(value, str):
        # Pattern matches ${VAR_NAME} or ${VAR_NAME:default}
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
        
        def replace_env(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) is not None else ""
            return os.environ.get(var_name, default_value)
        
        return re.sub(pattern, replace_env, value)
    
    elif isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}
    
    elif isinstance(value, list):
        return [_expand_env_vars(item) for item in value]
    
    return value


def _convert_types(value: Any) -> Any:
    """Convert string values to appropriate types.
    
    Args:
        value: Value to convert
    
    Returns:
        Converted value
    """
    if isinstance(value, str):
        # Convert boolean strings
        if value.lower() in ("true", "yes", "1"):
            return True
        elif value.lower() in ("false", "no", "0"):
            return False
        
        # Convert numeric strings
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
    
    elif isinstance(value, dict):
        return {k: _convert_types(v) for k, v in value.items()}
    
    elif isinstance(value, list):
        return [_convert_types(item) for item in value]
    
    return value


def _load_yaml_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load configuration from YAML file.
    
    Args:
        config_path: Path to config file. If None, uses default location.
    
    Returns:
        Configuration dictionary
    
    Raises:
        ConfigurationError: If config file cannot be loaded
    """
    if config_path is None:
        # Default to config.yaml in the same directory as this file
        config_path = Path(__file__).parent / "config.yaml"
    
    if not config_path.exists():
        raise ConfigurationError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return config or {}
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Failed to parse YAML configuration: {e}")
    except Exception as e:
        raise ConfigurationError(f"Failed to load configuration: {e}")


def _validate_required_fields(config: Dict[str, Any]) -> None:
    """Validate that required configuration fields are present and non-empty.
    
    Args:
        config: Configuration dictionary
    
    Raises:
        ConfigurationError: If required fields are missing or empty
    """
    # Host is always required
    if not config.get("unifi", {}).get("host"):
        raise ConfigurationError(
            "Missing required configuration field: unifi.host\n"
            "Set via UNIFI_HOST environment variable.\n"
            "See .env.example for reference."
        )
    
    # Either API key OR username+password must be provided
    api_key = config.get("unifi", {}).get("api_key", "")
    username = config.get("unifi", {}).get("username", "")
    password = config.get("unifi", {}).get("password", "")
    
    has_api_key = api_key and api_key.strip()
    has_credentials = username and username.strip() and password and password.strip()
    
    if not has_api_key and not has_credentials:
        raise ConfigurationError(
            "Missing authentication credentials. You must provide either:\n"
            "  Option 1 (Recommended): API Key\n"
            "    - unifi.api_key (set via UNIFI_API_KEY environment variable)\n"
            "  Option 2: Username and Password\n"
            "    - unifi.username (set via UNIFI_USERNAME environment variable)\n"
            "    - unifi.password (set via UNIFI_PASSWORD environment variable)\n"
            "\nSee .env.example for reference."
        )


def _validate_config_values(config: Dict[str, Any]) -> None:
    """Validate configuration values are within acceptable ranges.
    
    Args:
        config: Configuration dictionary
    
    Raises:
        ConfigurationError: If configuration values are invalid
    """
    errors = []
    
    # Validate log level
    valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    log_level = config.get("server", {}).get("log_level", "INFO")
    if log_level not in valid_log_levels:
        errors.append(f"Invalid log_level '{log_level}'. Must be one of: {', '.join(valid_log_levels)}")
    
    # Validate port
    port = config.get("unifi", {}).get("port", 443)
    if not isinstance(port, int) or port < 1 or port > 65535:
        errors.append(f"Invalid port '{port}'. Must be between 1 and 65535")
    
    # Validate performance settings
    perf = config.get("server", {}).get("performance", {})
    
    cache_ttl = perf.get("cache_ttl", 30)
    if not isinstance(cache_ttl, (int, float)) or cache_ttl < 0:
        errors.append(f"Invalid cache_ttl '{cache_ttl}'. Must be a positive number")
    
    max_concurrent = perf.get("max_concurrent_requests", 10)
    if not isinstance(max_concurrent, int) or max_concurrent < 1:
        errors.append(f"Invalid max_concurrent_requests '{max_concurrent}'. Must be a positive integer")
    
    request_timeout = perf.get("request_timeout", 30)
    if not isinstance(request_timeout, (int, float)) or request_timeout < 1:
        errors.append(f"Invalid request_timeout '{request_timeout}'. Must be at least 1 second")
    
    connection_timeout = perf.get("connection_timeout", 10)
    if not isinstance(connection_timeout, (int, float)) or connection_timeout < 1:
        errors.append(f"Invalid connection_timeout '{connection_timeout}'. Must be at least 1 second")
    
    # Validate retry settings
    retry = config.get("unifi", {}).get("retry", {})
    
    max_attempts = retry.get("max_attempts", 3)
    if not isinstance(max_attempts, int) or max_attempts < 1:
        errors.append(f"Invalid retry.max_attempts '{max_attempts}'. Must be a positive integer")
    
    backoff_factor = retry.get("backoff_factor", 2)
    if not isinstance(backoff_factor, (int, float)) or backoff_factor < 1:
        errors.append(f"Invalid retry.backoff_factor '{backoff_factor}'. Must be at least 1")
    
    if errors:
        raise ConfigurationError("Configuration validation failed:\n  - " + "\n  - ".join(errors))


def load_config(
    config_path: Optional[Path] = None,
    load_env: bool = True
) -> Config:
    """Load and validate configuration from YAML and environment variables.
    
    This function:
    1. Loads .env file if present (unless load_env=False)
    2. Loads YAML configuration
    3. Expands environment variables in YAML values
    4. Converts string values to appropriate types
    5. Validates required fields are present
    6. Validates configuration values are valid
    7. Returns structured Config object
    
    Args:
        config_path: Path to YAML config file. If None, uses default.
        load_env: Whether to load .env file. Default True.
    
    Returns:
        Config object with validated configuration
    
    Raises:
        ConfigurationError: If configuration is invalid or incomplete
    
    Example:
        >>> config = load_config()
        >>> print(config.unifi.host)
        '192.168.1.1'
    """
    # Load .env file if present
    if load_env:
        load_dotenv()
    
    # Load YAML configuration
    raw_config = _load_yaml_config(config_path)
    
    # Expand environment variables
    expanded_config = _expand_env_vars(raw_config)
    
    # Convert types
    typed_config = _convert_types(expanded_config)
    
    # Validate required fields
    _validate_required_fields(typed_config)
    
    # Validate configuration values
    _validate_config_values(typed_config)
    
    # Build structured config objects
    try:
        server_config = ServerConfig(
            name=typed_config.get("server", {}).get("name", "unifi-network-mcp"),
            log_level=typed_config.get("server", {}).get("log_level", "INFO"),
            diagnostics=typed_config.get("server", {}).get("diagnostics", {}),
            performance=typed_config.get("server", {}).get("performance", {}),
            logging=typed_config.get("server", {}).get("logging", {}),
        )
        
        unifi_config = UniFiConfig(
            host=typed_config["unifi"]["host"],
            port=typed_config["unifi"].get("port", 443),
            username=typed_config["unifi"].get("username", ""),
            password=typed_config["unifi"].get("password", ""),
            api_key=typed_config["unifi"].get("api_key", ""),
            site=typed_config["unifi"].get("site", "default"),
            verify_ssl=typed_config["unifi"].get("verify_ssl", False),
            retry=typed_config["unifi"].get("retry", {}),
        )
        
        tools_config = ToolsConfig(
            network_discovery=typed_config.get("tools", {}).get("network_discovery", {}),
            security=typed_config.get("tools", {}).get("security", {}),
            statistics=typed_config.get("tools", {}).get("statistics", {}),
            migration=typed_config.get("tools", {}).get("migration", {}),
            write_operations=typed_config.get("tools", {}).get("write_operations", {}),
            firewall=typed_config.get("tools", {}).get("firewall", {}),
            acl=typed_config.get("tools", {}).get("acl", {}),
            dns=typed_config.get("tools", {}).get("dns", {}),
        )
        
        return Config(
            server=server_config,
            unifi=unifi_config,
            tools=tools_config,
        )
    
    except KeyError as e:
        raise ConfigurationError(f"Missing required configuration key: {e}")
    except Exception as e:
        raise ConfigurationError(f"Failed to build configuration: {e}")
