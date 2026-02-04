#!/bin/bash
# Quick setup script for customer-app

set -e

echo "=========================================="
echo "  Customer App Setup"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "register_provider_app.py" ]; then
    echo "❌ Error: Please run this script from the customer-app directory"
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
    echo "⚠️  Please edit .env with provider app details:"
    echo "   - CUSTOMER_TENANT_ID (your tenant)"
    echo "   - PROVIDER_CLIENT_ID (from provider)"
    echo "   - PROVIDER_REDIRECT_URI (from provider)"
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
echo "1. Get provider app details from your ISV/provider"
echo "2. Edit .env with the provider app credentials"
echo "3. Activate the virtual environment:"
echo "   source .venv/bin/activate"
echo "4. Login to Azure (customer tenant):"
echo "   az login --tenant <your-customer-tenant-id>"
echo "5. Run the registration script:"
echo "   python register_provider_app.py"
echo ""
