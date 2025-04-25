# STACForge

## Prepare the Development Environment

To start developing STACForge, you'll need to crate some prerequisites:

* A production Spatio GeoCatalog
* An Azure Storage Account used for development

Open this folder in Visual Studio Code as a Dev Container. Then, add a new file to the `src` folder named `local.setting.json` with the following content:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsFeatureFlags": "EnableWorkerIndexing",
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "AzureFunctionsJobHost__logging__logLevel__Function": "Debug",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "GEOCATALOG_URL": "<url of a productions geocatalog>",
    "LOGS_STORAGE_ACCOUNT": "<development storage account>",
    "LOGS_TABLE": "logs",
    "STORAGE_TABLE_LOGS_LEVEL": "DEBUG",
    "DATA_STORAGE_ACCOUNT": "<development storage account>",
    "DATA_CONTAINER": "collections"
  }
}
```

> Once Visual Studio Code ends the Dev Container setup, you'll need to restart the environment to ensure the new settings are loaded.

Before running the function app locally, you need to set the following permissions to your account (or your VM identity if you are running Visual Studio Code from an Azure VM):

* On the storage account:
  * Storage Blob Data Contributor
  * Storage Blob Delegator
  * Storage Queue Data Contributor
  * Storage Table Data Contributor
* On the Spatio GeoCatalog:
  * GeoCatalog Administrator

In your development storage account, create the following containers:

* `collections`
* `data`
* `templates`

In your GeoCatalog, create credentials for the following containers in your storage account:

* `collections`
* `data`

Also, create a new collection named `potsdam`.

*NOTE:* PM to review if OK to share the below information with Private Preview customers. Also, the same must be removed in final public docs.

Microsoft internal users can copy some of the data from the `Datazoo` storage account to your development storage account. i.e., copy the files `1_DSM/1_DSM/dsm_potsdam_02_*` from the Datazoo to the `/potsdam` in the `data` container in your development storage account.
For users outside Microsoft, you can download the *Potsdam* dataset by clicking this link https://www.isprs.org/education/benchmarks/UrbanSemLab/default.aspx, and following the instructions.

Copy the `templates/potsdam,j2` file from this repo to the `templates` container in your development storage account.

## Run the Function App Locally

To run the Function App locally press `F5` in Visual Studio Code or select the menu option *Run* > *Start Debugging*. Once the function is up and running, you can invoke an orchestration by executing the following command in the terminal:

```bash
development_account="<name of your development storage account>"
curl -v -X POST http://localhost:7071/api/orchestrations/geotemplate_bulk_transform \
--json @- << EOF
{
  "crawlingType": "file",
  "sourceStorageAccountName": "$development_account",
  "sourceContainerName": "data",
  "startingDirectory": "potsdam",
  "pattern": "*.tif",
  "templateUrl": "https://$development_account.blob.core.windows.net/templates/potsdam.j2",
  "targetCollectionId": "potsdam"
}
EOF
```

## Deploy the Function App

To deploy STACForge to Azure, follow the document [STACForge Deployment](doc/deployment.md).

> **Note:** Do not use the same storage account for the development and production environments. If you want to reuse the source data and templates, set permissions accordingly.

Once he deployment is finished, you can deploy the code using Visual Studio *Deploy to Azure...* feature:

![VSCode Deploy to Azure...](doc/img/deploy_function.png)
