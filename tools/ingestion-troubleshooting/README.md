# STAC Item Ingestion Troubleshooter for Microsoft Planetary Computer Pro

This script is designed to help you troubleshoot the ingestion of STAC (SpatioTemporal Asset Catalog) items into a Microsoft Planetary Computer Pro GeoCatalog collection. It provides a step-by-step process that includes authentication, SAS token generation, ingestion source creation, and monitoring, with detailed feedback at each stage.

## Prerequisites

Before running this script, ensure you have the following installed:

- **Python 3.8+**
- **Required Python libraries**:
  - `requests`: For making HTTP requests to the GeoCatalog API.
  - `azure-identity`: For authenticating with Azure.
  - `azure-storage-blob`: For interacting with Azure Blob Storage.
  - `azure-core`: A core library for Azure SDKs.

You can install these libraries using `pip`:

```bash
pip install requests azure-identity azure-storage-blob azure-core
```

## Authentication

The script uses `AzureCliCredential` for authentication, which requires you to be logged into Azure through the Azure CLI. If you haven't already, install the [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) and log in with the following command:

```bash
az login
```

Ensure that the account you log in with has the necessary permissions to access the GeoCatalog and the specified Azure Storage account.

## Permissions

Ensure the authenticated user has the correct Role-Based Access Control (RBAC) roles assigned for both the GeoCatalog resource and the Azure Storage account.

### GeoCatalog Permissions

To ingest data into a GeoCatalog, the user running the script must have the **GeoCatalog Administrator** role assigned for the target GeoCatalog resource. This role grants the necessary permissions to create and manage STAC items within the catalog.

### Azure Storage Account Permissions

The script needs to read STAC items from your storage account and may need to write new files if creating a dummy item. To perform these actions, the user running the script needs the **Storage Blob Data Contributor** role assigned on the target storage account. This role provides the required permissions to:

- Read and write blob data.
- Generate a user delegation key, which is necessary for creating the SAS token used by the ingestion service.

For more details on assigning roles, see [Manage access for Microsoft Planetary Computer Pro](https://learn.microsoft.com/en-us/azure/planetary-computer/manage-access).

## Usage

You can run the script from your terminal. The basic command structure is as follows:

```bash
python stac_ingestion_troubleshooter.py \
    --geocatalog-url <your-geocatalog-url> \
    --collection-id <your-collection-id> \
    --storage-account <your-storage-account-name> \
    --container <your-container-name> \
    [--blob <path-to-your-stac-item.json>] \
    [--create-dummy]
```

### Examples

**1. Ingesting an Existing STAC Item:**

To ingest a specific STAC item that already exists in your Azure Storage container, use the `--blob` argument:

```bash
python stac_ingestion_troubleshooter.py \
    --geocatalog-url "https://your-geocatalog.geocatalog.spatio.azure.com" \
    --collection-id "your-collection" \
    --storage-account "yourstorageaccount" \
    --container "stac-items" \
    --blob "path/to/your-item.json"
```

**2. Creating and Ingesting a Dummy STAC Item:**

If you want to test the ingestion pipeline without using an existing STAC item, you can use the `--create-dummy` flag. The script will generate a new dummy STAC item and a corresponding asset file in your storage container.

```bash
python stac_ingestion_troubleshooter.py \
    --geocatalog-url "https://your-geocatalog.geocatalog.spatio.azure.com" \
    --collection-id "your-collection" \
    --storage-account "yourstorageaccount" \
    --container "stac-items" \
    --create-dummy
```

If you omit both the `--blob` and `--create-dummy` arguments, the script will automatically create a dummy item for testing.

## Arguments

- `--geocatalog-url`: The URL of your GeoCatalog instance.
- `--collection-id`: The ID of the collection you are ingesting items into.
- `--storage-account`: The name of your Azure Storage account.
- `--container`: The name of the container within your storage account where STAC items are stored.
- `--blob`: (Optional) The path to a specific STAC item JSON file within the container. If not provided, a dummy item will be created.
- `--create-dummy`: (Optional) A flag to indicate that a dummy STAC item should be created. If this flag is set, the `--blob` argument is ignored.

## Troubleshooting

If you encounter issues during the ingestion process, check the following:

- Ensure that all prerequisite software and libraries are correctly installed.
- Verify that you are logged into Azure CLI and the correct subscription is selected.
- Check the permissions of the authenticated user to ensure they have the necessary RBAC roles assigned.
- Review the GeoCatalog and Azure Storage account settings to ensure they are correctly configured.

For detailed error messages and logs, run the script with the `--debug` flag to enable debug output:

```bash
python stac_ingestion_troubleshooter.py --debug \
    --geocatalog-url "https://your-geocatalog.geocatalog.spatio.azure.com" \
    --collection-id "your-collection" \
    --storage-account "yourstorageaccount" \
    --container "stac-items" \
    --blob "path/to/your-item.json"
```

This will provide more detailed information about the requests being made and the responses being received, which can help identify the source of any issues.

## Support

If you need further assistance, consider reaching out for support through the following channels:

- **Microsoft Q&A**: For community-based support and to ask questions about Microsoft Planetary Computer.
- **Azure Support**: If you have a support plan with Azure, you can create a support ticket for technical assistance.

When seeking support, provide as much detail as possible about the issue you are facing, including:

- A clear description of the problem.
- The steps you have already taken to troubleshoot.
- Any relevant error messages or codes.
- The output of the script when run with the `--debug` flag, if applicable.

## Changelog

### Version 1.0

- Initial release of the STAC Item Ingestion Troubleshooter script.
- Supports ingestion of existing STAC items and creation of dummy STAC items.
- Basic authentication and permission checks.

### Version 1.1

- Added detailed troubleshooting information and support resources.
- Improved error handling and debug output.