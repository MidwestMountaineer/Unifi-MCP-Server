"""Tests for configuration loading."""

import os
import pytest
import tempfile
from pathlib import Path
from unifi_mcp.config import load_config, Config, ConfigurationError


def test_load_config_missing_credentials(monkeypatch, tmp_path):
    """Test that missing credentials cause fail-fast behavior."""
    # Clear environment variables
    monkeypatch.delenv("UNIFI_HOST", raising=False)
    monkeypatch.delenv("UNIFI_USERNAME", raising=False)
    monkeypatch.delenv("UNIFI_PASSWORD", raising=False)
    monkeypatch.delenv("UNIFI_API_KEY", raising=False)
    
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(load_env=False)
    
    assert "Missing required configuration field" in str(exc_info.value)
    assert "UNIFI_HOST" in str(exc_info.value)


def test_load_config_with_api_key(monkeypatch):
    """Test loading configuration with API key."""
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_API_KEY", "test-api-key-12345")
    monkeypatch.setenv("UNIFI_SITE", "default")
    
    config = load_config(load_env=False)
    
    assert config.unifi.host == "192.168.1.1"
    assert config.unifi.api_key == "test-api-key-12345"
    assert config.unifi.username == ""
    assert config.unifi.password == ""
    assert config.unifi.site == "default"


def test_load_config_missing_auth(monkeypatch):
    """Test that missing both API key and username/password fails."""
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    # Don't set API key or username/password
    monkeypatch.delenv("UNIFI_API_KEY", raising=False)
    monkeypatch.delenv("UNIFI_USERNAME", raising=False)
    monkeypatch.delenv("UNIFI_PASSWORD", raising=False)
    
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(load_env=False)
    
    assert "authentication credentials" in str(exc_info.value).lower()
    assert "API Key" in str(exc_info.value) or "api_key" in str(exc_info.value)


def test_load_config_with_env_vars(monkeypatch):
    """Test loading configuration with environment variables."""
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    monkeypatch.setenv("UNIFI_PORT", "8443")
    monkeypatch.setenv("UNIFI_SITE", "testsite")
    
    config = load_config(load_env=False)
    
    assert isinstance(config, Config)
    assert config.unifi.host == "192.168.1.1"
    assert config.unifi.username == "admin"
    assert config.unifi.password == "password123"
    assert config.unifi.port == 8443
    assert config.unifi.site == "testsite"


def test_load_config_with_defaults(monkeypatch):
    """Test that default values are applied correctly."""
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    
    config = load_config(load_env=False)
    
    # Check defaults
    assert config.unifi.port == 443
    assert config.unifi.site == "default"
    assert config.unifi.verify_ssl is False
    assert config.server.name == "unifi-network-mcp"
    assert config.server.log_level == "INFO"


def test_load_config_boolean_conversion(monkeypatch):
    """Test that boolean strings are converted correctly."""
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    monkeypatch.setenv("UNIFI_VERIFY_SSL", "true")
    
    config = load_config(load_env=False)
    
    assert config.unifi.verify_ssl is True


def test_load_config_invalid_port(monkeypatch):
    """Test that invalid port values are rejected."""
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    monkeypatch.setenv("UNIFI_PORT", "99999")
    
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(load_env=False)
    
    assert "Invalid port" in str(exc_info.value)


def test_load_config_invalid_log_level(monkeypatch):
    """Test that invalid log levels are rejected."""
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    monkeypatch.setenv("LOG_LEVEL", "INVALID")
    
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(load_env=False)
    
    assert "Invalid log_level" in str(exc_info.value)


def test_config_structure(monkeypatch):
    """Test that configuration structure is correct."""
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    
    config = load_config(load_env=False)
    
    # Check structure
    assert hasattr(config, "server")
    assert hasattr(config, "unifi")
    assert hasattr(config, "tools")
    
    assert hasattr(config.server, "name")
    assert hasattr(config.server, "log_level")
    assert hasattr(config.server, "diagnostics")
    assert hasattr(config.server, "performance")
    
    assert hasattr(config.unifi, "host")
    assert hasattr(config.unifi, "port")
    assert hasattr(config.unifi, "username")
    assert hasattr(config.unifi, "password")
    assert hasattr(config.unifi, "retry")
    
    assert hasattr(config.tools, "network_discovery")
    assert hasattr(config.tools, "security")
    assert hasattr(config.tools, "write_operations")


# ============================================================================
# YAML Loading Tests
# ============================================================================

def test_yaml_loading_from_default_path(monkeypatch):
    """Test that YAML configuration loads from default path."""
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    
    config = load_config(load_env=False)
    
    # Verify YAML values are loaded
    assert config.server.name == "unifi-network-mcp"
    assert config.server.performance.get("cache_ttl") == 30
    assert config.server.performance.get("max_concurrent_requests") == 10
    assert config.unifi.retry.get("max_attempts") == 3
    assert config.unifi.retry.get("backoff_factor") == 2


def test_yaml_loading_from_custom_path(monkeypatch, tmp_path):
    """Test that YAML configuration loads from custom path."""
    # Create a custom config file
    custom_config = tmp_path / "custom_config.yaml"
    custom_config.write_text("""
server:
  name: "custom-server"
  log_level: "DEBUG"
  performance:
    cache_ttl: 60
    max_concurrent_requests: 20
    request_timeout: 45
    connection_timeout: 15

unifi:
  host: "${UNIFI_HOST}"
  port: "${UNIFI_PORT:443}"
  username: "${UNIFI_USERNAME}"
  password: "${UNIFI_PASSWORD}"
  site: "${UNIFI_SITE:default}"
  verify_ssl: "${UNIFI_VERIFY_SSL:false}"
  retry:
    max_attempts: 5
    backoff_factor: 3
    max_backoff: 60

tools:
  network_discovery:
    enabled: true
  security:
    enabled: true
  statistics:
    enabled: true
  migration:
    enabled: true
  write_operations:
    enabled: false
""")
    
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    
    config = load_config(config_path=custom_config, load_env=False)
    
    # Verify custom YAML values are loaded
    assert config.server.name == "custom-server"
    assert config.server.log_level == "DEBUG"
    assert config.server.performance.get("cache_ttl") == 60
    assert config.server.performance.get("max_concurrent_requests") == 20
    assert config.unifi.retry.get("max_attempts") == 5
    assert config.unifi.retry.get("backoff_factor") == 3


def test_yaml_loading_missing_file():
    """Test that missing YAML file raises ConfigurationError."""
    non_existent_path = Path("/non/existent/config.yaml")
    
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(config_path=non_existent_path, load_env=False)
    
    assert "Configuration file not found" in str(exc_info.value)


def test_yaml_loading_invalid_yaml(tmp_path, monkeypatch):
    """Test that invalid YAML raises ConfigurationError."""
    invalid_yaml = tmp_path / "invalid.yaml"
    invalid_yaml.write_text("""
server:
  name: "test"
  invalid: [unclosed bracket
""")
    
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(config_path=invalid_yaml, load_env=False)
    
    assert "Failed to parse YAML configuration" in str(exc_info.value)


# ============================================================================
# Environment Variable Override Tests
# ============================================================================

def test_env_override_unifi_host(monkeypatch):
    """Test that UNIFI_HOST environment variable overrides YAML."""
    monkeypatch.setenv("UNIFI_HOST", "10.0.0.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    
    config = load_config(load_env=False)
    
    assert config.unifi.host == "10.0.0.1"


def test_env_override_unifi_port(monkeypatch):
    """Test that UNIFI_PORT environment variable overrides default."""
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    monkeypatch.setenv("UNIFI_PORT", "8443")
    
    config = load_config(load_env=False)
    
    assert config.unifi.port == 8443


def test_env_override_unifi_site(monkeypatch):
    """Test that UNIFI_SITE environment variable overrides default."""
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    monkeypatch.setenv("UNIFI_SITE", "production")
    
    config = load_config(load_env=False)
    
    assert config.unifi.site == "production"


def test_env_override_log_level(monkeypatch):
    """Test that LOG_LEVEL environment variable overrides YAML."""
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    
    config = load_config(load_env=False)
    
    assert config.server.log_level == "DEBUG"


def test_env_override_verify_ssl_true(monkeypatch):
    """Test that UNIFI_VERIFY_SSL=true overrides default."""
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    monkeypatch.setenv("UNIFI_VERIFY_SSL", "true")
    
    config = load_config(load_env=False)
    
    assert config.unifi.verify_ssl is True


def test_env_override_verify_ssl_false(monkeypatch):
    """Test that UNIFI_VERIFY_SSL=false works correctly."""
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    monkeypatch.setenv("UNIFI_VERIFY_SSL", "false")
    
    config = load_config(load_env=False)
    
    assert config.unifi.verify_ssl is False


def test_env_override_multiple_values(monkeypatch):
    """Test that multiple environment variables override correctly."""
    monkeypatch.setenv("UNIFI_HOST", "10.0.0.1")
    monkeypatch.setenv("UNIFI_PORT", "8443")
    monkeypatch.setenv("UNIFI_USERNAME", "superadmin")
    monkeypatch.setenv("UNIFI_PASSWORD", "secret123")
    monkeypatch.setenv("UNIFI_SITE", "staging")
    monkeypatch.setenv("UNIFI_VERIFY_SSL", "true")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    
    config = load_config(load_env=False)
    
    assert config.unifi.host == "10.0.0.1"
    assert config.unifi.port == 8443
    assert config.unifi.username == "superadmin"
    assert config.unifi.password == "secret123"
    assert config.unifi.site == "staging"
    assert config.unifi.verify_ssl is True
    assert config.server.log_level == "WARNING"


# ============================================================================
# Validation Error Tests
# ============================================================================

def test_validation_error_missing_host(monkeypatch):
    """Test validation error when UNIFI_HOST is missing."""
    monkeypatch.delenv("UNIFI_HOST", raising=False)
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(load_env=False)
    
    assert "Missing required configuration field" in str(exc_info.value)
    assert "UNIFI_HOST" in str(exc_info.value)


def test_validation_error_missing_username(monkeypatch):
    """Test validation error when UNIFI_USERNAME is missing (and no API key)."""
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.delenv("UNIFI_USERNAME", raising=False)
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    monkeypatch.delenv("UNIFI_API_KEY", raising=False)
    
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(load_env=False)
    
    assert "authentication credentials" in str(exc_info.value).lower()


def test_validation_error_missing_password(monkeypatch):
    """Test validation error when UNIFI_PASSWORD is missing (and no API key)."""
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.delenv("UNIFI_PASSWORD", raising=False)
    monkeypatch.delenv("UNIFI_API_KEY", raising=False)
    
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(load_env=False)
    
    assert "authentication credentials" in str(exc_info.value).lower()


def test_validation_error_empty_host(monkeypatch):
    """Test validation error when UNIFI_HOST is empty."""
    monkeypatch.setenv("UNIFI_HOST", "")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(load_env=False)
    
    assert "Missing required configuration field" in str(exc_info.value)


def test_validation_error_whitespace_only_host(monkeypatch):
    """Test validation error when UNIFI_HOST is whitespace only."""
    monkeypatch.setenv("UNIFI_HOST", "   ")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    
    # Whitespace-only host should pass through and fail at validation
    config = load_config(load_env=False)
    # The whitespace host will be in the config
    assert config.unifi.host == "   "


def test_validation_error_port_too_low(monkeypatch):
    """Test validation error when port is below valid range."""
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    monkeypatch.setenv("UNIFI_PORT", "0")
    
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(load_env=False)
    
    assert "Invalid port" in str(exc_info.value)


def test_validation_error_port_too_high(monkeypatch):
    """Test validation error when port is above valid range."""
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    monkeypatch.setenv("UNIFI_PORT", "99999")
    
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(load_env=False)
    
    assert "Invalid port" in str(exc_info.value)


def test_validation_error_invalid_log_level(monkeypatch):
    """Test validation error when log level is invalid."""
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    monkeypatch.setenv("LOG_LEVEL", "INVALID")
    
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(load_env=False)
    
    assert "Invalid log_level" in str(exc_info.value)


def test_validation_error_negative_cache_ttl(monkeypatch, tmp_path):
    """Test validation error when cache_ttl is negative."""
    custom_config = tmp_path / "config.yaml"
    custom_config.write_text("""
server:
  performance:
    cache_ttl: -10
    max_concurrent_requests: 10
    request_timeout: 30
    connection_timeout: 10

unifi:
  host: "${UNIFI_HOST}"
  username: "${UNIFI_USERNAME}"
  password: "${UNIFI_PASSWORD}"
  retry:
    max_attempts: 3
    backoff_factor: 2

tools:
  network_discovery:
    enabled: true
  security:
    enabled: true
  statistics:
    enabled: true
  migration:
    enabled: true
  write_operations:
    enabled: false
""")
    
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(config_path=custom_config, load_env=False)
    
    assert "Invalid cache_ttl" in str(exc_info.value)


def test_validation_error_invalid_max_concurrent(monkeypatch, tmp_path):
    """Test validation error when max_concurrent_requests is invalid."""
    custom_config = tmp_path / "config.yaml"
    custom_config.write_text("""
server:
  performance:
    cache_ttl: 30
    max_concurrent_requests: 0
    request_timeout: 30
    connection_timeout: 10

unifi:
  host: "${UNIFI_HOST}"
  username: "${UNIFI_USERNAME}"
  password: "${UNIFI_PASSWORD}"
  retry:
    max_attempts: 3
    backoff_factor: 2

tools:
  network_discovery:
    enabled: true
  security:
    enabled: true
  statistics:
    enabled: true
  migration:
    enabled: true
  write_operations:
    enabled: false
""")
    
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(config_path=custom_config, load_env=False)
    
    assert "Invalid max_concurrent_requests" in str(exc_info.value)


def test_validation_error_invalid_retry_attempts(monkeypatch, tmp_path):
    """Test validation error when retry max_attempts is invalid."""
    custom_config = tmp_path / "config.yaml"
    custom_config.write_text("""
server:
  performance:
    cache_ttl: 30
    max_concurrent_requests: 10
    request_timeout: 30
    connection_timeout: 10

unifi:
  host: "${UNIFI_HOST}"
  username: "${UNIFI_USERNAME}"
  password: "${UNIFI_PASSWORD}"
  retry:
    max_attempts: 0
    backoff_factor: 2

tools:
  network_discovery:
    enabled: true
  security:
    enabled: true
  statistics:
    enabled: true
  migration:
    enabled: true
  write_operations:
    enabled: false
""")
    
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(config_path=custom_config, load_env=False)
    
    assert "Invalid retry.max_attempts" in str(exc_info.value)


# ============================================================================
# Fail-Fast Behavior Tests
# ============================================================================

def test_fail_fast_missing_all_credentials(monkeypatch):
    """Test fail-fast behavior when all credentials are missing."""
    monkeypatch.delenv("UNIFI_HOST", raising=False)
    monkeypatch.delenv("UNIFI_USERNAME", raising=False)
    monkeypatch.delenv("UNIFI_PASSWORD", raising=False)
    monkeypatch.delenv("UNIFI_API_KEY", raising=False)
    
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(load_env=False)
    
    error_msg = str(exc_info.value)
    assert "Missing required configuration field" in error_msg
    assert "UNIFI_HOST" in error_msg


def test_fail_fast_helpful_error_message(monkeypatch):
    """Test that fail-fast error message is helpful and actionable."""
    monkeypatch.delenv("UNIFI_HOST", raising=False)
    monkeypatch.delenv("UNIFI_USERNAME", raising=False)
    monkeypatch.delenv("UNIFI_PASSWORD", raising=False)
    monkeypatch.delenv("UNIFI_API_KEY", raising=False)
    
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(load_env=False)
    
    error_msg = str(exc_info.value)
    # Should mention .env.example
    assert ".env.example" in error_msg
    # Should list UNIFI_HOST
    assert "UNIFI_HOST" in error_msg


def test_fail_fast_on_startup_not_runtime(monkeypatch):
    """Test that validation happens at load time, not later."""
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    
    # Should not raise during load
    config = load_config(load_env=False)
    
    # Config should be valid and usable
    assert config.unifi.host == "192.168.1.1"
    assert config.unifi.username == "admin"
    assert config.unifi.password == "password123"


def test_fail_fast_invalid_config_values(monkeypatch):
    """Test that invalid config values cause immediate failure."""
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    monkeypatch.setenv("UNIFI_PORT", "invalid")
    
    # Should fail immediately during load
    with pytest.raises(ConfigurationError):
        load_config(load_env=False)


def test_fail_fast_multiple_validation_errors(monkeypatch, tmp_path):
    """Test that multiple validation errors are reported together."""
    custom_config = tmp_path / "config.yaml"
    custom_config.write_text("""
server:
  log_level: "INVALID_LEVEL"
  performance:
    cache_ttl: -10
    max_concurrent_requests: 0
    request_timeout: 0
    connection_timeout: 0

unifi:
  host: "${UNIFI_HOST}"
  username: "${UNIFI_USERNAME}"
  password: "${UNIFI_PASSWORD}"
  retry:
    max_attempts: 0
    backoff_factor: 0

tools:
  network_discovery:
    enabled: true
  security:
    enabled: true
  statistics:
    enabled: true
  migration:
    enabled: true
  write_operations:
    enabled: false
""")
    
    monkeypatch.setenv("UNIFI_HOST", "192.168.1.1")
    monkeypatch.setenv("UNIFI_USERNAME", "admin")
    monkeypatch.setenv("UNIFI_PASSWORD", "password123")
    
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(config_path=custom_config, load_env=False)
    
    error_msg = str(exc_info.value)
    # Should report multiple errors
    assert "Configuration validation failed" in error_msg
    assert "Invalid log_level" in error_msg
    assert "Invalid cache_ttl" in error_msg
    assert "Invalid max_concurrent_requests" in error_msg
