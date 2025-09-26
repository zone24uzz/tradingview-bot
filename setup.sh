#!/bin/bash
# Quick setup script for MCP TradingView Server
# This script can be run multiple times safely - it will update dependencies

echo "Setting up MCP TradingView Server with uv..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "Please restart your terminal or run 'source ~/.bashrc' (or ~/.zshrc) and run this script again."
    exit 1
fi

# Check if uvx is available after uv installation
if ! command -v uvx &> /dev/null; then
    echo "⚠️  uvx not found in PATH. This may cause issues with Claude Desktop."
    echo "uvx is typically installed in ~/.local/bin/"
    if [ -f ~/.local/bin/uvx ]; then
        echo "✅ Found uvx at ~/.local/bin/uvx"
        echo "💡 Note: Configuration examples below use full path to handle this."
    fi
fi

# Create virtual environment
echo "Creating virtual environment..."
uv venv --python 3.11

# Install dependencies
echo "Installing dependencies..."
if ! uv pip install -e .; then
    echo "❌ Installation failed. Please check the error message above."
    exit 1
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To configure with Claude Desktop, add this to your claude_desktop_config.json:"
echo ""
echo "📍 Config file location:"
echo "   macOS: ~/Library/Application Support/Claude/claude_desktop_config.json"
echo "   Windows: %APPDATA%\\Claude\\claude_desktop_config.json"
echo "   Linux: ~/.config/Claude/claude_desktop_config.json"
echo ""
echo "{"
echo "  \"mcpServers\": {"
echo "    \"tradingview\": {"
echo "      \"command\": \"$(pwd)/.venv/bin/python\","
echo "      \"args\": [\"$(pwd)/tradingview_server.py\"],"
echo "      \"cwd\": \"$(pwd)\""
echo "    }"
echo "  }"
echo "}"
echo ""
echo "Alternative configuration with uvx (recommended):"
echo "{"
echo "  \"mcpServers\": {"
echo "    \"tradingview\": {"
echo "      \"command\": \"$(which uvx || echo ~/.local/bin/uvx)\","
echo "      \"args\": [\"--from\", \"$(pwd)\", \"mcp-tradingview\"]"
echo "    }"
echo "  }"
echo "}"
echo ""
echo "Alternative configuration with uv run:"
echo "{"
echo "  \"mcpServers\": {"
echo "    \"tradingview\": {"
echo "      \"command\": \"$(which uv)\","
echo "      \"args\": [\"run\", \"mcp-tradingview\"],"
echo "      \"cwd\": \"$(pwd)\""
echo "    }"
echo "  }"
echo "}"
echo ""
echo "HTTP transport configuration with uv run:"
echo "{"
echo "  \"mcpServers\": {"
echo "    \"tradingview\": {"
echo "      \"command\": \"$(which uv)\","
echo "      \"args\": [\"run\", \"mcp-tradingview\", \"--transport\", \"http\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\", \"--path\", \"/mcp\"],"
echo "      \"cwd\": \"$(pwd)\""
echo "    }"
echo "  }"
echo "}"
echo ""
echo "⚠️  Remember to restart Claude Desktop after updating the configuration!"
echo ""
echo "🔧 Troubleshooting:"
echo "If you see 'spawn uvx ENOENT' error in Claude Desktop logs:"
echo "1. Make sure uvx is installed: which uvx"
echo "2. If uvx is in ~/.local/bin/, use full path in config:"
echo "   \"command\": \"$(which uvx 2>/dev/null || echo ~/.local/bin/uvx)\""
echo "3. Alternative: Use uv run instead of uvx (see configuration above)"
echo ""
echo "📍 Check if uv/uvx is in PATH:"
echo "   echo \$PATH | grep -q ~/.local/bin && echo \"✅ PATH ok\" || echo \"❌ Add ~/.local/bin to PATH\""
