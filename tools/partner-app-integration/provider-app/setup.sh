#!/bin/bash
# Quick setup script for provider-app

set -e

echo "=========================================="
echo "  Provider App Setup"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "setup_provider_app.py" ]; then
    echo "❌ Error: Please run this script from the provider-app directory"
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv .venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  Please edit .env with your Azure credentials:"
    echo "   - AZURE_TENANT_ID"
    echo ""
    echo "   nano .env  # or use your favorite editor"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "=========================================="
echo "  ✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env with your Azure credentials"
echo "2. Activate the virtual environment:"
echo "   source .venv/bin/activate"
echo "3. Login to Azure:"
echo "   az login"
echo "4. Run the setup script:"
echo "   python setup_provider_app.py"
echo ""
