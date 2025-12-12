#!/usr/bin/env bash
#
# MCP Inspector Wrapper Script for UniFi MCP Server
#
# This script provides a convenient way to test the UniFi MCP Server using
# the MCP Inspector tool. It handles environment setup, server startup,
# inspector invocation, protocol compliance validation, and tool schema testing.
#
# Usage:
#   ./mcp_inspector.sh [mode] [options]
#
# Modes:
#   interactive  - Launch interactive inspector session (default)
#   validate     - Validate protocol compliance
#   list-tools   - List all available tools
#   test-tool    - Test a specific tool
#   test-all     - Test all tools
#
# Examples:
#   ./mcp_inspector.sh
#   ./mcp_inspector.sh validate
#   ./mcp_inspector.sh list-tools
#   ./mcp_inspector.sh test-tool unifi_list_devices
#   ./mcp_inspector.sh test-tool unifi_list_devices '{"device_type": "switch"}'
#
# Requirements:
#   - Python 3.11+
#   - npx (Node.js package runner)
#   - MCP Inspector (@modelcontextprotocol/inspector)
#   - UniFi MCP Server installed (pip install -e .)
#   - Valid .env file with UniFi credentials

set -euo pipefail

# Colors
COLOR_SUCCESS='\033[0;32m'
COLOR_ERROR='\033[0;31m'
COLOR_WARNING='\033[0;33m'
COLOR_INFO='\033[0;36m'
COLOR_RESET='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default values
MODE="${1:-interactive}"
TOOL_NAME="${2:-}"
TOOL_ARGS="${3:-{}}"

# Helper functions
print_success() {
    echo -e "${COLOR_SUCCESS}$1${COLOR_RESET}"
}

print_error() {
    echo -e "${COLOR_ERROR}$1${COLOR_RESET}" >&2
}

print_warning() {
    echo -e "${COLOR_WARNING}$1${COLOR_RESET}"
}

print_info() {
    echo -e "${COLOR_INFO}$1${COLOR_RESET}"
}

print_header() {
    print_info "
╔═══════════════════════════════════════════════════════════╗
║         UniFi MCP Server - MCP Inspector Wrapper          ║
╚═══════════════════════════════════════════════════════════╝
"
}

check_prerequisites() {
    print_info "\n=== Checking Prerequisites ==="
    
    local all_good=true
    
    # Check Python
    echo -n "Checking Python... "
    if command -v python3 &> /dev/null; then
        local python_version=$(python3 --version 2>&1)
        if [[ $python_version =~ Python\ 3\.1[1-9] ]]; then
            print_success "✓ $python_version"
        else
            print_error "✗ Python 3.11+ required, found: $python_version"
            all_good=false
        fi
    else
        print_error "✗ Python not found"
        all_good=false
    fi
    
    # Check npx
    echo -n "Checking npx... "
    if command -v npx &> /dev/null; then
        local npx_version=$(npx --version 2>&1)
        print_success "✓ npx $npx_version"
    else
        print_error "✗ npx not found (install Node.js)"
        all_good=false
    fi
    
    # Check .env file
    echo -n "Checking .env file... "
    if [ -f "$PROJECT_ROOT/.env" ]; then
        print_success "✓ Found"
    else
        print_error "✗ Not found (copy .env.example to .env)"
        all_good=false
    fi
    
    # Check if server is installed
    echo -n "Checking UniFi MCP Server... "
    if python3 -c "import unifi_mcp" 2>/dev/null; then
        print_success "✓ Installed"
    else
        print_error "✗ Not installed (run: pip install -e .)"
        all_good=false
    fi
    
    if [ "$all_good" = false ]; then
        print_error "\n✗ Prerequisites check failed. Please fix the issues above."
        exit 1
    fi
    
    print_success "\n✓ All prerequisites met"
}

start_interactive_inspector() {
    print_info "\n=== Starting Interactive MCP Inspector ==="
    print_info "This will launch an interactive session where you can:"
    print_info "  - List available tools"
    print_info "  - Invoke tools with custom arguments"
    print_info "  - Inspect request/response messages"
    print_info "  - Validate protocol compliance"
    print_warning "\nPress Ctrl+C to exit the inspector\n"
    
    # Run inspector with the server command
    cd "$PROJECT_ROOT"
    npx @modelcontextprotocol/inspector python3 -m unifi_mcp
}

test_protocol_compliance() {
    print_info "\n=== Validating Protocol Compliance ==="
    
    # Create a temporary test script
    local test_script=$(mktemp)
    cat > "$test_script" << 'EOF'
import asyncio
import json
import sys
from unifi_mcp.server import UniFiMCPServer
from unifi_mcp.config.loader import load_config

async def validate():
    try:
        config = load_config()
        server = UniFiMCPServer(config)
        
        # Test initialization
        print("✓ Server initialization successful")
        
        # Test tool listing
        tools = await server.list_tools()
        print(f"✓ Tool listing successful ({len(tools)} tools)")
        
        # Validate tool schemas
        for tool in tools:
            if not tool.get('name'):
                print(f"✗ Tool missing name: {tool}")
                sys.exit(1)
            if not tool.get('description'):
                print(f"✗ Tool missing description: {tool['name']}")
                sys.exit(1)
            if not tool.get('inputSchema'):
                print(f"✗ Tool missing inputSchema: {tool['name']}")
                sys.exit(1)
        
        print(f"✓ All tool schemas valid")
        print(f"\n✓ Protocol compliance validation passed")
        
    except Exception as e:
        print(f"✗ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

asyncio.run(validate())
EOF
    
    cd "$PROJECT_ROOT"
    if python3 "$test_script"; then
        print_success "\n✓ Protocol compliance validation passed"
    else
        print_error "\n✗ Protocol compliance validation failed"
        rm -f "$test_script"
        exit 1
    fi
    
    rm -f "$test_script"
}

get_tool_list() {
    print_info "\n=== Listing Available Tools ==="
    
    local test_script=$(mktemp)
    cat > "$test_script" << 'EOF'
import asyncio
import json
from unifi_mcp.server import UniFiMCPServer
from unifi_mcp.config.loader import load_config

async def list_tools():
    config = load_config()
    server = UniFiMCPServer(config)
    tools = await server.list_tools()
    
    # Group by category
    categories = {}
    for tool in tools:
        category = tool.get('category', 'general')
        if category not in categories:
            categories[category] = []
        categories[category].append(tool)
    
    # Print organized list
    for category, cat_tools in sorted(categories.items()):
        print(f"\n{category.upper()}:")
        for tool in sorted(cat_tools, key=lambda t: t['name']):
            print(f"  - {tool['name']}")
            print(f"    {tool['description']}")
    
    print(f"\nTotal: {len(tools)} tools")

asyncio.run(list_tools())
EOF
    
    cd "$PROJECT_ROOT"
    python3 "$test_script"
    rm -f "$test_script"
}

test_single_tool() {
    local name="$1"
    local args="$2"
    
    print_info "\n=== Testing Tool: $name ==="
    
    local test_script=$(mktemp)
    cat > "$test_script" << EOF
import asyncio
import json
from unifi_mcp.server import UniFiMCPServer
from unifi_mcp.config.loader import load_config

async def test_tool():
    try:
        config = load_config()
        server = UniFiMCPServer(config)
        
        # Parse arguments
        args = json.loads('$args')
        
        print(f"Tool: $name")
        print(f"Arguments: {json.dumps(args, indent=2)}")
        print()
        
        # Invoke tool
        result = await server.invoke_tool('$name', args)
        
        print("Result:")
        print(json.dumps(result, indent=2))
        print()
        print("✓ Tool invocation successful")
        
    except Exception as e:
        print(f"✗ Tool invocation failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

asyncio.run(test_tool())
EOF
    
    cd "$PROJECT_ROOT"
    if python3 "$test_script"; then
        print_success "\n✓ Tool test passed"
    else
        print_error "\n✗ Tool test failed"
        rm -f "$test_script"
        exit 1
    fi
    
    rm -f "$test_script"
}

test_all_tools() {
    print_info "\n=== Testing All Tools ==="
    print_warning "This will test basic invocation of all tools (without arguments)"
    
    local test_script=$(mktemp)
    cat > "$test_script" << 'EOF'
import asyncio
import json
from unifi_mcp.server import UniFiMCPServer
from unifi_mcp.config.loader import load_config

async def test_all():
    config = load_config()
    server = UniFiMCPServer(config)
    tools = await server.list_tools()
    
    passed = 0
    failed = 0
    skipped = 0
    
    for tool in tools:
        name = tool['name']
        schema = tool.get('inputSchema', {})
        required = schema.get('required', [])
        
        # Skip tools that require arguments
        if required:
            print(f"⊘ {name} (requires arguments: {', '.join(required)})")
            skipped += 1
            continue
        
        try:
            result = await server.invoke_tool(name, {})
            print(f"✓ {name}")
            passed += 1
        except Exception as e:
            print(f"✗ {name}: {e}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed, {skipped} skipped")
    
    if failed > 0:
        exit(1)

asyncio.run(test_all())
EOF
    
    cd "$PROJECT_ROOT"
    if python3 "$test_script"; then
        print_success "\n✓ All tool tests passed"
    else
        print_error "\n✗ Some tool tests failed"
        rm -f "$test_script"
        exit 1
    fi
    
    rm -f "$test_script"
}

show_usage() {
    cat << EOF
Usage: $0 [mode] [options]

Modes:
  interactive  - Launch interactive inspector session (default)
  validate     - Validate protocol compliance
  list-tools   - List all available tools
  test-tool    - Test a specific tool
  test-all     - Test all tools

Examples:
  $0
  $0 validate
  $0 list-tools
  $0 test-tool unifi_list_devices
  $0 test-tool unifi_list_devices '{"device_type": "switch"}'

Requirements:
  - Python 3.11+
  - npx (Node.js package runner)
  - MCP Inspector (@modelcontextprotocol/inspector)
  - UniFi MCP Server installed (pip install -e .)
  - Valid .env file with UniFi credentials
EOF
}

# Main execution
print_header

# Check for help flag
if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
    show_usage
    exit 0
fi

# Check prerequisites
check_prerequisites

# Execute based on mode
case "$MODE" in
    interactive)
        start_interactive_inspector
        ;;
    validate)
        test_protocol_compliance
        ;;
    list-tools)
        get_tool_list
        ;;
    test-tool)
        if [ -z "$TOOL_NAME" ]; then
            print_error "✗ Error: Tool name is required for test-tool mode"
            echo ""
            show_usage
            exit 1
        fi
        test_single_tool "$TOOL_NAME" "$TOOL_ARGS"
        ;;
    test-all)
        test_all_tools
        ;;
    *)
        print_error "✗ Error: Unknown mode: $MODE"
        echo ""
        show_usage
        exit 1
        ;;
esac

print_success "\n✓ Done"
