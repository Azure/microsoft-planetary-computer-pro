---
title: AI Workflow for Microsoft Planetary Computer Pro (Private Preview)
description: Learn how AI Workflow connects GeoCatalog data to deployed geospatial AI models to run inference, store results, and monitor executions.
author: aloverro
ms.author: adamloverro
ms.service: planetary-computer-pro
ms.topic: overview
ms.date: 10/21/2026
#customer intent: As a geospatial analyst or developer, I want to understand AI Workflow so that I can run repeatable inference on GeoCatalog data without building custom orchestration code.
---

# What is AI Workflow for Microsoft Planetary Computer Pro? (Private Preview)

AI Workflow is an orchestration capability in Microsoft Planetary Computer Pro that lets you run inference with supported geospatial AI models on data stored in GeoCatalog. It connects input data, a deployed model endpoint, and an output collection through APIs.

Instead of writing custom scripts to coordinate data preparation, model execution, and output management, you define a reusable workflow. AI Workflow executes the workflow and stores inference results in GeoCatalog for discovery, visualization, and downstream analysis.

> [!IMPORTANT]
> AI Workflow is currently in invite-only private preview. Contact the Microsoft Planetary Computer team to request access and enable the feature for your GeoCatalog. Features and behavior are subject to change.

## What you can do with AI Workflow

- **Connect data and models through APIs.** Use imagery ingested into GeoCatalog with supported models deployed through Microsoft Foundry.
- **Reuse workflow definitions.** Save the model, area of interest, input filters, and output settings for repeatable inference.
- **Catalog inference results.** Store outputs as STAC items and assets in a designated GeoCatalog collection.
- **Monitor executions.** Track run status and progress, review run history, and request cancellation of active runs.

## How AI Workflow works

A workflow definition describes what data to process, which model to use, and where to store the results. A workflow run is an execution of that saved definition.

1. **Prepare your data and model.** Ingest supported data into GeoCatalog and deploy a supported model endpoint through Microsoft Foundry.
1. **Authorize access to the model.** Assign a user-assigned managed identity the **AzureML Data Scientist** role on the model endpoint, attach the identity to your GeoCatalog, and register the endpoint as an ingestion source.
1. **Create an output collection.** Prepare a STAC collection to receive inference results.
1. **Define a workflow.** Specify the model endpoint, area of interest, input collection and filters, and output collection.
1. **Run and monitor the workflow.** Start an execution and retrieve its status and progress through the APIs.
1. **Use the results.** Open the output collection to discover the generated STAC items and assets.

### Workflow configuration

| Setting | Purpose |
| --- | --- |
| Model ID and endpoint | Identify the supported model and its deployed inference endpoint. |
| Area of interest | Define the geographic area to process. The example uses a GeoJSON FeatureCollection containing a Polygon in WGS 84 longitude and latitude. |
| Model input | Identify the input collection, model-specific input name, item filter, and item limit. |
| Output collection | Identify the destination STAC collection for inference results. |
| Output size | Configure output sizing. The example uses `MatchInput`. |

For a complete request and the setup steps, see [Use AI Workflow](./use-ai-workflow.md).

## Supported models

During private preview, AI Workflow supports the following models deployed through Microsoft Foundry to Azure Machine Learning endpoints:

| Model | Model catalog ID |
| --- | --- |
| [Earth Observation Overhead Sensing Model](https://ai.azure.com/catalog/models/eo-os-object-detection) | `eo-os-object-detection` |
| [MARS Automated Feature Extraction Model](https://ai.azure.com/catalog/models/mars-map-autoregressive) | `mars-map-autoregressive` |
| [Full Motion Video Grounding Detection Model](https://ai.azure.com/catalog/models/fmv-grounding-detection) | `fmv-grounding-detection` |

Review the associated model card in Microsoft Foundry for input requirements, supported ontologies, performance characteristics, and metrics. Input names and supported parameters are model-specific.

### Input and output data

Ingest input data into a GeoCatalog collection before running a workflow. Data must meet the requirements of the selected model.

For example, the MARS workflow in the how-to uses orthorectified RGB satellite imagery ingested as Cloud Optimized GeoTIFFs. Its STAC metadata includes ground sample distance (GSD), projection, band information, bounding box, and item geometry. The documented MARS GSD range is 25 to 75 centimeters, with 60 centimeters identified as optimal and an optimal tile size of 512 x 512 pixels. Confirm these requirements against the model card before preparing your data.

Inference results are stored as STAC items and assets in the output collection. Output formats for supported models include GeoJSON and GeoParquet. You can use these assets in downstream analytics or visualization tools, such as ArcGIS, subject to format compatibility.

## Authentication and access

AI Workflow uses two access paths:

- **Your application to GeoCatalog.** Authenticate API requests with a Microsoft Entra ID bearer token. For guidance, see [Configure application authentication](https://learn.microsoft.com/azure/planetary-computer/application-authentication).
- **GeoCatalog to the deployed model.** Use a user-assigned managed identity authorized on the model endpoint. The endpoint must use Microsoft Entra token-based authentication. Register the endpoint in GeoCatalog as an ingestion source with the managed identity.

## Pricing

> [!NOTE]
> The AI Workflow capability is available at no additional cost during private preview. Underlying Azure resource charges still apply.

You can incur charges for:

- Input and output data storage in Microsoft Planetary Computer Pro. See [Microsoft Planetary Computer Pro pricing](https://azure.microsoft.com/pricing/details/planetary-computer-pro/).
- GPU resources used by deployed AI models for inference.

## Private preview considerations

- **Invite-only access.** AI Workflow must be enabled for your GeoCatalog by the Microsoft Planetary Computer team.
- **Supported models only.** Use one of the supported model deployments and verify its input requirements.
- **GPU capacity.** Ensure that sufficient GPU quota and compute capacity are available for your deployment.
- **Concurrent workloads.** Avoid large-scale STAC ingestion while running AI Workflow jobs. In private preview, concurrent ingestion and inference can increase CPU utilization and affect execution times.
- **Preview API.** The how-to uses API version `2026-08-01-preview`.

## Next steps

- [Set up and use AI Workflow](./use-ai-workflow.md)

## Related content

- [Deploy a GeoCatalog resource](https://learn.microsoft.com/azure/planetary-computer/deploy-geocatalog-resource)
- [Manage access to Microsoft Planetary Computer Pro](https://learn.microsoft.com/azure/planetary-computer/manage-access)
- [Microsoft Foundry model catalog](https://ai.azure.com/catalog)
