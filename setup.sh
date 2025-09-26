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

# Function to update Claude Desktop config
update_claude_config() {
    # Determine config file location based on OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        CONFIG_FILE="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        CONFIG_FILE="$APPDATA/Claude/claude_desktop_config.json"
    else
        CONFIG_FILE="$HOME/.config/Claude/claude_desktop_config.json"
    fi

    # Check if jq is available for JSON manipulation
    if ! command -v jq &> /dev/null; then
        echo "⚠️  jq not found. Installing jq for JSON manipulation..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            if command -v brew &> /dev/null; then
                brew install jq
            else
                echo "❌ Please install jq manually: https://jqlang.github.io/jq/download/"
                return 1
            fi
        elif command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y jq
        elif command -v yum &> /dev/null; then
            sudo yum install -y jq
        else
            echo "❌ Please install jq manually: https://jqlang.github.io/jq/download/"
            return 1
        fi
    fi

    # Create config directory if it doesn't exist
    mkdir -p "$(dirname "$CONFIG_FILE")"

    # Create empty config if file doesn't exist
    if [ ! -f "$CONFIG_FILE" ]; then
        echo '{"mcpServers": {}}' > "$CONFIG_FILE"
        echo "📝 Created new Claude Desktop config file"
    fi

    # Backup existing config
    cp "$CONFIG_FILE" "$CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    echo "📋 Backed up existing config"

    # Determine which command to use (prefer uvx, fallback to uv run)
    UVXPATH=$(which uvx 2>/dev/null || echo ~/.local/bin/uvx)
    if [ -f "$UVXPATH" ]; then
        COMMAND="$UVXPATH"
        ARGS='["--from", "'"$(pwd)"'", "mcp-tradingview"]'
        echo "🔧 Using uvx configuration"
    else
        UVPATH=$(which uv)
        if [ -n "$UVPATH" ]; then
            COMMAND="$UVPATH"
            ARGS='["run", "mcp-tradingview"]'
            echo "🔧 Using uv run configuration"
        else
            echo "❌ Neither uvx nor uv found. Please install uv first."
            return 1
        fi
    fi

    # Update the JSON configuration
    TEMP_FILE=$(mktemp)
    jq --arg cmd "$COMMAND" --argjson args "$ARGS" --arg cwd "$(pwd)" \
       '.mcpServers.tradingview = {"command": $cmd, "args": $args} | if $cmd | contains("uv") and ($cmd | contains("run")) then .mcpServers.tradingview.cwd = $cwd else . end' \
       "$CONFIG_FILE" > "$TEMP_FILE"

    if [ $? -eq 0 ]; then
        mv "$TEMP_FILE" "$CONFIG_FILE"
        echo "✅ Successfully updated Claude Desktop configuration!"
        echo "📍 Config location: $CONFIG_FILE"
        echo ""
        echo "🔄 Configuration added/updated:"
        jq '.mcpServers.tradingview' "$CONFIG_FILE"
    else
        echo "❌ Failed to update configuration"
        rm -f "$TEMP_FILE"
        return 1
    fi
}

echo ""
echo "✅ Setup complete!"
echo ""
echo "🔧 Automatically updating Claude Desktop configuration..."
if update_claude_config; then
    echo ""
    echo "⚠️  Remember to restart Claude Desktop to load the updated configuration!"
else
    echo ""
    echo "❌ Automatic configuration update failed. Manual configuration required:"
    echo ""
    echo "📍 Config file location:"
    echo "   macOS: ~/Library/Application Support/Claude/claude_desktop_config.json"
    echo "   Windows: %APPDATA%\\Claude\\claude_desktop_config.json"
    echo "   Linux: ~/.config/Claude/claude_desktop_config.json"
    echo ""
    echo "Add this configuration:"
    echo "{"
    echo "  \"mcpServers\": {"
    echo "    \"tradingview\": {"
    echo "      \"command\": \"$(which uvx || echo ~/.local/bin/uvx)\","
    echo "      \"args\": [\"--from\", \"$(pwd)\", \"mcp-tradingview\"]"
    echo "    }"
    echo "  }"
    echo "}"
fi
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
