#!/bin/bash
#
# Install Git hooks for this repository
#

set -e

HOOKS_DIR=".git/hooks"
PRE_PUSH_HOOK="$HOOKS_DIR/pre-push"

echo "Installing Git pre-push hook..."

# Create hooks directory if it doesn't exist
mkdir -p "$HOOKS_DIR"

# Backup existing hook if it exists
if [ -f "$PRE_PUSH_HOOK" ]; then
    echo "Backing up existing pre-push hook..."
    cp "$PRE_PUSH_HOOK" "$PRE_PUSH_HOOK.bak"
fi

# Write the pre-push hook
cat > "$PRE_PUSH_HOOK" << 'HOOK_EOF'
#!/bin/bash
#
# Pre-push hook to ensure code is formatted before pushing
# This hook runs `make format` to auto-format code before pushing to remote
#

set -e

echo "🔍 Running pre-push checks..."
echo "📝 Formatting code with make format..."

# Check if uv is available, use it if present, otherwise use make directly
if command -v uv > /dev/null 2>&1; then
    echo "Using uv to run make format..."
    uv run make format
else
    echo "uv not found, using make directly..."
    make format
fi

# Check if there are any uncommitted changes after formatting
if ! git diff --quiet; then
    echo ""
    echo "⚠️  Code was reformatted. Please review and commit the changes:"
    echo ""
    git diff --stat
    echo ""
    echo "Run: git add -A && git commit -m 'chore: auto-format code'"
    echo ""
    echo "❌ Push aborted. Please commit the formatting changes first."
    exit 1
fi

echo "✅ Code is properly formatted. Proceeding with push..."
exit 0
HOOK_EOF

# Make the hook executable
chmod +x "$PRE_PUSH_HOOK"

echo "✅ Pre-push hook installed successfully!"
echo "The hook will automatically run 'make format' before every push."
