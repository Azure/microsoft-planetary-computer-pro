# Register ArcGIS Enterprise Cloud Data Stores

Register [Microsoft Planetary Computer Pro](https://planetarycomputer.microsoft.com/) STAC collections as [Planetary Computer Pro](https://enterprise.arcgis.com/en/portal/latest/use/add-data-store-item.htm) cloud data stores on [ArcGIS Enterprise](https://enterprise.arcgis.com/) Image Server — enabling direct access to GeoCatalog-managed imagery without SAS tokens.

## What It Does

1. **Discovers** all STAC collections from your MPC Pro GeoCatalog instance
2. **Resolves** the backing Azure storage account and container for each collection
3. **Prompts** you to choose which collections to register (or register all via `--all`)
4. **Creates a service principal** (Entra ID app registration) with GeoCatalog Reader on the GeoCatalog resource — or uses an existing one you provide
5. **Registers** each selected collection as a [Planetary Computer Pro](https://enterprise.arcgis.com/en/portal/latest/use/add-data-store-item.htm) cloud data store on your ArcGIS Enterprise server
6. **Validates** each data store after registration to confirm ArcGIS Server can access the data
7. **Federates** each data store to the ArcGIS Enterprise portal for visibility

Each GeoCatalog collection maps to a single managed storage container. This tool automates the process of registering those collections as Microsoft Planetary Computer Pro data stores so ArcGIS Image Server can read imagery data directly.

## Prerequisites

- Python 3.9+
- Azure CLI (`az`) installed and logged in (`az login`) — required for service principal creation and GeoCatalog access
- An MPC Pro GeoCatalog with at least one collection containing items
- ArcGIS Enterprise with Image Server (admin credentials)
- Permission to create Entra ID app registrations in your tenant (or an existing service principal)

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy and edit the .env file
cp .env.example .env
# Edit .env with your values

# 3. Run (interactive — prompts for collection selection)
python register_cloud_stores.py

# Or using a YAML config file
python register_cloud_stores.py --config config.yaml
```

## Usage

```
python register_cloud_stores.py [OPTIONS]

Options:
  --config, -c PATH          Path to YAML configuration file
  --env, -e PATH             Path to .env file (auto-detected by default)
  --all, -a                  Register all collections without prompting
  --dry-run                  Show what would be registered without making changes
  --list-only                Only list discovered collections
  --skip-service-principal   Skip SP creation, use existing creds from config
  --verbose, -v              Enable debug logging
```

### Examples

```bash
# List what collections are available
python register_cloud_stores.py --list-only

# Dry run — see what would happen (including SP creation plan)
python register_cloud_stores.py --dry-run

# Register everything non-interactively
python register_cloud_stores.py --all

# Use an existing service principal (skip creation)
python register_cloud_stores.py --skip-service-principal

# Use specific config files
python register_cloud_stores.py --config my-config.yaml --env my-secrets.env
```

## Configuration

Configuration can be provided via **YAML file**, **.env file**, or **environment variables**. The YAML file supports `${ENV_VAR}` substitution, so you can keep secrets in the environment and reference them from the config.

### Option A: `.env` file

Copy `.env.example` to `.env` and fill in the values:

```env
GEOCATALOG_ENDPOINT=https://my-geocatalog.geocatalog.spatio.azure.com
ARCGIS_PORTAL_URL=https://portal.domain.com/portal
ARCGIS_USERNAME=admin
ARCGIS_PASSWORD=secretpassword
ARCGIS_SERVER_ROLE=IMAGE_SERVER
STORAGE_CREDENTIAL_TYPE=service_principal

# Set to true (default) to auto-create a new service principal,
# or false to use an existing one.
CREATE_SERVICE_PRINCIPAL=true
SP_DISPLAY_NAME=ArcGIS-Server-GeocatalogReader

# Only needed if CREATE_SERVICE_PRINCIPAL=false:
# AZURE_TENANT_ID=00000000-0000-0000-0000-000000000000
# AZURE_CLIENT_ID=00000000-0000-0000-0000-000000000000
# AZURE_CLIENT_SECRET=your-secret
```

### Option B: YAML config file

Copy `config.example.yaml` to `config.yaml`. Secrets can reference env vars:

```yaml
geocatalog:
  endpoint: https://my-geocatalog.geocatalog.spatio.azure.com

arcgis:
  portal_url: https://portal.domain.com/portal
  username: admin
  password: ${ARCGIS_PASSWORD}
  server_role: IMAGE_SERVER

storage_credentials:
  credential_type: service_principal
  create_service_principal: true               # auto-create a new SP
  sp_display_name: ArcGIS-Server-GeocatalogReader
  # Or use an existing SP:
  # create_service_principal: false
  # tenant_id: ${AZURE_TENANT_ID}
  # client_id: ${AZURE_CLIENT_ID}
  # client_secret: ${AZURE_CLIENT_SECRET}
```

### Storage Credential Types

The `storage_credentials` section defines how ArcGIS Server authenticates to the underlying Azure storage **at runtime** (this is separate from the credential used to query the GeoCatalog):

| Type | When to use |
|---|---|
| `service_principal` | Entra ID service principal with `GeoCatalog Reader` role — required for the Planetary Computer Pro data store type |
| `access_key` | Storage account key (simplest, but less secure) |
| `managed_identity` | User-assigned managed identity on the ArcGIS Server VM |
| `sas_token` | Shared access signature (time-limited) |

## How It Works

```
┌───────────────┐    list_collections()    ┌───────────────────────────┐
│  MPC Pro       │ ◄────────────────────── │  This Tool                 │
│  GeoCatalog    │ ──────────────────────► │                             │
│                │    collections + items   │  1. Discover collections    │
└───────────────┘                          │  2. Prompt user             │
                                           │  3. Create/use SP           │
┌───────────────┐    az ad sp create       │  4. Assign GeoCatalog       │
│  Entra ID      │ ◄────────────────────── │     Reader role             │
│  (Azure AD)    │ ──────────────────────► │  5. Register as Planetary   │
│                │    client_id + secret    │     Computer Pro stores     │
└───────────────┘                          │  6. Validate each store     │
                                           │  7. Federate to portal      │
                                           └──────────┬──────────────────┘
                                                      │
┌───────────────┐    ds.add() + federate              │
│  ArcGIS        │ ◄──────────────────────────────────┘
│  Image Server  │ ──► REST validateDataItem per store
└───────────────┘
```

### Service Principal Management

By default (when `credential_type` is `service_principal`), the tool:

1. Creates a new Entra ID app registration ("ArcGIS-Server-GeocatalogReader")
2. Generates a client secret (valid 2 years)
3. Assigns **GeoCatalog Reader** on the GeoCatalog resource
4. Uses the new credentials for the data store connection strings

**To use an existing service principal instead**, either:
- Set `CREATE_SERVICE_PRINCIPAL=false` and provide `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` / `AZURE_TENANT_ID` in your `.env`
- Or pass `--skip-service-principal` on the command line

The tool will still offer to assign the GeoCatalog Reader role for an existing SP.

### Data Store Validation

After each data store is registered, the tool validates the connection via the ArcGIS Server REST `validateDataItem` endpoint to confirm that ArcGIS Server can access the data through the Planetary Computer Pro data store. Validation results are shown in the results table:

- **passed** — ArcGIS Server confirmed it can read from the data store
- **failed** — connection error (check credentials, network access, firewall rules)

### Storage Discovery

For each collection, the tool resolves the backing storage account and container by:

1. Checking for `msft:storage_account` and `msft:container` extension properties on the collection (set by some GeoCatalog configurations)
2. Falling back to querying one STAC item and parsing the asset `href` URL (pattern: `https://<account>.blob.core.windows.net/<container>/...`)

### Data Store Naming

Each Planetary Computer Pro data store is named after the collection ID with hyphens replaced by underscores (e.g., `sentinel-2-l2a` → `sentinel_2_l2a`).

## Project Structure

```
register-arcgis-enterprise/
├── register_cloud_stores.py   # CLI entry point
├── requirements.txt
├── .env.example               # Environment variable template
├── config.example.yaml        # YAML config template
├── README.md
└── src/
    ├── __init__.py
    ├── config.py              # Configuration loading (.env / YAML / env vars)
    ├── discovery.py           # MPC Pro collection + storage discovery
    ├── registration.py        # ArcGIS Enterprise Planetary Computer Pro data store registration + validation
    ├── service_principal.py   # Entra ID service principal create / role assignment
    └── cli.py                 # Interactive prompts, SP step, formatted output
```

## Troubleshooting

### "No collections found"

- Verify the GeoCatalog endpoint is correct and accessible
- Ensure `az login` or another credential provider is configured for `DefaultAzureCredential`
- Check your account has read access to the GeoCatalog

### "Could not determine storage for collection"

- The collection may not have any ingested items yet — storage info is discovered from item asset hrefs
- You can still register the data store manually through the ArcGIS Enterprise portal using the Planetary Computer Pro service type

### "Failed to register data store"

- Verify the ArcGIS admin credentials have data store registration privileges
- Check that the ArcGIS Server can reach the storage endpoint (`https://<account>.blob.core.windows.net`)
- If the data store already exists under a different name, use `--list-only` with `--verbose` to debug

### Data store validation failed

- Verify the service principal has **GeoCatalog Reader** on the GeoCatalog resource
- Ensure the ArcGIS Server machines can reach `*.blob.core.windows.net` on port 443
- If using a service principal, confirm the tenant_id, client_id, and client_secret are correct
- Check that the storage container actually exists and contains data

### Service principal creation failed

- Ensure you're logged into the Azure CLI (`az login`) with a user that can create app registrations
- If your tenant restricts app registration, ask your admin to create one and provide the credentials via config
- Use `--skip-service-principal` to bypass creation and provide existing credentials

### SSL certificate errors

Set `ARCGIS_VERIFY_CERT=false` in your `.env` (or `verify_cert: false` in YAML) for self-signed certificates. **Not recommended for production.**
