# 🚀 Quick Reference Card

## Repository Overview
```
partner-app-integration/
├── client-app/     # Original testing code
├── provider-app/   # Multi-tenant app setup
└── customer-app/   # Customer registration
```

## Provider App Quick Commands

```bash
cd provider-app
./setup.sh                           # Initial setup
source .venv/bin/activate            # Activate venv
az login                             # Login to Azure
python setup_provider_app.py         # Create multi-tenant app
```

**Output**: `customer_onboarding.json` (share with customers)

---

## Customer App Quick Commands

```bash
cd customer-app
./setup.sh                           # Initial setup
source .venv/bin/activate            # Activate venv
az login --tenant <tenant-id>        # Login as customer
python register_provider_app.py      # Register provider app
python assign_geocatalog_role.py     # Assign GeoCatalog Administrator role
python assign_users.py --users user@domain.com
python verify_setup.py               # Verify setup
```

**Input Required**: Provider's App ID and Tenant ID

---

## Client App Quick Commands

```bash
cd client-app
source ../.venv/bin/activate         # Or create new venv
python test_geocatalog.py            # Run tests
jupyter notebook test_planetary_computer_geocatalog.ipynb
```

**Works exactly as before!**

---

## Common Azure CLI Commands

```bash
# Login
az login
az login --tenant <tenant-id>

# Check current account
az account show

# List app registrations
az ad app list --display-name "name"

# List service principals
az ad sp list --display-name "name"

# Show app permissions
az ad app permission list --id <app-id>

# Grant admin consent (portal is easier)
# https://portal.azure.com → Enterprise Applications → Permissions
```

---

## File Locations

| What | Where | Purpose |
|------|-------|---------|
| Provider config | `provider-app/.env` | Azure subscription details |
| Customer config | `customer-app/.env` | Provider app details |
| Client config | `client-app/.env` | GeoCatalog credentials |
| Onboarding info | `provider-app/customer_onboarding.json` | Share with customers |
| Registration info | `customer-app/registration_info.json` | Customer setup results |

---

## Environment Variables

### Provider App (.env)
```bash
AZURE_SUBSCRIPTION_ID=xxx
AZURE_TENANT_ID=xxx
PROVIDER_APP_NAME=planetary-computer-provider
```

### Customer App (.env)
```bash
CUSTOMER_TENANT_ID=xxx
PROVIDER_CLIENT_ID=xxx  # From provider
AZURE_SUBSCRIPTION_ID=xxx  # Subscription containing GeoCatalog
GEOCATALOG_RESOURCE_GROUP=xxx
GEOCATALOG_NAME=xxx
```

### Client App (.env)
```bash
AZURE_CLIENT_ID=xxx
AZURE_TENANT_ID=xxx
AZURE_CLIENT_SECRET=xxx
GEOCATALOG_URL=https://...
```

---

## Troubleshooting

### Provider App
```bash
# Check if app exists
az ad app list --display-name "planetary-computer-provider"

# View app details
az ad app show --id <app-id>

# List service principals
az ad sp list --filter "appId eq '<app-id>'"
```

### Customer App
```bash
# Verify correct tenant
az account show | grep tenantId

# Check if SP exists
az ad sp list --filter "appId eq '<provider-app-id>'"

# View permissions
python verify_setup.py
```

### Client App
```bash
# Test authentication
python test_oauth2_token.py

# Verify GeoCatalog access
python test_geocatalog.py
```

---

## Next Steps Guide

1. **Understanding Architecture?** → Read `ARCHITECTURE.md`
1. **Need Provider Setup?** → Follow `provider-app/README.md`
1. **Need Customer Setup?** → Follow `customer-app/README.md`

---

## Documentation Index

| File | Content |
|------|---------|
| `README.md` | Repository overview |
| `ARCHITECTURE.md` | Multi-tenant architecture diagrams |
| `provider-app/README.md` | Provider app documentation |
| `customer-app/README.md` | Customer app documentation |
| `client-app/README.md` | Original client documentation |
