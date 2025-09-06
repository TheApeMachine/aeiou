#!/bin/bash

# AEIOU Development Environment Setup Script

set -e

echo "🚀 Setting up AEIOU development environment..."

# Check if we're in the right directory
if [ ! -f "Makefile" ] || [ ! -d "sidecar" ] || [ ! -d "nvim" ]; then
    echo "❌ Error: Please run this script from the AEIOU project root directory"
    exit 1
fi

# Create virtual environment
echo "📦 Creating Python virtual environment..."
cd sidecar
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Initialize database
echo "🗄️  Initializing database..."
python -c "from app.memory_store import MemoryStore; MemoryStore()"

# Setup pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
pre-commit install

# Create .env file template
if [ ! -f ".env" ]; then
    echo "📝 Creating .env template..."
    cat > .env << EOF
# AEIOU Environment Configuration

# OpenAI API Key (required for AI features)
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration
DATABASE_URL=sqlite:///aeiou_memory.db

# Server Configuration
HOST=127.0.0.1
PORT=8000
DEBUG=True

# Logging
LOG_LEVEL=INFO
LOG_FILE=aeiou.log

# Feature Flags
ENABLE_RAG=True
ENABLE_VCS_INTEGRATION=True
ENABLE_PERMISSION_SYSTEM=True
EOF
    echo "⚠️  Please edit sidecar/.env and add your OpenAI API key"
fi

cd ..

# Setup Neovim plugin for development
echo "🔧 Setting up Neovim plugin for development..."
if [ -d "~/.local/share/nvim/site/pack/aeiou" ]; then
    echo "📁 Neovim plugin directory already exists"
else
    mkdir -p ~/.local/share/nvim/site/pack/aeiou/start
    ln -sf $(pwd)/nvim ~/.local/share/nvim/site/pack/aeiou/start/
    echo "🔗 Created Neovim plugin symlink"
fi

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit sidecar/.env and add your OpenAI API key"
echo "2. Run 'make run' to start the sidecar"
echo "3. Open Neovim and run ':AeiouTranscode' to test"
echo ""
echo "Available make targets:"
make help