---
title: Use AI Workflow in Microsoft Planetary Computer Pro (Private Preview)
description: Learn how to configure model access, create an AI Workflow, run inference on GeoCatalog imagery, monitor runs, and access results.
author: aloverro
ms.author: adamloverro
ms.service: planetary-computer-pro
ms.topic: how-to
ms.date: 10/21/2026
#customer intent: As a geospatial developer, I want to configure and run AI Workflow so that I can extract features from imagery and store inference results in GeoCatalog.
---

# Use AI Workflow in Microsoft Planetary Computer Pro (Private Preview)

This article shows you how to set up AI Workflow and use its APIs to run the MARS Automated Feature Extraction model on overhead imagery of Pereira, Colombia. You create a reusable workflow, start a run, monitor its progress, and access the results in GeoCatalog.

For background and supported models, see [What is AI Workflow?](./ai-workflow-overview.md).

> [!IMPORTANT]
> AI Workflow is currently in invite-only private preview. Contact the Microsoft Planetary Computer team to enable it for your GeoCatalog before following these steps. Features and behavior are subject to change.

## Prerequisites

- An Azure subscription with an existing [GeoCatalog resource](https://learn.microsoft.com/azure/planetary-computer/deploy-geocatalog-resource) and AI Workflow enabled.
- Access to manage GeoCatalog collections and ingestion sources. See [Manage access to Microsoft Planetary Computer Pro](https://learn.microsoft.com/azure/planetary-computer/manage-access).
- Permissions to deploy a model through Microsoft Foundry, create a user-assigned managed identity, assign its endpoint role, and attach the identity to your GeoCatalog.
- Sufficient GPU quota and compute capacity for the selected model deployment.
- Supported imagery ingested into a GeoCatalog STAC collection. For this example, use a collection named `colombia-earthquake-imagery` containing the pre-event and post-event imagery you want to analyze.
- Python with the `requests` package installed for the API examples.
- A Microsoft Entra ID access token for GeoCatalog. See [Configure application authentication](https://learn.microsoft.com/azure/planetary-computer/application-authentication).

The MARS example expects orthorectified RGB satellite imagery ingested as Cloud Optimized GeoTIFFs, with STAC metadata for GSD, projection, bands, bounding box, and item geometry. The documented MARS GSD range is 25 to 75 centimeters, with 60 centimeters identified as optimal and an optimal tile size of 512 x 512 pixels. Review the [MARS model card](https://ai.azure.com/catalog/models/mars-map-autoregressive) for current requirements before preparing your data.

> [!NOTE]
> Avoid large-scale STAC ingestion while running AI Workflow jobs during private preview. Concurrent ingestion and inference can increase CPU utilization and affect execution times.

## Step 1: Deploy a supported model

1. Sign in to [Microsoft Foundry](https://ai.azure.com/) and open the model catalog.
1. Search for `mars-map-autoregressive`. For other supported models, see the [AI Workflow overview](./ai-workflow-overview.md#supported-models).
1. Select **Use this model** and select a project.
1. Choose the endpoint and deployment names.
1. Select the instance count and virtual machine SKU based on your inference throughput requirements and available GPU capacity.
1. Deploy the model.
1. On the resulting Azure Machine Learning endpoint, verify that the authentication type is **Microsoft Entra token-based (Azure AD)**.
1. Copy the endpoint's **REST endpoint** URL. You use this URL when registering the endpoint and creating the workflow.

## Step 2: Authorize GeoCatalog to invoke the model

1. In the Azure portal, create a [user-assigned managed identity](/entra/identity/managed-identities-azure-resources/how-manage-user-assigned-managed-identities).
1. Assign the identity the **AzureML Data Scientist** role on the deployed model endpoint.
1. Open your GeoCatalog resource in the Azure portal.
1. Under **Security**, select **Identity**.
1. Select **Add**, select the subscription and user-assigned managed identity, and then select **Add** to attach it to the GeoCatalog.

## Step 3: Register the model endpoint

Register the deployed model endpoint as an ingestion source so that GeoCatalog can invoke it with the managed identity.

1. In your GeoCatalog, go to **Settings** and select **Create Ingestion Source**.
1. For **Credential Type**, select **Managed Identity**.
1. For **Container URL**, enter the REST endpoint URL from Step 1.
1. For **Managed Identity**, select the identity authorized in Step 2.
1. Create the ingestion source.

## Step 4: Create the output collection

1. In your GeoCatalog, select **Collections** > **Create Collection** > **Load a Template Collection**.
1. Set `id` to a unique collection identifier. This example uses `pereira-mars-building-footprints`.
1. Set `title` to a descriptive name, such as `Pereira MARS Building Footprints`.
1. Add an `item_assets` definition to the collection JSON at the same level as `stac_version`. The following example describes image and GeoJSON result assets:

   ```json
   "item_assets": {
     "image": {
       "type": "image/tiff; application=geotiff; profile=cloud-optimized",
       "roles": ["data"],
       "title": "Satellite Image Object Detections"
     },
     "geojson": {
       "type": "application/geo+json",
       "roles": ["data"],
       "title": "Object Detections Results GeoJSON"
     }
   }
   ```

   This is a property to add to the template, not a complete collection document. Retain the template's other required fields and ensure that asset definitions match the outputs of your selected model.

1. Review the configuration and select **Create**.

For additional guidance, see [Create STAC collections](https://learn.microsoft.com/azure/planetary-computer/create-stac-collection?tabs=restapi).

## Step 5: Configure the API example

Run the following Python examples in order in the same session. They use API version `2026-08-01-preview`.

Set these environment variables before running the code:

| Variable | Value |
| --- | --- |
| `GEOCATALOG_URL` | Your GeoCatalog endpoint URL, such as `https://<name>.<hash>.<region>.geocatalog.spatio.azure.com`. |
| `MODEL_ENDPOINT` | The deployed model's REST endpoint URL registered in Step 3. |
| `SPATIO_ACCESS_TOKEN` | A valid Microsoft Entra ID access token for GeoCatalog, without the `Bearer ` prefix. |

Do not store access tokens in source code or commit them to source control.

```python
import os

import requests

BASE_URL = os.environ["GEOCATALOG_URL"].rstrip("/")
MODEL_ENDPOINT = os.environ["MODEL_ENDPOINT"]
API_VERSION = "2026-08-01-preview"
WORKFLOW_ID = "colombia-earthquake-pereira-assessment"
ACCESS_TOKEN = os.environ["SPATIO_ACCESS_TOKEN"]

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
}
```

Define the workflow:

```python
WORKFLOW_BODY = {
    "displayName": "Pereira earthquake assessment",
    "description": "MARS building extraction for pre/post-event imagery in Pereira",
    "modelId": "microsoft/mars-map-autoregressive",
    "modelEndpoint": MODEL_ENDPOINT,
    "areaOfInterest": {
        "kind": "GeoJson",
        "geoJson": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-75.7350, 4.7900],
                                [-75.6900, 4.7900],
                                [-75.6900, 4.8400],
                                [-75.7350, 4.8400],
                                [-75.7350, 4.7900],
                            ]
                        ],
                    },
                    "properties": {},
                }
            ],
        },
    },
    "modelInput": {
        "image_data": {
            "collectionId": "colombia-earthquake-imagery",
            "filter": {
                "op": "and",
                "args": [
                    {
                        "op": ">=",
                        "args": [{"property": "datetime"}, "2024-01-01T00:00:00Z"],
                    },
                    {
                        "op": "<=",
                        "args": [{"property": "datetime"}, "2024-12-31T23:59:59Z"],
                    },
                ],
            },
            "limit": 50,
        }
    },
    "outputCollectionId": "pereira-mars-building-footprints",
    "outputSize": {"kind": "MatchInput"},
}
```

Before submitting the workflow, adjust these values for your data:

- **Model:** Confirm the deployed endpoint, model ID, model input name (`image_data` in this example), and supported parameters.
- **Area of interest:** Replace the example polygon with your target area. Coordinates use WGS 84 longitude and latitude.
- **Input collection and dates:** Update the collection ID and ISO 8601 UTC date range to match available imagery. The example selects imagery within 2024, up to the configured limit of 50 items. If you're comparing pre-event and post-event results, ensure the range includes both periods.
- **Output collection:** Use the collection ID created in Step 4.

This workflow extracts features from matching imagery. Downstream comparison and analyst validation of pre-event and post-event results are separate from this example.

## Step 6: Create or replace the workflow

Use `PUT` to save the definition under your workflow ID.

> [!IMPORTANT]
> If the workflow ID already exists, this request replaces its saved definition. Use a unique ID to avoid replacing another workflow.

```python
response = requests.put(
    f"{BASE_URL}/ai/workflows/{WORKFLOW_ID}",
    params={"api-version": API_VERSION},
    headers=HEADERS,
    json=WORKFLOW_BODY,
    timeout=60,
)
response.raise_for_status()
create_response = response.json()
print(
    create_response["id"],
    create_response["createdAt"],
    create_response["lastModifiedAt"],
)
```

A successful request returns `200 OK` or `201 Created`. Confirm that the response `id` matches `WORKFLOW_ID` and includes creation and modification timestamps.

### List saved workflows

```python
response = requests.get(
    f"{BASE_URL}/ai/workflows",
    params={"api-version": API_VERSION, "top": 15},
    headers=HEADERS,
    timeout=60,
)
response.raise_for_status()
list_response = response.json()
workflows = list_response["value"]
print([workflow["id"] for workflow in workflows])
```

A successful request returns `200 OK` with workflow definitions in `value`. This request asks for up to 15 workflows; absence from this response alone doesn't prove that your workflow doesn't exist. Retrieve it by ID to verify the saved definition.

### Retrieve the saved definition

```python
response = requests.get(
    f"{BASE_URL}/ai/workflows/{WORKFLOW_ID}",
    params={"api-version": API_VERSION},
    headers=HEADERS,
    timeout=60,
)
response.raise_for_status()
workflow_definition = response.json()
print(
    workflow_definition["displayName"],
    workflow_definition["modelId"],
    workflow_definition["outputCollectionId"],
)
```

A successful request returns `200 OK`. Confirm that the model and input/output settings match your intended configuration.

## Step 7: Run the workflow

Use `POST` to start an execution of the saved definition:

```python
response = requests.post(
    f"{BASE_URL}/ai/workflows/{WORKFLOW_ID}:run",
    params={"api-version": API_VERSION},
    headers=HEADERS,
    timeout=60,
)
response.raise_for_status()
run_response = response.json()
run_id = run_response["id"]
print(run_response)
```

A successful request returns `202 Accepted`. The response includes run metadata such as `id`, `workflowId`, `status`, `percentComplete`, `createdAt`, and `lastModifiedAt`. The initial status is typically `NotStarted` or `Running`.

Save `run_id` to retrieve the status of this specific execution. Acceptance of the request doesn't mean inference has finished.

## Step 8: Monitor execution and review run history

Retrieve the run status:

```python
response = requests.get(
    f"{BASE_URL}/ai/workflows/{WORKFLOW_ID}/runs/{run_id}",
    params={"api-version": API_VERSION},
    headers=HEADERS,
    timeout=60,
)
response.raise_for_status()
run_status = response.json()
print(
    run_status["status"],
    run_status.get("percentComplete"),
    run_status.get("finishedAt"),
)
```

A successful status request returns `200 OK`. Repeat the request to monitor progress toward a terminal state such as `Succeeded` or `Failed`. Check `status` to determine the outcome, not just `percentComplete`. If the run fails, inspect the returned run details before starting another execution.

To review active and historical runs for the workflow:

```python
response = requests.get(
    f"{BASE_URL}/ai/workflows/{WORKFLOW_ID}/runs",
    params={"api-version": API_VERSION, "top": 20},
    headers=HEADERS,
    timeout=60,
)
response.raise_for_status()
runs_response = response.json()
runs = runs_response["value"]
for run in runs:
    print(run["id"], run["status"], run.get("percentComplete"))
```

A successful request returns `200 OK` with run entries in `value`. This example requests up to 20 entries. Use the specific run status endpoint to check a run that isn't in the returned list.

### Cancel an active run

To request cancellation, first retrieve the latest status using the status request above. For a run that is still `NotStarted` or `Running`, submit:

```python
if run_status["status"] in {"NotStarted", "Running"}:
    response = requests.post(
        f"{BASE_URL}/ai/workflows/{WORKFLOW_ID}/runs/{run_id}:cancel",
        params={"api-version": API_VERSION},
        headers=HEADERS,
        timeout=60,
    )
    response.raise_for_status()
    print(response.json())
else:
    print(f"Cancellation not requested: run status is {run_status['status']}.")
```

An accepted cancellation request returns `200 OK` with an updated run state. Retrieve the status again to verify the outcome.

## Step 9: Access inference results

After the run succeeds:

1. Open your GeoCatalog and go to **Collections**.
1. Open the configured output collection, `pereira-mars-building-footprints` in this example.
1. Inspect the generated STAC items and their assets.
1. Use the output assets for downstream analysis or visualization. Supported model outputs include GeoJSON and GeoParquet; availability depends on the selected model.

For pre-event and post-event analysis, compare the extracted features from the relevant imagery and validate the findings. Compatibility with downstream tools, including ArcGIS, depends on the output format.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| GeoCatalog API request returns `401` or `403` | Verify the GeoCatalog access token is valid and your identity has the required access. Refresh the token and update `HEADERS` if it expires. |
| Workflow can't invoke the model endpoint | Verify Microsoft Entra token-based authentication, the managed identity's endpoint role assignment, its attachment to GeoCatalog, and the ingestion source's endpoint URL and identity. |
| Input imagery doesn't match the intended analysis | Check the collection ID, spatial coverage, date filter, and item limit. Confirm that the imagery meets the model's input requirements. |
| Run status is `Failed` | Inspect the returned run details and verify the model deployment, input configuration, and output collection before retrying. |
| Execution takes longer than expected | Verify model compute capacity and avoid concurrent large-scale STAC ingestion during private preview. |
| Results aren't in the expected collection | Check the saved workflow's `outputCollectionId` and the specific run's status before looking for output STAC items. |

## Related content

- [What is AI Workflow?](./ai-workflow-overview.md)
- [MARS Automated Feature Extraction model card](https://ai.azure.com/catalog/models/mars-map-autoregressive)
- [Create STAC collections](https://learn.microsoft.com/azure/planetary-computer/create-stac-collection?tabs=restapi)
- [Configure application authentication](https://learn.microsoft.com/azure/planetary-computer/application-authentication)
