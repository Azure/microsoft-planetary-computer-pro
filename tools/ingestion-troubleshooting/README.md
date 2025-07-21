# STAC Item Ingestion Troubleshooter for Microsoft Planetary Computer Pro

This script helps you troubleshoot STAC item ingestion issues in Microsoft Planetary Computer Pro. Follow the progressive test framework below to systematically validate your ingestion pipeline.

## Quick Setup

**Prerequisites**:
- Python 3.8+ with required libraries: `pip install requests azure-identity azure-storage-blob azure-core`
- Azure CLI: `az login` (must be logged into the correct Azure subscription)

**Required Permissions**:
- **GeoCatalog Administrator** role on your GeoCatalog resource
- **Storage Blob Data Contributor** role on your Azure Storage account

---

## Progressive Testing Framework

Run these tests in order to isolate and diagnose issues. Each test builds on the previous one's success.

### Basic Command Structure

```bash
python stac_ingestion_troubleshooter.py \
    --geocatalog-url <your-geocatalog-url> \
    --storage-account <your-storage-account-name> \
    [additional-test-specific-options]
```

---

## Test 1: Basic Connectivity & Permissions Validation

**Purpose**: Validate that GeoCatalog is working, permissions are correct, and you have access to the storage account.

**What it tests**:
- ✅ Azure authentication setup
- ✅ GeoCatalog API access and permissions  
- ✅ Storage account access and permissions
- ✅ End-to-end ingestion with auto-created resources
- ✅ Automatic cleanup functionality

**Command** (only 2 required arguments):
```bash
python stac_ingestion_troubleshooter.py \
    --geocatalog-url "https://your-geocatalog.geocatalog.spatio.azure.com" \
    --storage-account "yourstorageaccount"
```

**What happens**:
- Creates temporary `troubleshooting-container` and `troubleshooting-collection`
- Generates dummy TXT STAC item with sample data
- Tests complete ingestion pipeline
- Automatically cleans up all test artifacts

**Success indicators**:
- ✓ Authentication successful
- ✓ GeoCatalog API accessible  
- ✓ Storage account accessible
- ✓ Ingestion completed successfully
- ✓ All artifacts cleaned up

---

## Test 2: Storage Container Permissions Validation

**Purpose**: Validate storage container permissions and verify you can work with existing containers.

**What it tests**:
- ✅ Access to specific existing containers
- ✅ Read/write permissions on user containers
- ✅ Data protection (preserves existing container data)
- ✅ Smart ingestion source management

**Command**:
```bash
python stac_ingestion_troubleshooter.py \
    --geocatalog-url "https://your-geocatalog.geocatalog.spatio.azure.com" \
    --storage-account "yourstorageaccount" \
    --container "your-existing-container"
```

**What happens**:
- Validates the specified container exists and is accessible
- Creates dummy STAC item in your existing container
- Tests ingestion pipeline with real container
- **Data Protection**: Only removes dummy files created by the script

**Success indicators**:
- ✓ Container exists and is accessible
- ✓ Can read/write to the container
- ✓ Existing container data preserved during cleanup
- ✓ Smart ingestion source reuse (if applicable)

---

## Test 3: Existing STAC Item Validation

**Purpose**: Test ingestion of your actual STAC items to validate they work correctly.

**What it tests**:
- ✅ Your actual STAC item structure and format
- ✅ Asset accessibility and URL handling
- ✅ Collection compatibility
- ✅ Real-world ingestion scenarios

**Command**:
```bash
python stac_ingestion_troubleshooter.py \
    --geocatalog-url "https://your-geocatalog.geocatalog.spatio.azure.com" \
    --storage-account "yourstorageaccount" \
    --container "your-container-with-stac-items" \
    --collection-id "your-target-collection" \
    --blob "path/to/your-stac-item.json"
```

**What happens**:
- Reads and validates your existing STAC item
- Processes asset URLs and collection links
- Tests ingestion with your real data
- Preserves all your existing data

**Success indicators**:
- ✓ STAC item read and validated successfully
- ✓ All required STAC fields present
- ✓ Assets accessible and properly formatted
- ✓ Item successfully ingested into target collection

**Optional: Preserve for inspection**:
```bash
# Add --keep-artifacts to preserve the ingested item for manual verification
python stac_ingestion_troubleshooter.py \
    --geocatalog-url "https://your-geocatalog.geocatalog.spatio.azure.com" \
    --storage-account "yourstorageaccount" \
    --container "your-container-with-stac-items" \
    --collection-id "your-target-collection" \
    --blob "path/to/your-stac-item.json" \
    --keep-artifacts
```

---

## Additional Diagnostic Tests

Once basic connectivity is working, use these tests to diagnose specific ingestion issues:

### Test 4: URL Format Troubleshooting

**Purpose**: Compare relative vs absolute URL handling to diagnose link-related failures.

```bash
# Test with relative URLs (may cause GenericIngestionError)
python stac_ingestion_troubleshooter.py \
    --geocatalog-url "https://your-geocatalog.geocatalog.spatio.azure.com" \
    --storage-account "yourstorageaccount" \
    --use-relative-links
```

### Test 5: Image Asset Troubleshooting  

**Purpose**: Test JPG assets and role compatibility to diagnose image processing issues.

```bash
# Test JPG with recommended thumbnail role
python stac_ingestion_troubleshooter.py \
    --geocatalog-url "https://your-geocatalog.geocatalog.spatio.azure.com" \
    --storage-account "yourstorageaccount" \
    --asset-type jpg

# Test JPG with data role (may cause transformation errors)
python stac_ingestion_troubleshooter.py \
    --geocatalog-url "https://your-geocatalog.geocatalog.spatio.azure.com" \
    --storage-account "yourstorageaccount" \
    --asset-type jpg \
    --asset-role data
```

### Test 6: Timeout & Performance Testing

**Purpose**: Test with extended timeouts for large or complex STAC items.

```bash
python stac_ingestion_troubleshooter.py \
    --geocatalog-url "https://your-geocatalog.geocatalog.spatio.azure.com" \
    --storage-account "yourstorageaccount" \
    --container "your-container" \
    --blob "large-stac-item.json" \
    --timeout 900
```

### Test 7: Manual Inspection Mode

**Purpose**: Preserve all artifacts for detailed manual inspection and troubleshooting.

```bash
python stac_ingestion_troubleshooter.py \
    --geocatalog-url "https://your-geocatalog.geocatalog.spatio.azure.com" \
    --storage-account "yourstorageaccount" \
    --keep-artifacts
```

**Artifacts preserved for inspection**:
- 📦 Container: `troubleshooting-container`
- 📚 Collection: `troubleshooting-collection` 
- 📄 STAC item and assets in the GeoCatalog Explorer

---

## Key Features

- **🔍 Comprehensive Validation**: Validates GeoCatalog access, storage account permissions, and resource availability
- **🧠 Intelligent Resource Management**: Smart ingestion source management with SAS token expiry detection and automatic refresh
- **🛡️ Data Protection**: Protects existing user data while providing complete cleanup of test artifacts
- **🚀 Zero-Configuration Testing**: Run complete end-to-end tests with just 2 required arguments
- **📊 Professional Messaging**: Clean, informative output with step-by-step progress and actionable troubleshooting tips
- **⚙️ Flexible Configuration**: Supports various asset types, roles, URL formats, and ingestion scenarios

---

## What the Script Does (Step-by-Step)

When you run the script, it performs the following comprehensive validation and ingestion process:

### 1. **Initial Setup & Variable Definition**
- Validates command-line arguments and sets intelligent defaults
- Displays clear configuration summary showing what will be processed
- Indicates cleanup mode (automatic cleanup vs. artifact preservation)

### 2. **Authentication & Access Validation**
- Sets up Azure authentication (AzureCliCredential with DefaultAzureCredential fallback)
- Validates GeoCatalog access and API connectivity
- Validates storage account access and permissions
- Provides specific troubleshooting tips for authentication failures

### 3. **Resource Management**
- **Container Management**: Creates or validates containers with intelligent behavior
- **Collection Management**: Creates or validates STAC collections automatically
- **Data Protection**: Preserves existing user data while managing test resources

### 4. **SAS Token & Ingestion Source Management** 
- Generates fresh SAS tokens with 24-hour expiry
- **Intelligent Ingestion Source Handling**:
  - Checks for existing ingestion sources for the target container
  - Validates SAS token expiry using official API data (`connectionInfo.expiration`)
  - Only refreshes when tokens expire within 1 hour (smart efficiency)
  - Displays clear status: "✓ Existing SAS token is valid (expires in X hours)"
  - No false warnings for normal resource existence

### 5. **STAC Item Preparation**
- Creates dummy STAC items (if no existing blob specified) with configurable asset types and roles
- Processes existing STAC items with validation and correction
- Ensures proper absolute/relative URL handling based on configuration
- Validates STAC item structure and provides warnings for missing fields

### 6. **Ingestion & Monitoring**
- Submits STAC items for ingestion with comprehensive error handling
- Real-time monitoring of ingestion operations with status updates
- Verification that items were successfully ingested into the collection

### 7. **Intelligent Cleanup**
- **Automatic Mode**: Removes all test artifacts while preserving existing user data
- **Preservation Mode** (`--keep-artifacts`): Keeps all artifacts for manual inspection
- **Data Protection**: Only deletes resources/data created by the script itself

### 8. **Professional Reporting**
- Provides clear success/failure summary
- Offers direct links to view results in GeoCatalog Explorer
- Gives actionable troubleshooting tips for any encountered issues

---

## Arguments Reference

### Required Arguments (Mandatory)
- `--geocatalog-url`: The URL of your GeoCatalog instance (e.g., `https://your-geocatalog.geocatalog.spatio.azure.com`)
- `--storage-account`: The name of your Azure Storage account

### Optional Arguments

#### Resource Configuration
- `--container`: The name of the container within your storage account where STAC items are stored
  - **Default behavior**: If not provided, automatically creates/uses `troubleshooting-container`
  - **User-specified behavior**: If specified, the container must exist (will not be auto-created)
  - **Cleanup behavior**: Auto-created containers are fully deleted; existing containers preserve user data
- `--collection-id`: The ID of the collection you are ingesting items into
  - **Default behavior**: If not provided, automatically creates/uses `troubleshooting-collection`  
  - **Smart creation**: If the specified collection doesn't exist, it will be created automatically
  - **Cleanup behavior**: Auto-created collections are fully deleted; existing collections preserve user items

#### STAC Item Configuration  
- `--blob`: The path to a specific STAC item JSON file within the container
  - **Default behavior**: If not provided, a dummy STAC item will be created automatically
  - **Processing**: Existing STAC items are validated and processed with absolute/relative URL corrections
- `--use-relative-links`: Use relative links in STAC asset hrefs instead of absolute URLs
  - **Default behavior**: False (uses absolute URLs - recommended for production)
  - **Purpose**: Useful for troubleshooting URL-related ingestion issues
- `--asset-type`: Type of asset to create for dummy STAC items
  - **Choices**: `txt`, `jpg`
  - **Default**: `txt` (text file with sample data)
- `--asset-role`: Role of the asset in the STAC item
  - **Choices**: `data`, `thumbnail`
  - **Default behavior**: 
    - `data` role for `txt` assets
    - `thumbnail` role for `jpg` assets
  - **⚠️ Important**: Incorrect role assignments (e.g., `jpg` with `data` role) can cause ingestion failures

#### Operation Configuration
- `--timeout`: Timeout for monitoring ingestion operation
  - **Unit**: Seconds
  - **Default**: 300 seconds (5 minutes)
  - **Purpose**: Adjust for long-running ingestion operations or large STAC items
- `--keep-artifacts`: Keep test artifacts after completion
  - **Default behavior**: False (automatically cleans up all test artifacts)
  - **Purpose**: Preserve containers, collections, and dummy data for manual inspection and troubleshooting
  - **Artifacts preserved**: Auto-created containers, collections, STAC items, and blob data

### Default Script Behavior

When you run the script with only the required arguments:

```bash
python stac_ingestion_troubleshooter.py \
    --geocatalog-url "https://your-geocatalog.geocatalog.spatio.azure.com" \
    --collection-id "your-collection" \
    --storage-account "yourstorageaccount" \
    --container "stac-items"
```

The script will:
1. ✅ Create a dummy STAC item (since no `--blob` specified)
2. ✅ Generate a TXT asset with `data` role (default asset type)
3. ✅ Use absolute URLs for all asset links (recommended)
4. ✅ Monitor ingestion for up to 5 minutes (default timeout)

### Processing and Troubleshooting Features

The script includes several specialized features to help diagnose common ingestion issues:

1. **Asset Type Processing**: Process different file formats (TXT vs JPG) to verify asset processing
2. **Asset Role Validation**: Process different asset roles to ensure compatibility between file types and their intended use
3. **URL Format Processing**: Compare absolute vs relative URL handling to diagnose link-related failures
4. **Comprehensive Error Reporting**: Detailed error codes and messages for production troubleshooting

## Troubleshooting Guide

### Step-by-Step Diagnosis

1. **Start with Test 1** - Basic connectivity validation
2. **If Test 1 fails** - Check authentication and permissions
3. **If Test 1 passes** - Move to Test 2 for container validation  
4. **If Test 2 passes** - Move to Test 3 for real STAC item testing
5. **Use Additional Tests** - For specific error diagnosis

### Common Issues and Solutions

1. **"GenericIngestionError" with relative URLs**: Ensure all asset hrefs use absolute URLs (not relative paths)
2. **"Asset transformation exception" with JPG files**: Verify JPG assets use `thumbnail` role, not `data` role
3. **"Forbidden access" errors**: Check SAS token validity and storage account permissions
4. **Timeout errors**: Increase the `--timeout` value for large or complex STAC items

---

## Interpreting Results

### Success Output Patterns
When tests pass, you'll see clean, professional output like:
```
✓ Authentication using AzureCliCredential successful
✓ GeoCatalog endpoint accessible  
✓ Successfully accessed storage account 'yourstorageaccount'
✓ Found existing ingestion source with ID: 32ec3175-9083-4789-b0f0-151a6048874d
✓ Existing SAS token is valid (expires in 23 hours)
✓ STAC item accepted for ingestion
✓ STAC item ingestion completed successfully!
✓ All artifacts cleaned up successfully!
```

### Common Error Patterns & Solutions

| Error Pattern | Likely Cause | Solution |
|---------------|--------------|----------|
| `❌ ERROR: Authentication failed` | Not logged into Azure CLI | Run `az login` |
| `❌ ERROR: Access denied to storage account` | Missing Storage Blob Data Contributor role | Check RBAC permissions |
| `❌ ERROR: Access denied to GeoCatalog` | Missing GeoCatalog Administrator role | Check GeoCatalog permissions |
| `❌ ERROR: GenericIngestionError` | Relative URLs in assets | Use absolute URLs (avoid `--use-relative-links`) |
| `❌ ERROR: Asset transformation exception` | JPG with `data` role | Use `thumbnail` role for JPG assets |
| `⏰ SAS token expires in X minutes` | Token refresh in progress | Normal behavior - new token being created |

---

For detailed error messages and logs, the script automatically provides comprehensive output including:
- **Step-by-step execution progress** with clear section headers
- **Detailed error codes and messages** with specific failure context
- **Real-time operation status monitoring** with timestamps
- **Actionable troubleshooting tips** based on specific error types encountered
- **Resource status information** (e.g., "✓ Existing SAS token is valid (expires in 23 hours)")
- **Professional messaging** with no redundant step numbering or confusing warnings

---

## Support

If you need further assistance, consider reaching out for support through the following channels:

- **Microsoft Q&A**: For community-based support and to ask questions about Microsoft Planetary Computer.
- **Azure Support**: If you have a support plan with Azure, you can create a support ticket for technical assistance.

When seeking support, provide as much detail as possible about the issue you are facing, including:

- A clear description of the problem.
- The steps you have already taken to troubleshoot.
- Any relevant error messages or codes.
- The complete output of the script including all status messages and error details.

## Data Protection and Cleanup Behavior

The script is designed to safely clean up test artifacts while protecting your existing data:

### Automatic Data Protection

- **Existing Containers**: If you specify a container that already exists, the script will only delete dummy blobs it creates, preserving all other container contents
- **Existing Collections**: If you specify a collection that already exists, the script will only delete dummy STAC items it creates, preserving all other collection items  
- **New Resources**: Only containers and collections created entirely by the script are completely removed during cleanup

### Cleanup Examples

**Scenario 1: Using existing resources**
```bash
# Your container "my-data" and collection "my-collection" already exist
python stac_ingestion_troubleshooter.py \
    --geocatalog-url "https://your-geocatalog.geocatalog.spatio.azure.com" \
    --storage-account "yourstorageaccount" \
    --container "my-data" \
    --collection-id "my-collection"
```
**Result**: Only dummy files and STAC items created by the script are deleted. Your existing container and collection data remain untouched.

**Scenario 2: Auto-creating new resources**
```bash
# Let script create new container and collection
python stac_ingestion_troubleshooter.py \
    --geocatalog-url "https://your-geocatalog.geocatalog.spatio.azure.com" \
    --storage-account "yourstorageaccount"
```
**Result**: The script-created `troubleshooting-container` and `troubleshooting-collection` are completely removed after testing.

### Preserving Test Artifacts

Use `--keep-artifacts` to preserve all test artifacts for manual inspection:

```bash
python stac_ingestion_troubleshooter.py \
    --geocatalog-url "https://your-geocatalog.geocatalog.spatio.azure.com" \
    --storage-account "yourstorageaccount" \
    --keep-artifacts
```

This keeps all created resources (even script-created ones) for troubleshooting purposes.

## Changelog

### Version 2.1 (Current)

- **🧠 Intelligent Ingestion Source Management**: 
  - Smart detection and reuse of existing ingestion sources
  - Automatic SAS token expiry validation using official API (`connectionInfo.expiration`)
  - Only refreshes tokens when they expire within 1 hour (improved efficiency)
  - Professional messaging: "✓ Existing SAS token is valid (expires in X hours)"
- **📊 Enhanced UX and Messaging**:
  - Removed redundant step numbering and confusing validation messages  
  - Eliminated false warnings for normal resource existence
  - Clean, professional output with actionable troubleshooting guidance
- **🛡️ Improved Reliability**:
  - Uses official API fields instead of parsing SAS token strings
  - Robust date/time handling with timezone awareness
  - Enhanced error handling with specific troubleshooting context

### Version 2.0

- **Enhanced Processing Capabilities**: Added comprehensive features for asset types, roles, and URL formats
- **Asset Type Support**: Added support for both TXT and JPG asset types in dummy STAC items
- **Asset Role Validation**: Added configurable asset roles (`data`, `thumbnail`) to test compatibility 
- **URL Format Processing**: Added `--use-relative-links` flag to process relative vs absolute URL handling
- **Timeout Configuration**: Added configurable timeout for monitoring long-running ingestion operations
- **Advanced Error Reporting**: Enhanced error reporting with specific error codes and troubleshooting guidance
- **Production Troubleshooting**: Added systematic framework for diagnosing ingestion regressions

### Version 1.1

- Added detailed troubleshooting information and support resources.
- Improved error handling and debug output.

### Version 1.0

- Initial release of the STAC Item Ingestion Troubleshooter script.
- Supports ingestion of existing STAC items and creation of dummy STAC items.
- Basic authentication and permission checks.