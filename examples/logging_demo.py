"""Demo script showing logging system with redaction capabilities.

This script demonstrates:
- Setting up logging with different levels
- Automatic sensitive data redaction
- Correlation ID tracking
- File logging
"""

import sys
from pathlib import Path

# Add src to path for demo purposes
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from unifi_mcp.utils.logging import (
    get_logger,
    log_with_redaction,
    set_correlation_id,
    setup_logging,
)


def demo_basic_logging():
    """Demonstrate basic logging setup."""
    print("\n=== Demo 1: Basic Logging ===")
    
    # Setup logging
    setup_logging(log_level="INFO")
    logger = get_logger("demo")
    
    logger.info("Server starting...")
    logger.debug("This won't show at INFO level")
    logger.warning("This is a warning")
    logger.error("This is an error")


def demo_sensitive_data_redaction():
    """Demonstrate automatic sensitive data redaction."""
    print("\n=== Demo 2: Sensitive Data Redaction ===")
    
    setup_logging(log_level="INFO")
    logger = get_logger("demo")
    
    # This will automatically redact the password
    log_with_redaction(
        logger,
        "info",
        "User authentication attempt",
        {
            "username": "admin",
            "password": "super_secret_password",
            "ip_address": "192.168.1.100"
        }
    )
    
    # Nested sensitive data
    log_with_redaction(
        logger,
        "info",
        "API request",
        {
            "endpoint": "/api/login",
            "headers": {
                "Authorization": "Bearer secret-token-here",
                "Content-Type": "application/json"
            },
            "body": {
                "username": "user@example.com",
                "api_key": "abc123xyz789"
            }
        }
    )


def demo_correlation_id():
    """Demonstrate correlation ID tracking."""
    print("\n=== Demo 3: Correlation ID Tracking ===")
    
    setup_logging(log_level="INFO", include_correlation_id=True)
    logger = get_logger("demo")
    
    # Set correlation ID for request tracking
    correlation_id = set_correlation_id("req-12345")
    
    logger.info("Processing request")
    logger.info("Connecting to UniFi controller")
    logger.info("Request completed successfully")
    
    print(f"\nAll logs above have correlation ID: {correlation_id}")


def demo_different_log_levels():
    """Demonstrate different log levels."""
    print("\n=== Demo 4: Different Log Levels ===")
    
    print("\nWith DEBUG level:")
    setup_logging(log_level="DEBUG")
    logger = get_logger("demo")
    
    logger.debug("Debug message - shows at DEBUG level")
    logger.info("Info message")
    logger.warning("Warning message")
    
    print("\nWith WARNING level:")
    setup_logging(log_level="WARNING")
    logger = get_logger("demo")
    
    logger.debug("Debug message - won't show")
    logger.info("Info message - won't show")
    logger.warning("Warning message - shows at WARNING level")
    logger.error("Error message - shows at WARNING level")


def demo_file_logging():
    """Demonstrate logging to file."""
    print("\n=== Demo 5: File Logging ===")
    
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "demo.log"
        
        setup_logging(
            log_level="INFO",
            log_to_file=True,
            log_file_path=log_file
        )
        logger = get_logger("demo")
        
        logger.info("This goes to both console and file")
        log_with_redaction(
            logger,
            "info",
            "Sensitive data logged",
            {"username": "admin", "password": "secret"}
        )
        
        # Close handlers to flush
        import logging
        for handler in logging.getLogger().handlers:
            handler.close()
        
        print(f"\nLog file created at: {log_file}")
        print("Log file contents:")
        print("-" * 60)
        print(log_file.read_text())
        print("-" * 60)


if __name__ == "__main__":
    print("UniFi MCP Server - Logging System Demo")
    print("=" * 60)
    
    demo_basic_logging()
    demo_sensitive_data_redaction()
    demo_correlation_id()
    demo_different_log_levels()
    demo_file_logging()
    
    print("\n" + "=" * 60)
    print("Demo complete!")
