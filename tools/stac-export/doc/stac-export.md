# STAC Export CLI User Manual

The **STAC Export** CLI tool allows users to export existing SpatioTemporal Asset Catalogs (STAC) as *offline catalogs*. This manual provides instructions on installing and using the tool.

> **NOTE:** The current version of the tool only supports exporting STAC catalogs from a **PgSTAC** database.

## Installation

### Prerequisites

- Python 3.x installed on your system.
- Pip package manager installed.

### Installation Steps

1. Clone the repository from GitHub:

```bash
git clone https://github.com/Azure/spatio-private-preview-docs.git
```

2. Navigate to the directory containing the cloned repository:

```bash
cd spatio-private-preview-docs/tools/stac-export
```

3. Create and activate a virtual environment (not mandatory, but recommended):

```bash
# linux/macOS
python -m venv .venv
source .venv/bin/activate
```

```powershell
# Windows
python -m venv .venv
.venv\Scripts\Activate
```

4. Install the tool using pip:

```bash
pip install .
```

## Usage

To access the tool's help, run the following command:

```bash
stac-export --help
```

### List Collections

To list all collections in a PgSTAC database, run the following command:

```bash
stac-export pgstac list collections --host "HOSTNAME" --username "USERNAME"
```

Replace `HOSTNAME` and `USERNAME` with the appropriate values. The command will prompt you to enter the password for the specified user.

The command accepts the following options:

| Option | Description | Default Value |
| ------ | ----------- | ------------- |
| `--host` | The hostname of the database server. | `localhost` |
| `--port` | The port number of the database server. | `5432` |
| `--username` | The username to connect to the PgSTAC database. | `postgres` |
| `--password` | The password to connect to the PgSTAC database. ||
| `--database` | The name of the PgSTAC database to connect to. | `postgres` |
| `--limit` | The maximum number of collections to list. `-1` lists all the collections. | `-1` |
| `--help` | Show this message and exit. ||

### List Items

To list all items in a collection, run the following command:

```bash
stac-export pgstac list items --host "HOSTNAME" --username "USERNAME" --collection "COLLECTION_ID"
```

Replace `HOSTNAME`, `USERNAME`, and `COLLECTION_ID` with the appropriate values. The command will prompt you to enter the password for the specified user.

The command accepts the following options:

| Option | Description | Default Value |
| ------ | ----------- | ------------- |
| `--host` | The hostname of the database server. | `localhost` |
| `--port` | The port number of the database server. | `5432` |
| `--username` | The username to connect to the PgSTAC database. | `postgres` |
| `--password` | The password to connect to the PgSTAC database. ||
| `--database` | The name of the PgSTAC database to connect to. | `postgres` |
| `--collection` | The ID of the collection to list items from. ||
| `--limit` | The maximum number of items to list. `-1` lists all the items. | `-1` |
| `--help` | Show this message and exit. ||

### Export Collection

To export a STAC collection from a PgSTAC database to a designated directory, run the following command:

```bash
stac-export pgstac export --host "HOSTNAME" --username "USERNAME" --collection "COLLECTION_ID" --output "OUTPUT_DIR"
```

Replace `HOSTNAME`, `USERNAME`, `COLLECTION_ID`, and `OUTPUT_DIR` with the appropriate values. The command will prompt you to enter the password for the specified user.

The command accepts the following options:

| Option | Description | Default Value |
| ------ | ----------- | ------------- |
| `--host` | The hostname of the database server. | `localhost` |
| `--port` | The port number of the database server. | `5432` |
| `--username` | The username to connect to the PgSTAC database. | `postgres` |
| `--password` | The password to connect to the PgSTAC database. ||
| `--database` | The name of the PgSTAC database to connect to. | `postgres` |
| `--collection` | The ID of the collection to export. ||
| `--limit` | The maximum number of items to export. `-1` exports the whole collection. | `-1` |
| `--output` | The directory to export the collection to. ||
| `--batch-size` | The number of items to export in each batch. | `1000` |
| `--validate / --no-validate` | Validate each items before exporting. | `--no-validate` |
| `--max-items-per-collection` | The maximum number of items per collection. If the number of items is greater than this value, the items will be split into multiple collections. | `500000` |
| `--help` | Show this message and exit. ||

The command will create a directory with the collection ID in the specified output directory and export the collection as an *offline STAC collection*. It will create the following artifacts:

- One or more JSON files containing the collection with all its linked items. The files will be named as the collection id and a sequential number as suffix. E.g., `sentinel-2-l2a_1.json`, `sentinel-2-l2a_2.json`.
- A text file containing the list of asset's URLs. The file will be named as the collection id plus the `-assets.txt` suffix. E.g., `sentinel-2-l2a-assets.txt`.

#### Further Steps

Once you have exported the collection, it can be used used in a **Spatio** bulk import. Currently, *Spatio* only supports importing offline collections from *Azure Storage Accounts* or public URLs.

If you want also to export the asset files to an Azure Storage Account, you can use AzCopy. AzCopy is a command-line utility that you can use to copy blobs or files to or from a storage account. You can get more information about AzCopy [here](https://learn.microsoft.com/azure/storage/common/storage-use-azcopy-v10). AzCopy have an undocumented feature that allows you to use a file to specify the list of files to transfer (more information [here](https://github.com/Azure/azure-storage-azcopy/wiki/Listing-specific-files-to-transfer)). You can use the asset's URLs file to transfer the assets to an Azure Storage Account.

Let's say you have exported the assets URLs to a file named `naip-assets.txt`:

```text
https://naipeuwest.blob.core.windows.net/naip/v002/pr/2022/pr_030cm_2022/18065/51/m_1806551_nw_20_030_20221212_20230329.tif
https://naipeuwest.blob.core.windows.net/naip/v002/pr/2022/pr_030cm_2022/18065/50/m_1806550_ne_20_030_20221212_20230329.tif
https://naipeuwest.blob.core.windows.net/naip/v002/pr/2022/pr_030cm_2022/18065/44/m_1806544_nw_20_030_20221212_20230329.tif
https://naipeuwest.blob.core.windows.net/naip/v002/pr/2022/pr_030cm_2022/18066/61/m_1806661_ne_19_030_20221127_20230329.tif
https://naipeuwest.blob.core.windows.net/naip/v002/pr/2022/pr_030cm_2022/18066/56/m_1806656_sw_19_030_20221127_20230329.tif
```

In this case, all assets are stored in the `naipeuwest`storage account, in the `naip` container. We need to modify the file to contain only the assets paths relative to the container. In Linux, you can use the following command in the `stac-export` output directory:

```bash
ASSETS_FILE="naip-assets.txt"
ASSETS_RELATIVE_FILE="naip-assets-relative.txt"
STORAGE_ACCOUNT="naipeuwest"
STORAGE_CONTAINER="naip"
cat $ASSETS_FILE | sed "s/https:\/\/$STORAGE_ACCOUNT.blob.core.windows.net\/$STORAGE_CONTAINER\///g" > $ASSETS_RELATIVE_FILE
```

> More information about the `sed` command can be found [here](https://www.gnu.org/software/sed/manual/sed.html).

The `naip-assets-relative.txt` file will contain the following:

```text
v002/pr/2022/pr_030cm_2022/18065/51/m_1806551_nw_20_030_20221212_20230329.tif
v002/pr/2022/pr_030cm_2022/18065/50/m_1806550_ne_20_030_20221212_20230329.tif
v002/pr/2022/pr_030cm_2022/18065/44/m_1806544_nw_20_030_20221212_20230329.tif
v002/pr/2022/pr_030cm_2022/18066/61/m_1806661_ne_19_030_20221127_20230329.tif
v002/pr/2022/pr_030cm_2022/18066/56/m_1806656_sw_19_030_20221127_20230329.tif
```

To transfer the assets to the `naip` container in the `naipeunorth` storage account, in Linux you can use the following commands in the `stac-export` output directory:

```bash
ORIGIN_ACCOUNT="naipeuwest"
ORIGIN_CONTAINER="naip"
DESTINATION_ACCOUNT="naipeunorth"
DESTINATION_CONTAINER="naip"
ASSETS_RELATIVE_FILE="naip-assets-relative.txt"

# Login to the Azure CLI
az login

# Transfer the assets using your az credentials
# Ensure you have enough privileges to read from the origin storage account and write to the destination storage account
AZCOPY_AUTO_LOGIN_TYPE="AZCLI" azcopy copy "https://$ORIGIN_ACCOUNT.blob.core.windows.net/$ORIGIN_CONTAINER" "https://$DESTINATION_ACCOUNT.blob.core.windows.net/$DESTINATION_CONTAINER" --list-of-files $ASSETS_RELATIVE_FILE
```

To update the STAC items assets URLs to point to the new location, you can execute the following command:

```bash
find items/ -name '*.json' -exec sed -i "s/https:\/\/$ORIGIN_ACCOUNT.blob.core.windows.net\/$ORIGIN_CONTAINER\//https:\/\/$DESTINATION_ACCOUNT.blob.core.windows.net\/$DESTINATION_CONTAINER\//g" {} \;
```

The last step is to upload the collection and the updated items to an Azure Storage Account. In Linux, you can use the following commands in the `stac-export` output directory:

```bash
COLLECTION_ID="naip"
STORAGE_ACCOUNT="naipeunorth"
STORAGE_CONTAINER="naip"

# Login to the Azure CLI
az login

# Transfer the collection and the items using your az credentials
# Ensure you have enough privileges to write to the storage account
AZCOPY_AUTO_LOGIN_TYPE="AZCLI" azcopy copy "$COLLECTION_ID.json" "https://$STORAGE_ACCOUNT.blob.core.windows.net/$STORAGE_CONTAINER"
AZCOPY_AUTO_LOGIN_TYPE="AZCLI" azcopy copy 'items/*.json' "https://$STORAGE_ACCOUNT.blob.core.windows.net/$STORAGE_CONTAINER"

echo "Your collection is now available at https://$STORAGE_ACCOUNT.blob.core.windows.net/$STORAGE_CONTAINER/$COLLECTION_ID.json"
```

Refer to the [Spatio documentation (TBD)] for more information on how to import the collection into a Spatio instance.
