---
title: Example of How to Use GeoAI Orchestrator 
description: Learn how to run MARS on NAIP imagery for two periods, monitor workflow runs, and compare building predictions in GeoCatalog.
author: aloverro
ms.author: adamloverro
ms.service: planetary-computer-pro
ms.topic: how-to
ms.date: 10/29/2026
# customer intent: As a geospatial developer, I want to run GeoAI Orchestrator on imagery from two periods so that I can compare residential development.
---

# Example of How to Use GeoAI Orchestrator

This example walks through how GeoAI Orchestrator is used to extract building footprints from NAIP imagery of Union Park, Little Elm, Texas, for two periods: 2012-2014 and 2020-2022. Run the MARS Automated Feature Extraction model separately for each period over the same area, and then compare the results.

The input collection contains Union Park imagery acquired between 2012 and 2022. Each workflow filters that collection by acquisition date and selects the most recent matching item. For the input data in this example, the selected images are from July 2014 and July 2022.

> [!IMPORTANT]
> GeoAI Orchestrator is currently in invite-only private preview. Complete [Get started with GeoAI Orchestrator](./get-started-ai-workflow.md) before following this example. Features and capabilities are subject to change.

## Example settings

| Setting | Value |
| --- | --- |
| Location | Union Park, Little Elm, Texas, USA |
| API version | `2026-08-01-preview` |
| Workflow IDs | `union-park-buildings-2012-2014`; `union-park-buildings-2020-2022` |
| Input collection | `union-park-naip` |
| Output collections | `union-park-buildings-2012-2014`; `union-park-buildings-2020-2022` |
| Model | `microsoft/mars-map-autoregressive` |
| Model input | `image_data` |
| Requested category | `Building` |
| Area of interest (AOI) | `BoundingBox`; approximately 1.1 km across; identical for both workflows |
| Coordinate system | WGS 84 longitude and latitude |
| Date-time format | ISO 8601 UTC |
| Authentication | OAuth 2.0 bearer token |

The example follows this API sequence:

1. Create or replace a workflow.
1. List workflows.
1. Get the saved workflow.
1. Run the workflow.
1. Get the workflow run status.
1. Repeat for the second input range.
1. List workflow runs.
1. View and compare results.
1. Cancel a run, if needed.

## Before you begin

Confirm that:

- GeoAI Orchestrator is enabled for your GeoCatalog.
- MARS is deployed through Microsoft Foundry.
- The deployed endpoint is registered with GeoCatalog.
- GeoCatalog is authorized to invoke the endpoint through a managed identity.
- You have a GeoCatalog API access token with permissions to create and run workflows. See [Configure application authentication](https://learn.microsoft.com/azure/planetary-computer/application-authentication).
- The input and output collections described in the following sections exist.
- The input imagery is accessible and meets the model's input requirements.
- Python and the `requests` package are available for the API examples.

### Prepare the input collection

Create a STAC collection named `union-park-naip` and ingest NAIP items covering Union Park from 2012 through 2022. For your own scenario, create a collection containing imagery for your location and dates of interest.

This example uses four acquisitions. Imagery for every intervening year isn't required.

| Acquisition | STAC item ID | Resolution |
| --- | --- | --- |
| July 6, 2012 | `tx_m_3309649_ne_14_1_20120706` | 1 m |
| July 24, 2014 | `tx_m_3309649_ne_14_1_20140724_20141006` | 1 m |
| November 11, 2020 | `tx_m_3309649_ne_14_060_20201111` | 0.6 m |
| July 4, 2022 | `tx_m_3309649_ne_14_060_20220704` | 0.6 m |

MARS uses the red, green, and blue (RGB) bands. Ingest the items and ensure their imagery assets are accessible before running the workflow. The workflow doesn't ingest NAIP data automatically.

| July 24, 2014 - 1 m NAIP | July 4, 2022 - 0.6 m NAIP |
| :---: | :---: |
| ![Union Park source imagery in 2014, showing earthworks and an existing school.](./media/image15.png) | ![Union Park source imagery in 2022, showing residential development around the school.](./media/image16.png) |

*Input NAIP imagery of Union Park in July 2014 and July 2022. The selected area changes from site preparation to a residential neighborhood.*

### Prepare the output collections

Create `union-park-buildings-2012-2014` and `union-park-buildings-2020-2022` by using the [output collection configuration](./get-started-ai-workflow.md#step-4-create-an-output-stac-collection). Separate collections make the results easy to locate and compare.

## Configure Workflow

Run the code blocks in order in the same Python session. Set the following environment variables before running the code:

| Variable | Value |
| --- | --- |
| `GEOCATALOG_URL` | Your GeoCatalog endpoint URL, such as `https://<name>.<hash>.<region>.geocatalog.spatio.azure.com`. |
| `MODEL_ENDPOINT` | The deployed MARS REST endpoint URL registered with GeoCatalog. |
| `SPATIO_ACCESS_TOKEN` | Your GeoCatalog API access token, without the `Bearer ` prefix. |

> [!IMPORTANT]
> Don't store access tokens in source code or commit them to source control.

## Step 1: Create or replace a workflow

```python
import os
import time

import requests



BASE_URL = os.environ["GEOCATALOG_URL"].rstrip("/")
API_VERSION = "2026-08-01-preview"
MODEL_ENDPOINT = os.environ["MODEL_ENDPOINT"]
INPUT_COLLECTION = "union-park-naip"

HEADERS = {
    "Authorization": f"Bearer {os.environ['SPATIO_ACCESS_TOKEN']}",
    "Content-Type": "application/json",
}

SCENARIOS = {
    "2012-2014": {
        "workflow_id": "union-park-buildings-2012-2014",
        "start": "2012-01-01T00:00:00Z",
        "end": "2015-01-01T00:00:00Z",
        "output_collection": "union-park-buildings-2012-2014",
    },
    "2020-2022": {
        "workflow_id": "union-park-buildings-2020-2022",
        "start": "2020-01-01T00:00:00Z",
        "end": "2023-01-01T00:00:00Z",
        "output_collection": "union-park-buildings-2020-2022",
    },
}

AOI = {
    "kind": "BoundingBox",
    "bbox": [
        -96.92999982245009,
        33.2227276385933,
        -96.91796751281566,
        33.23284011460632,
    ],
}


def workflow_body(period):
    scenario = SCENARIOS[period]
    return {
        "displayName": f"Union Park building extraction - {period}",
        "description": "MARS building extraction for residential-development comparison",
        "modelId": "microsoft/mars-map-autoregressive",
        "modelEndpoint": MODEL_ENDPOINT,
        "areaOfInterest": AOI,
        "modelInput": {
            "image_data": {
                "collectionId": INPUT_COLLECTION,
                "filter": {
                    "op": "and",
                    "args": [
                        {
                            "op": ">=",
                            "args": [{"property": "datetime"}, scenario["start"]],
                        },
                        {
                            "op": "<",
                            "args": [{"property": "datetime"}, scenario["end"]],
                        },
                    ],
                },
                "sortBy": [{"field": "datetime", "direction": "desc"}],
                "limit": 1,
            }
        },
        "modelHyperparameters": {"categories": ["Building"]},
        "outputCollectionId": scenario["output_collection"],
        "outputSize": {"kind": "MatchInput"},
    }


PERIOD = "2012-2014"
WORKFLOW_ID = SCENARIOS[PERIOD]["workflow_id"]
WORKFLOW_BODY = workflow_body(PERIOD)
run_ids = {}
```

### How input selection works

- **`collectionId`** selects the collection you ingested.
- **`image_data`** is the model's image-input name.
- **`filter`** selects items acquired within the date range.
- **`sortBy`** orders matching items by datetime, newest first.
- **`areaOfInterest`** selects the neighborhood to process. Bounding-box order is `[west, south, east, north]`.
- **`categories`** requests `Building` predictions.
- **`outputCollectionId`** identifies where results are published.

For the four acquisitions in this example:

| Input range | Matching acquisitions | Selected acquisition |
| --- | --- | --- |
| 2012-2014 | July 2012; July 2014 | July 24, 2014 |
| 2020-2022 | November 2020; July 2022 | July 4, 2022 |

> [!NOTE]
> Each selected tile covers the entire AOI. Don't copy `limit: 1` unchanged for an AOI that requires multiple source tiles. Check spatial coverage and adjust selection for that scenario.



Use `PUT /ai/workflows/{workflowId}` to save the workflow for the first input range. This request doesn't start inference.

> [!IMPORTANT]
> If the workflow ID already exists, `PUT` replaces its saved definition. Use a unique ID to avoid replacing another workflow.

```python
r = requests.put(
    f"{BASE_URL}/ai/workflows/{WORKFLOW_ID}",
    params={"api-version": API_VERSION},
    headers=HEADERS,
    json=WORKFLOW_BODY,
    timeout=60,
)
r.raise_for_status()
create_response = r.json()
print(
    create_response["id"],
    create_response["createdAt"],
    create_response["lastModifiedAt"],
)
```

A successful request returns `201 Created` for a new workflow or `200 OK` for a replacement. Confirm that `create_response["id"]` equals `WORKFLOW_ID` and that the response includes `createdAt` and `lastModifiedAt`.

## Step 2: List workflows

Use `GET /ai/workflows` to confirm that the workflow is available. Follow `nextLink` so that workflows on later pages aren't missed.

```python
workflows = []
url = f"{BASE_URL}/ai/workflows"
params = {"api-version": API_VERSION, "top": 20}

while url:
    r = requests.get(url, params=params, headers=HEADERS, timeout=60)
    r.raise_for_status()
    page = r.json()
    workflows.extend(page.get("value", []))
    url = page.get("nextLink")
    params = None

ids = {workflow["id"] for workflow in workflows}
print(WORKFLOW_ID in ids)
```

Each successful request returns `200 OK`. The workflow appears in the complete list with its saved definition, and `WORKFLOW_ID in ids` evaluates to `True`.

## Step 3: Get the workflow

Use `GET /ai/workflows/{workflowId}` to inspect the saved input range, AOI, model settings, and output collection before running inference.

```python
r = requests.get(
    f"{BASE_URL}/ai/workflows/{WORKFLOW_ID}",
    params={"api-version": API_VERSION},
    headers=HEADERS,
    timeout=60,
)
r.raise_for_status()
workflow_definition = r.json()
print(workflow_definition["modelInput"])
print(workflow_definition["areaOfInterest"])
print(workflow_definition["outputCollectionId"])
```

A successful request returns `200 OK` with the persisted workflow definition. Verify that:

- `modelInput` contains the configured datetime filter, descending sort, and item limit.
- `areaOfInterest` and `outputCollectionId` match your requested configuration.

## Step 4: Run the workflow

Use `POST /ai/workflows/{workflowId}:run` to start execution of the saved workflow.

```python
r = requests.post(
    f"{BASE_URL}/ai/workflows/{WORKFLOW_ID}:run",
    params={"api-version": API_VERSION},
    headers=HEADERS,
    timeout=60,
)
r.raise_for_status()
run_response = r.json()
run_id = run_response["id"]
run_ids[PERIOD] = run_id
print(run_id, run_response["status"])
```

A successful request returns `202 Accepted` with run metadata such as `id`, `workflowId`, `status`, `percentComplete`, `createdAt`, and `lastModifiedAt`. The initial status is typically `NotStarted` or `Running`.

Save the returned run ID. Acceptance doesn't mean inference has finished, and calling this API again starts another run.

## Step 5: Get the workflow run status

Use `GET /ai/workflows/{workflowId}/runs/{runId}` to poll until the run reaches `Succeeded`, `Failed`, or `Canceled`.

```python
deadline = time.monotonic() + 1800

while True:
    r = requests.get(
        f"{BASE_URL}/ai/workflows/{WORKFLOW_ID}/runs/{run_id}",
        params={"api-version": API_VERSION},
        headers=HEADERS,
        timeout=60,
    )
    r.raise_for_status()
    run_status = r.json()
    print(run_status["status"], run_status.get("percentComplete"))

    if run_status["status"] == "Succeeded":
        break
    if run_status["status"] in {"Failed", "Canceled"}:
        raise RuntimeError(f"Run did not succeed: {run_status}")
    if time.monotonic() >= deadline:
        raise TimeoutError(f"Stopped waiting for {run_id}; check its status again.")
    time.sleep(10)
```

Each successful status request returns `200 OK`. The sample prints lifecycle state and progress, and explicitly reports failed runs, canceled runs, and polling timeouts. Wait for `Succeeded` before proceeding to comparison.

> [!NOTE]
> This sample waits up to 30 minutes. Reaching the polling timeout doesn't cancel the run.

## Step 6: Repeat for the second input range

Keep the input collection, AOI, endpoint, and model settings unchanged. Switch to the second period:

```python
PERIOD = "2020-2022"
WORKFLOW_ID = SCENARIOS[PERIOD]["workflow_id"]
WORKFLOW_BODY = workflow_body(PERIOD)
```

Repeat steps 1-5 without rerunning the Python setup, which would clear `run_ids`. The second workflow filters the same input collection to 2020-2022 and selects its latest matching acquisition, July 4, 2022.

Retain both run IDs for result retrieval:

```python
print(run_ids)
```

You now have two distinct workflow definitions and runs, one per input range. Each run uses the same geographic area but a different selected acquisition.

## Step 7: List workflow runs

Use `GET /ai/workflows/{workflowId}/runs` to review each workflow's execution history and confirm that the submitted run is present.

```python
for period, scenario in SCENARIOS.items():
    runs = []
    url = f"{BASE_URL}/ai/workflows/{scenario['workflow_id']}/runs"
    params = {"api-version": API_VERSION, "top": 20}

    while url:
        r = requests.get(url, params=params, headers=HEADERS, timeout=60)
        r.raise_for_status()
        page = r.json()
        runs.extend(page.get("value", []))
        url = page.get("nextLink")
        params = None

    print(period, run_ids[period] in {run["id"] for run in runs})
```

Each successful request returns `200 OK`. The sample prints `True` for both periods. Run records include lifecycle state, progress, and timestamps.

## Step 8: View and compare results

Open the configured output collections in GeoCatalog:

| Input range | Output collection |
| --- | --- |
| 2012-2014 | `union-park-buildings-2012-2014` |
| 2020-2022 | `union-park-buildings-2020-2022` |

Find each run's output STAC items by using `workflow_id` and `workflow_run_id`. Use the run IDs saved earlier, especially if a workflow has been executed more than once.

Inspect the output imagery and GeoJSON prediction assets over the corresponding source imagery. GeoParquet is available through a configured downstream vector transformation.

![Side-by-side MARS overlays for Union Park: July 2014 with 26 building predictions and July 2022 with 723 predictions. Counts are model outputs, not validated new-building counts.](./media/image17.png)

*Union Park in July 2014 and July 2022. Site preparation in the earlier image is replaced by residential streets and houses in the later image. Building predictions are shown in red.*

### Reference results from the tested experiment

| Input range | Actual imagery acquisition | Patches | Building predictions |
| --- | --- | --- | --- |
| 2012-2014 | July 24, 2014 | 4 | 26 |
| 2020-2022 | July 4, 2022 | 9 | 723 |

> [!IMPORTANT]
> The reference experiment selected these acquisitions by exact item ID. This walkthrough instead uses date filters, descending datetime order, and `limit: 1` to select the same acquisitions from the four-item collection. Verify the selected items and rerun this date-filter version before treating the reference counts as its measured results. Prediction counts aren't validated new-building counts.

Both runs should publish outputs to their configured collections so that you can inspect the same area at two points in time. In the reference experiment:

- Much of the central area is under development in July 2014.
- The same area contains residential streets and houses in July 2022.
- Existing buildings, such as the school, provide a recognizable reference.

## Step 9: Cancel a run (optional)

Use `POST /ai/workflows/{workflowId}/runs/{runId}:cancel` if you need to stop a run. Skip this step for the comparison runs until their results are collected.

The sample retrieves the latest state before deciding whether to cancel:

```python
PERIOD = "2020-2022"
WORKFLOW_ID = SCENARIOS[PERIOD]["workflow_id"]
run_id = run_ids[PERIOD]
run_url = f"{BASE_URL}/ai/workflows/{WORKFLOW_ID}/runs/{run_id}"

r = requests.get(
    run_url,
    params={"api-version": API_VERSION},
    headers=HEADERS,
    timeout=60,
)
r.raise_for_status()
run_status = r.json()

if run_status["status"] in {"NotStarted", "Running"}:
    r = requests.post(
        f"{run_url}:cancel",
        params={"api-version": API_VERSION},
        headers=HEADERS,
        timeout=60,
    )
    r.raise_for_status()

    # Cancellation returns an empty body; fetch the state separately.
    r = requests.get(
        run_url,
        params={"api-version": API_VERSION},
        headers=HEADERS,
        timeout=60,
    )
    r.raise_for_status()
    cancel_response = {"skipped": False, "run": r.json()}
else:
    cancel_response = {
        "skipped": True,
        "reason": f"Run is already terminal: {run_status['status']}",
    }

print(cancel_response)
```

An accepted cancellation returns `200 OK` with an empty response body. For active runs, `cancel_response["run"]` contains the state retrieved by the separate `GET` request. For terminal runs, the sample skips cancellation and sets `cancel_response["skipped"]` to `True`.

Cancellation is asynchronous. The state might initially remain `Running`, or the run might finish before cancellation takes effect.

## Reference documentation

- [GeoAI Orchestrator overview](./ai-workflow-overview.md)
- [Get started with GeoAI Orchestrator](./get-started-ai-workflow.md)
- [GeoAI Orchestrator API specification](./openapi.json)
- [Microsoft Planetary Computer Pro - Microsoft Azure](https://azure.microsoft.com/en-us/products/planetary-computer-pro)
- [Microsoft Planetary Computer Pro - Microsoft Learn](https://learn.microsoft.com/en-us/azure/planetary-computer/)


