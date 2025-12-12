"""Tests for logging utilities with redaction."""

import logging
import tempfile
from pathlib import Path

import pytest

from unifi_mcp.utils.logging import (
    clear_correlation_id,
    generate_correlation_id,
    get_correlation_id,
    get_logger,
    log_with_redaction,
    redact_sensitive_data,
    set_correlation_id,
    setup_logging,
)


class TestCorrelationID:
    """Tests for correlation ID management."""
    
    def test_generate_correlation_id(self):
        """Test correlation ID generation."""
        correlation_id = generate_correlation_id()
        assert correlation_id is not None
        assert len(correlation_id) == 36  # UUID format
        assert "-" in correlation_id
    
    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
        test_id = "test-correlation-id-123"
        set_correlation_id(test_id)
        assert get_correlation_id() == test_id
        clear_correlation_id()
    
    def test_set_correlation_id_auto_generate(self):
        """Test auto-generation when setting correlation ID."""
        correlation_id = set_correlation_id()
        assert correlation_id is not None
        assert get_correlation_id() == correlation_id
        clear_correlation_id()
    
    def test_clear_correlation_id(self):
        """Test clearing correlation ID."""
        set_correlation_id("test-id")
        clear_correlation_id()
        assert get_correlation_id() is None


class TestSensitiveDataRedaction:
    """Tests for sensitive data redaction."""
    
    def test_redact_password_in_dict(self):
        """Test redacting password field in dictionary."""
        data = {"username": "admin", "password": "secret123"}
        redacted = redact_sensitive_data(data)
        assert redacted["username"] == "admin"
        assert redacted["password"] == "[REDACTED]"
    
    def test_redact_multiple_sensitive_fields(self):
        """Test redacting multiple sensitive fields."""
        data = {
            "username": "admin",
            "password": "secret123",
            "api_key": "abc123xyz",
            "token": "bearer-token-here",
            "email": "user@example.com"
        }
        redacted = redact_sensitive_data(data)
        assert redacted["username"] == "admin"
        assert redacted["email"] == "user@example.com"
        assert redacted["password"] == "[REDACTED]"
        assert redacted["api_key"] == "[REDACTED]"
        assert redacted["token"] == "[REDACTED]"
    
    def test_redact_nested_dict(self):
        """Test redacting nested dictionary structures."""
        data = {
            "user": {
                "username": "admin",
                "credentials": {
                    "password": "secret123",
                    "api_key": "xyz789"
                }
            },
            "server": "192.168.1.1"
        }
        redacted = redact_sensitive_data(data)
        assert redacted["user"]["username"] == "admin"
        assert redacted["server"] == "192.168.1.1"
        assert redacted["user"]["credentials"]["password"] == "[REDACTED]"
        assert redacted["user"]["credentials"]["api_key"] == "[REDACTED]"
    
    def test_redact_list_of_dicts(self):
        """Test redacting list containing dictionaries."""
        data = [
            {"username": "user1", "password": "pass1"},
            {"username": "user2", "password": "pass2"}
        ]
        redacted = redact_sensitive_data(data)
        assert redacted[0]["username"] == "user1"
        assert redacted[0]["password"] == "[REDACTED]"
        assert redacted[1]["username"] == "user2"
        assert redacted[1]["password"] == "[REDACTED]"
    
    def test_redact_case_insensitive(self):
        """Test that redaction is case-insensitive."""
        data = {
            "PASSWORD": "secret1",
            "Password": "secret2",
            "password": "secret3",
            "API_KEY": "key1",
            "api_key": "key2"
        }
        redacted = redact_sensitive_data(data)
        assert redacted["PASSWORD"] == "[REDACTED]"
        assert redacted["Password"] == "[REDACTED]"
        assert redacted["password"] == "[REDACTED]"
        assert redacted["API_KEY"] == "[REDACTED]"
        assert redacted["api_key"] == "[REDACTED]"
    
    def test_redact_various_sensitive_patterns(self):
        """Test redacting various sensitive field patterns."""
        data = {
            "passwd": "secret",
            "pwd": "secret",
            "secret": "secret",
            "authorization": "Bearer token",
            "x-csrf-token": "csrf-token",
            "session": "session-id",
            "cookie": "cookie-value",
            "private_key": "private-key-data"
        }
        redacted = redact_sensitive_data(data)
        for key in data.keys():
            assert redacted[key] == "[REDACTED]", f"Field '{key}' should be redacted"
    
    def test_redact_non_dict_types(self):
        """Test that non-dict types are handled correctly."""
        assert redact_sensitive_data("string") == "string"
        assert redact_sensitive_data(123) == 123
        assert redact_sensitive_data(45.67) == 45.67
        assert redact_sensitive_data(True) is True
        assert redact_sensitive_data(None) is None
    
    def test_redact_custom_redaction_text(self):
        """Test using custom redaction text."""
        data = {"password": "secret123"}
        redacted = redact_sensitive_data(data, redaction_text="***")
        assert redacted["password"] == "***"
    
    def test_redact_max_depth_protection(self):
        """Test max depth protection against infinite recursion."""
        # Create deeply nested structure
        data = {"level1": {"level2": {"level3": {"password": "secret"}}}}
        redacted = redact_sensitive_data(data, max_depth=2)
        assert "[MAX_DEPTH_EXCEEDED]" in str(redacted)


class TestLoggingSetup:
    """Tests for logging setup."""
    
    def test_setup_logging_default(self):
        """Test default logging setup."""
        logger = setup_logging()
        assert logger is not None
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0
    
    def test_setup_logging_debug_level(self):
        """Test logging setup with DEBUG level."""
        logger = setup_logging(log_level="DEBUG")
        assert logger.level == logging.DEBUG
    
    def test_setup_logging_invalid_level(self):
        """Test that invalid log level raises error."""
        with pytest.raises(ValueError, match="Invalid log level"):
            setup_logging(log_level="INVALID")
    
    def test_setup_logging_with_file(self):
        """Test logging setup with file output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = setup_logging(log_to_file=True, log_file_path=log_file)
            
            # Write a test log
            test_logger = get_logger("test")
            test_logger.info("Test message")
            
            # Close all handlers to release file lock on Windows
            for handler in logger.handlers:
                handler.close()
            logger.handlers.clear()
            
            # Verify file was created and contains log
            assert log_file.exists()
            content = log_file.read_text()
            assert "Test message" in content
    
    def test_setup_logging_file_without_path(self):
        """Test that file logging without path raises error."""
        with pytest.raises(ValueError, match="log_file_path is required"):
            setup_logging(log_to_file=True)
    
    def test_get_logger(self):
        """Test getting a named logger."""
        logger = get_logger("test_module")
        assert logger.name == "test_module"


class TestLogWithRedaction:
    """Tests for log_with_redaction function."""
    
    def test_log_with_redaction_info(self, caplog):
        """Test logging with redaction at INFO level."""
        # Don't call setup_logging to avoid stdout handler
        logger = get_logger("test")
        logger.setLevel(logging.INFO)
        
        with caplog.at_level(logging.INFO, logger="test"):
            log_with_redaction(
                logger,
                "info",
                "User login",
                {"username": "admin", "password": "secret123"}
            )
        
        assert "User login" in caplog.text
        assert "admin" in caplog.text
        assert "secret123" not in caplog.text
        assert "[REDACTED]" in caplog.text
    
    def test_log_with_redaction_no_data(self, caplog):
        """Test logging without additional data."""
        # Don't call setup_logging to avoid stdout handler
        logger = get_logger("test")
        logger.setLevel(logging.INFO)
        
        with caplog.at_level(logging.INFO, logger="test"):
            log_with_redaction(logger, "info", "Simple message")
        
        assert "Simple message" in caplog.text


class TestCorrelationIDInLogs:
    """Tests for correlation ID in log output."""
    
    def test_correlation_id_in_logs(self):
        """Test that correlation ID appears in logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = setup_logging(log_level="INFO", include_correlation_id=True, 
                                   log_to_file=True, log_file_path=log_file)
            
            correlation_id = set_correlation_id("test-correlation-123")
            test_logger = get_logger("test")
            test_logger.info("Test message")
            
            # Close handlers to release file
            for handler in logger.handlers:
                handler.close()
            logger.handlers.clear()
            
            # Check log file
            content = log_file.read_text()
            assert "test-correlation-123" in content
            clear_correlation_id()
    
    def test_no_correlation_id_shows_dash(self):
        """Test that missing correlation ID shows as dash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = setup_logging(log_level="INFO", include_correlation_id=True,
                                   log_to_file=True, log_file_path=log_file)
            
            clear_correlation_id()
            test_logger = get_logger("test")
            test_logger.info("Test message")
            
            # Close handlers to release file
            for handler in logger.handlers:
                handler.close()
            logger.handlers.clear()
            
            # Check log file - should show "-" when no correlation ID is set
            content = log_file.read_text()
            assert "[-]" in content or " - " in content
