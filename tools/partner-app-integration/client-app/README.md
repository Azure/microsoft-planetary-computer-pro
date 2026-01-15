# Azure Planetary Computer GeoCatalog Testing Application

This repository contains a test application for interacting with Azure Planetary Computer Pro GeoCatalog operations using multiple authentication methods.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [Authentication Methods](#authentication-methods)
- [Understanding Client Types](#understanding-client-types)
- [Azure App Registration Setup](#azure-app-registration-setup)
- [Configuration Guide](#configuration-guide)
- [Running the Application](#running-the-application)
- [Token Caching](#token-caching)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Testing Summary](#testing-summary)
- [Security Best Practices](#security-best-practices)
- [Dependencies](#dependencies)

---

## Overview

The application demonstrates how to:
- Authenticate with Azure using multiple methods:
  - Service Principal (Client Secret)
  - Device Code Flow (azure.identity)
  - MSAL Device Code Flow (on-behalf-of-user)
  - MSAL Interactive Browser (on-behalf-of-user)
- Connect to a Microsoft Planetary Computer Pro GeoCatalog
- Perform basic STAC API operations (GET requests)
- List collections and search for items
- Retrieve API conformance information

---

## Quick Start

### TL;DR - Get Running in 5 Minutes

**Your app is a confidential client (requires secret).**

- ✅ **App-only auth works now** (Option 1 - currently active)
- 🔧 **User auth needs Azure Portal change** (Options 3 & 4 - enable "Allow public client flows")

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure your .env file (see Configuration Guide below)

# 4. Run the script
python test_geocatalog.py
# ✅ Working! Using app-only authentication
```

**Need user authentication?** See [Enable User Authentication](#enable-user-authentication) below.

---

## Prerequisites

1. **Azure Account**: An active Azure subscription
2. **Service Principal or App Registration**: A registered Azure AD application with:
   - Client ID (Of the external application)
   - Tenant ID (Of the destination GeoCatalot resource)
   - Client Secret (for app-only authentication)
3. **GeoCatalog Access**: Access to a Planetary Computer Pro GeoCatalog resource
4. **Python**: Python 3.10 or higher

---

## Setup Instructions

### 1. Create Python Virtual Environment

```bash
cd client-app
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 1. Configure Environment Variables

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your Azure credentials:

```env
# Azure Service Principal Credentials
AZURE_CLIENT_ID=your-client-id-here
AZURE_TENANT_ID=your-customers-tenant-id-here
AZURE_CLIENT_SECRET=your-client-secret-here

# GeoCatalog Configuration
GEOCATALOG_URL=https://your-geocatalog.geocatalog.spatio.azure.com
```

**Important**: Never commit the `.env` file to version control! It's already in `.gitignore`.

---

## Authentication Methods

This application supports **four authentication methods**:

### Method 1: Client Secret (Service Principal) ✅ Working Now

**Use when**: Your app needs to run unattended or as a service.

```python
credential = authenticate_client_secret(config)
```

**Requirements**:
- Service Principal with client secret
- No user interaction required

**Flow**:
```
Application → Azure AD → Access Token → GeoCatalog API
```

**Advantages**:
- Fully automated
- No user interaction needed
- Perfect for scripts and services

---

### Method 2: Device Code Flow (azure.identity)

**Use when**: Simple user authentication is needed. This requires that your user identity has access in the destination (customer) tenant, and has GeoCatalog roles assigned to your identity.

```python
credential = authenticate_device_code(config)
```

**Flow**:
1. Displays a code and URL
2. User navigates to URL in browser
3. Enters code and authenticates
4. Token is returned

**Requirements**:
- Enable "Allow public client flows" in Azure Portal

---

## Running the Application

### Using the Python Script

```bash
# Activate virtual environment
source .venv/bin/activate

# Run with default authentication (Method 1 - Client Secret)
python test_geocatalog.py
```

### Using the Jupyter Notebook

```bash
# Open in Jupyter
jupyter notebook test_planetary_computer_geocatalog.ipynb

# Or open in VS Code with Jupyter extension
```

The notebook is organized into the following sections:

1. **Install Required Packages**: Ensures all dependencies are available
2. **Import Libraries and Load Configuration**: Loads credentials from `.env`
3. **Authenticate with Azure Client Secret**: Obtains an access token
4. **Test STAC API - Get Landing Page**: Verifies API connectivity
5. **List All Collections**: Retrieves all STAC collections
6. **Get Specific Collection Details**: Fetches details for a single collection
7. **Search for Items**: Searches for STAC items across collections
8. **Get API Conformance Classes**: Lists supported STAC API features
9. **Summary**: Recap and next steps

### Switching Authentication Methods

Edit `test_geocatalog.py` and change the authentication method:

```python
# Method 1: Client Secret (Default - Working)
credential = authenticate_client_secret(config)

# Method 2: Device Code Flow (requires public client flows enabled)
# credential = authenticate_device_code(config)
```

---

## API Reference

- **Azure Planetary Computer Docs**: https://learn.microsoft.com/en-us/azure/planetary-computer/
- **STAC API Reference**: https://learn.microsoft.com/en-us/rest/api/planetarycomputer/
- **API Version**: `2025-04-30-preview`

### API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/stac` | GET | STAC API landing page |
| `/stac/conformance` | GET | API conformance classes |
| `/stac/collections` | GET | List all collections |
| `/stac/collections/{id}` | GET | Get specific collection |
| `/stac/search` | POST | Search for items |

### Next Steps

After validating basic GET operations, you can extend the application to:

- **Create Collections**: POST to `/stac/collections`
- **Add Items**: POST to `/stac/collections/{collection_id}/items`
- **Configure Ingestion Sources**: Set up automated data ingestion
- **Generate SAS Tokens**: Create secure access tokens for assets
- **Explore Data Visualization**: Use the tiling and visualization APIs

---

## Troubleshooting

### Common Authentication Errors

#### Error: `AADSTS7000218: requires 'client_assertion' or 'client_secret'`

**Meaning:** Your app is a confidential client  
**Fix:** Enable "Allow public client flows" in Azure Portal  
**Why:** Command-line apps need public client mode for user auth

**Steps:**
1. Go to Azure Portal → App Registrations → Your App → Authentication
2. Set "Allow public client flows" to "Yes"
3. Save and try again

---

#### Error: "AADSTS700016: Application not found in directory"

**Solution**: Ensure the `AZURE_CLIENT_ID` in `.env` matches your App Registration's Application ID.

---

#### Error: "AADSTS65001: The user or administrator has not consented"

**Solution**: 
1. Grant admin consent in Azure Portal
2. Or have user consent during first login

---

#### Error: "public_client_application.py: Browser-based authentication is not supported"

**Solution**: 
- Ensure app is configured as Public Client
- Enable "Allow public client flows" in Authentication settings

---

### Common Application Errors

#### "Missing required environment variables"

- Check that `.env` file exists
- Verify all variables are set correctly
- Ensure no extra spaces in variable values

---

#### "Authentication failed"

- Verify credentials are correct in `.env`
- Check that Service Principal exists and is active
- Ensure Service Principal has access to the GeoCatalog
- Verify network connectivity to Azure

---

#### HTTP 404 Errors

- Ensure the GeoCatalog URL is correct
- Remove trailing slash from URL if present
- Verify the API version parameter is included: `api-version=2025-04-30-preview`

---

#### HTTP 403 Forbidden

- Service Principal lacks required permissions
- Add appropriate role assignment to the GeoCatalog resource

---

#### Token Expiration

Tokens typically expire after 1 hour. Re-run the authentication cell to obtain a new token.

---

#### Token cached but getting errors

**Solution**: Clear the cache and re-authenticate:
```bash
# Remove cached credentials (Linux/macOS)
rm -rf ~/.msal_token_cache.bin

# Then re-run
python test_geocatalog.py
```

---

#### Device code flow not working in SSH session

**Solution**: This is expected. Device code flow is designed for this:
1. Code displays in SSH session
2. Open browser on local machine
3. Navigate to URL and enter code
4. Authentication succeeds in SSH session

---

#### 400 Bad Request: "Expecting Value"

**Note:** This is an API-level issue, not an authentication issue. If you see this error:
- Authentication is actually working (would be 401/403 if not)
- Check API version, request format
- Verify service configuration

---

## Testing Summary

### ✅ SUCCESS: App-Only Authentication (Method 1)

**Status:** ✅ **WORKING**

```
✓ Authentication successful!
  Token obtained at: 2025-11-06 22:19:56
  Token expires at: 2025-11-06 23:19:55
```

**Use this when:**
- The app needs to access resources using its own identity
- No user context is required
- Daemon/service scenarios

---

### 🔧 User Authentication (Methods 2-4)

**Status:** 🔧 **Requires Azure Portal Configuration**

**What's needed:**
- Enable "Allow public client flows" in Azure Portal
- Configure redirect URIs (for interactive flow)
- Grant user permissions

**After configuration:**
- Methods 2-4 will work perfectly
- Token caching will reduce authentication prompts
- User context will be available

---

### Test Results Summary

| Method | Auth Type | Client Type | Status | Action Required |
|--------|-----------|-------------|--------|-----------------|
| 1 | App-Only | Confidential | ✅ Working | None - already configured |
| 2 | User (azure.identity) | Public | 🔧 Needs config | Enable public client flows |
| 3 | User (MSAL Device Code) | Public | 🔧 Needs config | Enable public client flows |
| 4 | User (MSAL Interactive) | Public | 🔧 Needs config | Enable public client flows |

**Current Default:** Method 1 (working)  

---

## Security Best Practices

1. **Never commit credentials**: Always use `.env` files (excluded in `.gitignore`)
2. **Rotate secrets regularly**: Client secrets should be rotated periodically
3. **Use least privilege**: Grant only necessary permissions
4. **Monitor token usage**: Review sign-in logs in Azure Portal
5. **Secure token cache**: Ensure file permissions protect cached tokens
6. **Store secrets securely**: Use Azure Key Vault in production
7. **Monitor access logs**: Review for suspicious activity

---

## Additional Resources

- [MSAL Python Documentation](https://msal-python.readthedocs.io/)
- [Azure Identity Documentation](https://learn.microsoft.com/en-us/python/api/overview/azure/identity-readme)
- [Microsoft Identity Platform](https://learn.microsoft.com/en-us/azure/active-directory/develop/)
- [Public Client vs Confidential Client](https://learn.microsoft.com/en-us/azure/active-directory/develop/msal-client-applications)
- [Azure Planetary Computer Documentation](https://learn.microsoft.com/en-us/azure/planetary-computer/)
- [STAC Specification](https://stacspec.org/)
- [Python Requests Documentation](https://requests.readthedocs.io/)

