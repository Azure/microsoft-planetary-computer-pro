# Customer Application - Tenant Registration

This component handles the customer-side registration and configuration of the provider's enterprise application in the customer's Azure AD tenant.

## 🎯 Purpose

The customer app is responsible for:
- Registering the provider's multi-tenant app in the customer tenant
- Granting admin consent for required permissions
- Assigning users/groups to the application
- Configuring customer-specific access controls
- Managing the service principal in the customer tenant

## 📋 Prerequisites

- Access to customer's Azure AD tenant
- Global Administrator or Application Administrator role
- Azure CLI installed (`az --version` to verify)
- Python 3.10+
- Provider application details (client ID, tenant ID)

## 🚀 Setup Instructions

### 1. Install Dependencies

```bash
cd customer-app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with the provider app details you received:

```env
# Customer tenant details
CUSTOMER_TENANT_ID=your-customer-tenant-id

# Provider app details (received from provider)
PROVIDER_CLIENT_ID=provider-app-client-id
PROVIDER_REDIRECT_URI=https://localhost:8080/callback
```

### 3. Run Customer Registration

```bash
python register_provider_app.py
```

This will:
1. Create the service principal in your tenant
2. Request admin consent for permissions
3. Display consent URL for admin approval
4. Configure initial role assignments

## 📁 Files

- `register_provider_app.py` - Main registration script
- `assign_users.py` - User/group assignment management
- `assign_geocatalog_role.py` - **NEW**: Assign GeoCatalog Administrator role
- `verify_setup.py` - Setup verification script
- `requirements.txt` - Python dependencies
- `.env` - Configuration (not committed to git)

## 🔧 Key Operations

### 1. Register Provider App

```bash
python register_provider_app.py
```

Creates the enterprise application (service principal) in your tenant.

### 2. Assign GeoCatalog Administrator Role

```bash
python assign_geocatalog_role.py
```

Grants the provider app access to your GeoCatalog resource with the "GeoCatalog Administrator" role.

**Prerequisites:**
- Service principal registered (step 1 complete)
- GeoCatalog resource exists in your subscription
- You have Owner or User Access Administrator role on the GeoCatalog

**Configuration** (in `.env`):
```env
AZURE_SUBSCRIPTION_ID=your-subscription-id
GEOCATALOG_RESOURCE_GROUP=your-resource-group
GEOCATALOG_NAME=your-geocatalog-name
```

The script will automatically build the full resource ID from these components.

### 3. Grant Admin Consent

```bash
python register_provider_app.py
```

Opens a browser for admin to consent to the requested permissions (included in step 1).


## 🔐 Permissions Required

The provider app typically requests:

### Application Permissions (Admin Consent Required)
- Access to GeoCatalog resources
- Read organizational data (if applicable)

### Delegated Permissions (User Consent)
- Sign in and read user profile
- Access resources on behalf of the user

## 📊 Admin Consent Flow

1. Run the registration script
2. Copy the admin consent URL provided
3. Share with Global Administrator
4. Admin approves the permissions
5. Application becomes available to users

### Example Consent URL
```
https://login.microsoftonline.com/{customer-tenant-id}/adminconsent?
  client_id={provider-client-id}
  &redirect_uri=https://localhost
```

## 🛡️ Security Considerations

- **Review permissions carefully** before granting admin consent
- **Limit user assignments** to only those who need access
- **Enable MFA** for users accessing the application
- **Monitor sign-in logs** for unusual activity
- **Review permissions quarterly** to ensure they're still necessary

## 🔍 Verification

After registration, verify the setup:

```bash
# Check if service principal exists
az ad sp list --display-name "Planetary Computer Provider" --output table

# View assigned users
az ad sp show --id {service-principal-id} --query "appRoles"

# Check consent status
python verify_setup.py
```

## 📋 Compliance

Ensure you have documented:
- Why this application is needed
- Who approved the registration
- What data the application can access
- Review date for permissions

## 🐛 Troubleshooting

### Admin Consent Fails
- Ensure you have Global Administrator role
- Check if application is blocked by conditional access
- Verify provider app is configured for multi-tenancy

### Users Can't Access
- Verify user assignment in Azure Portal
- Check if "User assignment required" is enabled
- Ensure users have appropriate licenses

### Service Principal Not Found
- Re-run registration script
- Check provider client ID is correct
- Verify tenant ID matches your customer tenant

## 📚 Additional Resources

- [Enterprise Application Management](https://learn.microsoft.com/en-us/azure/active-directory/manage-apps/what-is-application-management)
- [Admin Consent Workflow](https://learn.microsoft.com/en-us/azure/active-directory/manage-apps/configure-admin-consent-workflow)
- [User Assignment](https://learn.microsoft.com/en-us/azure/active-directory/manage-apps/assign-user-or-group-access-portal)

## 📞 Support

For issues with customer-side registration:
1. Check the troubleshooting section above
2. Review Azure AD sign-in logs
3. Contact your provider for application-specific issues
