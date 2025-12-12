#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Wrapper script for testing UniFi MCP Server with MCP Inspector

.DESCRIPTION
    This script provides a convenient way to test the UniFi MCP Server using
    the MCP Inspector tool. It handles:
    - Environment setup
    - Server startup
    - Inspector invocation
    - Protocol compliance validation
    - Tool schema testing

.PARAMETER Mode
    The testing mode to use:
    - interactive: Launch interactive inspector session (default)
    - validate: Validate protocol compliance
    - list-tools: List all available tools
    - test-tool: Test a specific tool
    - test-all: Test all tools

.PARAMETER ToolName
    The name of the tool to test (required when Mode is 'test-tool')

.PARAMETER ToolArgs
    JSON arguments for the tool (optional, used with 'test-tool')

.PARAMETER Verbose
    Enable verbose output

.EXAMPLE
    .\mcp_inspector.ps1
    Launch interactive inspector session

.EXAMPLE
    .\mcp_inspector.ps1 -Mode validate
    Validate protocol compliance

.EXAMPLE
    .\mcp_inspector.ps1 -Mode list-tools
    List all available tools

.EXAMPLE
    .\mcp_inspector.ps1 -Mode test-tool -ToolName unifi_list_devices
    Test a specific tool

.EXAMPLE
    .\mcp_inspector.ps1 -Mode test-tool -ToolName unifi_list_devices -ToolArgs '{"device_type": "switch"}'
    Test a tool with arguments

.NOTES
    Requires:
    - Python 3.11+
    - npx (Node.js package runner)
    - MCP Inspector (@modelcontextprotocol/inspector)
    - UniFi MCP Server installed (pip install -e .)
    - Valid .env file with UniFi credentials
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('interactive', 'validate', 'list-tools', 'test-tool', 'test-all')]
    [string]$Mode = 'interactive',
    
    [Parameter()]
    [string]$ToolName = '',
    
    [Parameter()]
    [string]$ToolArgs = '{}',
    
    [Parameter()]
    [switch]$Verbose
)

# Set error action preference
$ErrorActionPreference = 'Stop'

# Colors for output
$ColorSuccess = 'Green'
$ColorError = 'Red'
$ColorWarning = 'Yellow'
$ColorInfo = 'Cyan'

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = 'White',
        [switch]$NoNewline
    )
    
    if ($NoNewline) {
        Write-Host $Message -ForegroundColor $Color -NoNewline
    } else {
        Write-Host $Message -ForegroundColor $Color
    }
}

function Test-Prerequisites {
    Write-ColorOutput "`n=== Checking Prerequisites ===" -Color $ColorInfo
    
    $allGood = $true
    
    # Check Python
    Write-ColorOutput "Checking Python..." -Color $ColorInfo -NoNewline
    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match 'Python 3\.1[1-9]') {
            Write-ColorOutput " ✓ $pythonVersion" -Color $ColorSuccess
        } else {
            Write-ColorOutput " ✗ Python 3.11+ required, found: $pythonVersion" -Color $ColorError
            $allGood = $false
        }
    } catch {
        Write-ColorOutput " ✗ Python not found" -Color $ColorError
        $allGood = $false
    }
    
    # Check npx
    Write-ColorOutput "Checking npx..." -Color $ColorInfo -NoNewline
    try {
        $npxVersion = npx --version 2>&1
        Write-ColorOutput " ✓ npx $npxVersion" -Color $ColorSuccess
    } catch {
        Write-ColorOutput " ✗ npx not found (install Node.js)" -Color $ColorError
        $allGood = $false
    }
    
    # Check .env file
    Write-ColorOutput "Checking .env file..." -Color $ColorInfo -NoNewline
    $envFile = Join-Path $PSScriptRoot ".." ".env"
    if (Test-Path $envFile) {
        Write-ColorOutput " ✓ Found" -Color $ColorSuccess
    } else {
        Write-ColorOutput " ✗ Not found (copy .env.example to .env)" -Color $ColorError
        $allGood = $false
    }
    
    # Check if server is installed
    Write-ColorOutput "Checking UniFi MCP Server..." -Color $ColorInfo -NoNewline
    try {
        $serverCheck = python -c "import unifi_mcp; print('OK')" 2>&1
        if ($serverCheck -match 'OK') {
            Write-ColorOutput " ✓ Installed" -Color $ColorSuccess
        } else {
            Write-ColorOutput " ✗ Not installed (run: pip install -e .)" -Color $ColorError
            $allGood = $false
        }
    } catch {
        Write-ColorOutput " ✗ Not installed (run: pip install -e .)" -Color $ColorError
        $allGood = $false
    }
    
    if (-not $allGood) {
        Write-ColorOutput "`n✗ Prerequisites check failed. Please fix the issues above." -Color $ColorError
        exit 1
    }
    
    Write-ColorOutput "`n✓ All prerequisites met" -Color $ColorSuccess
}

function Start-InteractiveInspector {
    Write-ColorOutput "`n=== Starting Interactive MCP Inspector ===" -Color $ColorInfo
    Write-ColorOutput "This will launch an interactive session where you can:" -Color $ColorInfo
    Write-ColorOutput "  - List available tools" -Color $ColorInfo
    Write-ColorOutput "  - Invoke tools with custom arguments" -Color $ColorInfo
    Write-ColorOutput "  - Inspect request/response messages" -Color $ColorInfo
    Write-ColorOutput "  - Validate protocol compliance" -Color $ColorInfo
    Write-ColorOutput "`nPress Ctrl+C to exit the inspector`n" -Color $ColorWarning
    
    # Run inspector with the server command
    npx @modelcontextprotocol/inspector python -m unifi_mcp
}

function Test-ProtocolCompliance {
    Write-ColorOutput "`n=== Validating Protocol Compliance ===" -Color $ColorInfo
    
    # Create a temporary test script
    $testScript = @"
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
"@
    
    $tempFile = [System.IO.Path]::GetTempFileName() + ".py"
    $testScript | Out-File -FilePath $tempFile -Encoding UTF8
    
    try {
        python $tempFile
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "`n✓ Protocol compliance validation passed" -Color $ColorSuccess
        } else {
            Write-ColorOutput "`n✗ Protocol compliance validation failed" -Color $ColorError
            exit 1
        }
    } finally {
        Remove-Item $tempFile -ErrorAction SilentlyContinue
    }
}

function Get-ToolList {
    Write-ColorOutput "`n=== Listing Available Tools ===" -Color $ColorInfo
    
    $testScript = @"
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
"@
    
    $tempFile = [System.IO.Path]::GetTempFileName() + ".py"
    $testScript | Out-File -FilePath $tempFile -Encoding UTF8
    
    try {
        python $tempFile
    } finally {
        Remove-Item $tempFile -ErrorAction SilentlyContinue
    }
}

function Test-SingleTool {
    param(
        [string]$Name,
        [string]$Args
    )
    
    Write-ColorOutput "`n=== Testing Tool: $Name ===" -Color $ColorInfo
    
    $testScript = @"
import asyncio
import json
from unifi_mcp.server import UniFiMCPServer
from unifi_mcp.config.loader import load_config

async def test_tool():
    try:
        config = load_config()
        server = UniFiMCPServer(config)
        
        # Parse arguments
        args = json.loads('$Args')
        
        print(f"Tool: $Name")
        print(f"Arguments: {json.dumps(args, indent=2)}")
        print()
        
        # Invoke tool
        result = await server.invoke_tool('$Name', args)
        
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
"@
    
    $tempFile = [System.IO.Path]::GetTempFileName() + ".py"
    $testScript | Out-File -FilePath $tempFile -Encoding UTF8
    
    try {
        python $tempFile
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "`n✓ Tool test passed" -Color $ColorSuccess
        } else {
            Write-ColorOutput "`n✗ Tool test failed" -Color $ColorError
            exit 1
        }
    } finally {
        Remove-Item $tempFile -ErrorAction SilentlyContinue
    }
}

function Test-AllTools {
    Write-ColorOutput "`n=== Testing All Tools ===" -Color $ColorInfo
    Write-ColorOutput "This will test basic invocation of all tools (without arguments)" -Color $ColorWarning
    
    $testScript = @"
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
"@
    
    $tempFile = [System.IO.Path]::GetTempFileName() + ".py"
    $testScript | Out-File -FilePath $tempFile -Encoding UTF8
    
    try {
        python $tempFile
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "`n✓ All tool tests passed" -Color $ColorSuccess
        } else {
            Write-ColorOutput "`n✗ Some tool tests failed" -Color $ColorError
            exit 1
        }
    } finally {
        Remove-Item $tempFile -ErrorAction SilentlyContinue
    }
}

# Main execution
Write-ColorOutput @"

╔═══════════════════════════════════════════════════════════╗
║         UniFi MCP Server - MCP Inspector Wrapper          ║
╚═══════════════════════════════════════════════════════════╝
"@ -Color $ColorInfo

# Check prerequisites
Test-Prerequisites

# Execute based on mode
switch ($Mode) {
    'interactive' {
        Start-InteractiveInspector
    }
    'validate' {
        Test-ProtocolCompliance
    }
    'list-tools' {
        Get-ToolList
    }
    'test-tool' {
        if (-not $ToolName) {
            Write-ColorOutput "✗ Error: -ToolName is required for test-tool mode" -Color $ColorError
            exit 1
        }
        Test-SingleTool -Name $ToolName -Args $ToolArgs
    }
    'test-all' {
        Test-AllTools
    }
}

Write-ColorOutput "`n✓ Done" -Color $ColorSuccess
