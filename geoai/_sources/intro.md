# GeoAI

Welcome to the GeoAI documentation for Microsoft Planetary Computer Pro!

## About

Microsoft is developing GeoAI (Geospatial Artificial Intelligence) solutions by delivering tools and tutorials that unify the geospatial data management capabilities of Microsoft Planetary Computer Pro and the Azure AI platform Microsoft Foundry. Through a combination of first-party and third-party models, Microsoft is building an ecosystem of GeoAI capabilities for organizations to deploy at scale with Azure Cloud.

We are using this resource to share and distribute materials to help guide your organization on your journey to build AI powered geospatial solutions. As new models and capabilities are released we will announce them through our product blogs for [Planetary Computer Pro](https://techcommunity.microsoft.com/category/azure/blog/microsoft-planetary-computer-blog) or [Microsoft Foundry](https://techcommunity.microsoft.com/category/azure-ai-foundry/blog/azure-ai-foundry-blog), and provide documentation, examples, and tutorials here. 

### Support
If you have questions, or experience any challenges working with this resource, please [open an issue](https://github.com/Azure/microsoft-planetary-computer-pro/issues/new).

## GeoAI Models

| Model Name | Description | Publisher | Applications | Example(s) |
|---|---|---|---|---|
| Aurora | AI weather forecasting model for atmospheric and climate impact analysis. [Model Card](https://ai.azure.com/catalog/models/Aurora) | Microsoft Research | Weather Forecasting | [Storm Impact Assessment](https://aka.ms/aurora-on-mpc-github) |
| EO-OS Object Detection | Geospatial object detection model for Earth observation imagery. [Model Card](https://ai.azure.com/catalog/models/eo-os-object-detection) | Microsoft | Object Detection | [Airplane detection with NAIP](./examples/eoos_object_detection.ipynb) |
| MARS Map Autoregressive | Autoregressive geospatial model for map generation and completion tasks. [Model Card](https://ai.azure.com/catalog/models/mars-map-autoregressive) | Microsoft | Map Generation | [Map Feature Extraction with NAIP](./examples/mars_map_generation.ipynb) |
| Fields of the World (FTW) 'PRUE' | Baseline AI model for agricultural field boundary detection. [Model Card](https://ai.azure.com/catalog/models/ftw-prue-efnet-b7-ccby) | Taylor Geospatial | Agriculture | Coming Soon |
| Earth2Studio FCN3 StormScope | Storm-focused weather forecasting model for atmospheric prediction workflows. [Model Card](https://ai.azure.com/catalog/models/earth2studio-fcn3-stormscope) | NVIDIA | Weather Forecasting | Coming Soon |
| Earth2Studio FCN3 | Foundation weather forecasting model for global atmospheric prediction. [Model Card](https://ai.azure.com/catalog/models/earth2studio-fcn3) | NVIDIA | Weather Forecasting | Coming Soon |


## GeoAI SDK (Preview)

The Planetary Computer Pro [GeoAI SDK](./geoai-sdk/README.md) provides an extensible, Python API for working with geospatial AI models. By abstracting interactions with Planetary Computer, Planetary Computer Pro, and GeoAI models hosted in Microsoft Foundry.  As new models are added to the geospatial ai model offerings in Foundry, the GeoAI SDK can be extended to support new models while providing an easy to use and consistent user experience.

## Azure Services

### Microsoft Planetary Computer

The Planetary Computer combines a multi-petabyte catalog of global environmental data with intuitive APIs, a flexible scientific environment that allows users to answer global questions about that data, and applications that put those answers in the hands of conservation stakeholders. [Learn More](https://aka.ms/planetarycomputer)

### Microsoft Planetary Computer Pro

Microsoft Planetary Computer's vision is to empower every organization to unlock the full potential of geospatial data. Microsoft Planetary Computer Pro is a geospatial data management service built on top of Azure's hyperscale infrastructure and ecosystem. The Microsoft Planetary Computer Pro GeoCatalog is a new Azure resource that provides foundational capabilities to ingest, manage, search, and distribute geospatial datasets. [Learn more](https://aka.ms/planetarycomputerpro)

### Microsoft Foundry

Microsoft Foundry is a unified Azure platform-as-a-service offering for enterprise AI operations, model builders, and application development. This foundation combines production-grade infrastructure with friendly interfaces, enabling developers to focus on building applications rather than managing infrastructure. Microsoft Foundry unifies agents, models, and tools under a single management grouping with built-in enterprise-readiness capabilities including tracing, monitoring, evaluations, and customizable enterprise setup configurations. [Learn More](https://ai.azure.com)