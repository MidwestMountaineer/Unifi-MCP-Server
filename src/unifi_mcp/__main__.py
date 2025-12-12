"""Main entry point for UniFi MCP Server.

This module provides the command-line entry point for running the server.
It handles:
- Configuration loading
- Logging setup
- Server initialization and startup
- Graceful shutdown
"""

import asyncio
import sys
from pathlib import Path

from .config.loader import Config, ConfigurationError, load_config
from .server import main as server_main
from .utils.logging import setup_logging, get_logger


def main() -> None:
    """Main entry point for the UniFi MCP server.
    
    This function:
    1. Loads configuration from YAML and environment variables
    2. Sets up logging
    3. Starts the MCP server
    4. Handles graceful shutdown
    
    Exit codes:
        0: Normal exit
        1: Configuration error
        2: Runtime error
    """
    try:
        # Load configuration
        config = load_config()
        
        # Setup logging
        setup_logging(
            log_level=config.server.log_level,
            log_to_file=config.server.logging.get("log_to_file", False),
            log_file_path=config.server.logging.get("log_file_path"),
        )
        
        logger = get_logger(__name__)
        logger.info("Starting UniFi MCP Server")
        
        # Run the server
        asyncio.run(server_main(config))
        
        logger.info("UniFi MCP Server stopped normally")
        sys.exit(0)
    
    except ConfigurationError as e:
        # Configuration error - print to stderr and exit
        print(f"Configuration Error: {e}", file=sys.stderr)
        print("\nPlease check your configuration and environment variables.", file=sys.stderr)
        print("See .env.example for reference.", file=sys.stderr)
        sys.exit(1)
    
    except KeyboardInterrupt:
        # User interrupted - exit gracefully
        print("\nShutdown requested by user", file=sys.stderr)
        sys.exit(0)
    
    except Exception as e:
        # Unexpected error
        print(f"Fatal Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
