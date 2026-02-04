# Provider Application - Enterprise App Setup

This component handles the setup and management of the Azure App Registration that will be shared with customers as a multi-tenant enterprise application.

## 🎯 Purpose

The provider app is responsible for:
- Creating an Azure App Registration configured for multi-tenancy
- Setting up appropriate API permissions
- Configuring authentication flows (OAuth 2.0, OIDC)
- Managing service principal and secrets
- Providing onboarding materials for customers

## 📋 Prerequisites

- Azure subscription with permissions to create App Registrations
- Azure CLI installed (`az --version` to verify)
- Python 3.10+
- Owner or Application Administrator role in Azure AD

## 🚀 Setup Instructions

### 1. Install Dependencies

```bash
cd provider-app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your Azure tenant details:

```env
AZURE_TENANT_ID=your-tenant-id
PROVIDER_APP_NAME=planetary-computer-provider
```

### 3. Run Provider Setup

```bash
python setup_provider_app.py
```

This will:
1. Create a multi-tenant App Registration
2. Configure OAuth 2.0 permissions
3. Generate client secret
4. Set up redirect URIs
5. Output customer onboarding information

## 📁 Files

- `setup_provider_app.py` - Main setup script
- `requirements.txt` - Python dependencies
- `.env` - Configuration (not committed to git)

## 🔧 Key Features

### Multi-Tenant Configuration
The app registration will be configured to support:
- Multiple customer tenants
- Consent workflow
- Admin consent requirements

### API Permissions
Default permissions include:
- Microsoft Graph API (User.Read)
- Azure Resource Manager (user_impersonation)
- Custom GeoCatalog permissions

### Authentication Flows
Supports:
- Authorization Code flow (web apps)
- Device Code flow (CLI/scripts)
- Client Credentials flow (service-to-service)

## 📤 Customer Onboarding

After setup, you'll receive:
1. **Application (client) ID**: Share with customers
2. **Tenant ID**: Your provider tenant
3. **Onboarding documentation**: Auto-generated for customers
4. **Admin consent URL**: For customer admin approval

## 🔐 Security Best Practices

- Rotate client secrets regularly (90-day cycle recommended)
- Use Azure Key Vault for production secrets
- Enable audit logging
- Review app permissions quarterly
- Implement conditional access policies


## 📚 Additional Resources

- [Azure App Registration Best Practices](https://learn.microsoft.com/en-us/azure/active-directory/develop/security-best-practices-for-app-registration)
- [Multi-tenant SaaS Applications](https://learn.microsoft.com/en-us/azure/active-directory/develop/single-and-multi-tenant-apps)

## 🐛 Troubleshooting

Common issues and solutions will be documented here as they arise.

## 📞 Support

For issues specific to provider setup, please check the troubleshooting section or contact the development team.
