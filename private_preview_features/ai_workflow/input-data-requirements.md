---
title: Input data requirements for AI Workflow supported models
description: Learn the imagery, STAC metadata, video, and telemetry requirements for models supported by AI Workflow.
author: aloverro
ms.author: adamloverro
ms.service: planetary-computer-pro
ms.topic: concept-article
ms.date: 10/29/2026
# customer intent: As a geospatial developer, I want to understand model input requirements so that I can prepare data for AI Workflow.
---

# Input data requirements for AI Workflow supported models

This article describes the input data requirements for each model supported by AI Workflow. Use these requirements when preparing data for ingestion into Microsoft Planetary Computer Pro.

> [!IMPORTANT]
> AI Workflow is currently in invite-only private preview. Features and capabilities are subject to change.

## EO_OS Object Detection Model

The [Earth Observation Overhead Sensing Model](https://ai.azure.com/catalog/models/eo-os-object-detection) requires orthorectified satellite or airborne imagery.

| Requirement | Value |
| --- | --- |
| Ground sample distance (GSD) | Between 30 and 150 cm; optimal GSD is 60 cm |
| Imagery format | RGB Cloud Optimized GeoTIFF (COG), ingested into Microsoft Planetary Computer Pro |
| STAC metadata | GSD, projection (for example, `proj:epsg`), band information (for example, `eo:bands`), and accurate bounding box (`bbox`) and geometry fields |
| Optimal tiling | 1024 x 1024 pixels |
| Tile stride | 800 pixels, with approximately 20% overlap between adjacent tiles |
| Detection confidence threshold | 0.5 |

## MARS Model

The [MARS Automated Feature Extraction Model](https://ai.azure.com/catalog/models/mars-map-autoregressive) requires orthorectified satellite or airborne imagery.

| Requirement | Value |
| --- | --- |
| Ground sample distance (GSD) | Between 25 and 75 cm; optimal GSD is 60 cm |
| Imagery format | RGB Cloud Optimized GeoTIFF (COG), ingested into Microsoft Planetary Computer Pro |
| STAC metadata | `gsd`, projection (for example, `proj:epsg`), band information (for example, `eo:bands`), and accurate bounding box (`bbox`) and geometry fields |

### Scenarios to avoid

For optimal results, avoid:

- **Polygons with interior holes** - The model doesn't currently support multiply connected polygons, such as donut-shaped polygons, and fills internal voids.
- **Challenging environmental conditions** - Significant cloud cover, extensive dirt road networks, or highly arid urban environments characterized by desert or sandy terrain.
- **Large transportation complexes** - Expansive railroad yards or multi-level highway interchanges with several overlapping road networks.
- **Extremely dense urban centers** - Areas dominated by high-rise skyscrapers and significant building overlap.

The model generally performs best in regions with moderate building density and clear building separation, particularly across North America, Europe, and Australia. Although the model can be applied globally, performance can vary in highly dense metropolitan areas, complex transportation corridors, and challenging environmental conditions.

## FMV Grounding Object Detection Model

For the [Full Motion Video Grounding Detection Model](https://ai.azure.com/catalog/models/fmv-grounding-detection), each source STAC item represents one video segment and must contain two assets: the video and its telemetry. Items missing a required asset are rejected.

### Video asset

| Requirement | Value |
| --- | --- |
| Asset key | `Video`, `data`, `fmv`, or `mp4` |
| Codec | H.264 |
| Container | MPEG-TS or MP4 |
| Frame rate | Constant. Variable frame rate isn't supported. |
| Content | `One continuous se` (incomplete wording in the source document; see the following note) |
| Duration | 60 seconds maximum (hard limit). Split longer footage into multiple STAC items before ingestion. |

> [!NOTE]
> The source document's video content requirement ends at "One continuous se". Confirm the full requirement with the Microsoft Planetary Computer team before preparing video inputs.

### Telemetry asset

Telemetry is MISB ST 0601 KLV exported to CSV, with a header row followed by one row per telemetry sample. KLV carried as a metadata stream inside the transport stream isn't read. Demultiplex it to a CSV sidecar before ingestion.

| Requirement | Value |
| --- | --- |
| Asset key | `Metadata`, `KLV`, `telemetry`, or `csv` |
| Format | CSV with a header row and one row per telemetry sample |
| Rows | At least two |
| Time span | Greater than zero and no more than 60 seconds |

Columns are identified by name, never by position. Column order doesn't matter, and columns not listed in the following sections are ignored. Names are matched case-insensitively, and spaces are treated as underscores. For example, `2:Unix Time Stamp` and `2:unix_time_stamp` identify the same column.

Each name carries the MISB ST 0601 tag number as a prefix, in the form `<tag>:<field name>`. Standard KLV export tools already produce this format.

### Required timestamp

| MISB tag | Column name | Meaning |
| --- | --- | --- |
| 2 | `2:unix_time_stamp` or `2:precision_timestamp` | Sample time, in UNIX microseconds |

Timestamps must be strictly increasing. They order the samples, establish the telemetry time span, and become the `datetime` of the output STAC item.

### Required frame footprint

Supply the frame footprint in either of the following forms. Absolute corners are used when present. Otherwise, offset corners are added to the frame center.

| Form | MISB tags | Column names |
| --- | --- | --- |
| Absolute corners | 82-89 | `82:corner_lat_1`, `83:corner_lon_1`, `84:corner_lat_2`, `85:corner_lon2`, `86:corner_lat_3`, `87:corner_lon_3`, `88:corner_lat_4`, `89:corner_lon_4` |
| Frame center + offset corners | 23, 24, 26-33 | `23:frame-center_latitude`, `24:frame_center_longitude`, `26:offset_corner_lat_1`, `27:offset_corner_lon_1`, `28:offset_corner_lat_2`, `29:offset_corner_lon_2`, `30:offset_corner_lat_3`, `31:offset_corner_lon_3`, `32:offset_corner_lat_4`, `33:offset_corner_lon_4` |

> [!NOTE]
> Column names are preserved as supplied in the source document. Its table lists `23:frame-center_latitude`, but its CSV example uses `23:frame_center_latitude`. The absolute-corner table also lists `85:corner_lon2` without the underscore used in the other corner names. Confirm the accepted names before preparing telemetry.

Corners are numbered 1 to 4 clockwise from the top-left of the image:

1. Corner 1 is the ground position of the image's top-left pixel.
1. Corner 2 is the ground position of its top-right pixel.
1. Corner 3 is the ground position of its bottom-right pixel.
1. Corner 4 is the ground position of its bottom-left pixel.

The following example uses a frame center and offset corners:

```csv
2:unix_time_stamp,23:frame_center_latitude,24:frame_center_longitude,26:offset_corner_lat_1,27:offset_corner_lon_1,28:offset_corner_lat_2,29:offset_corner_lon_2,30:offset_corner_lat_3,31:offset_corner_lon_3,32:offset_corner_lat_4,33:offset_corner_lon_4
1755792000000000,41.14020,-104.82550,0.00181,-0.00243,0.00174,0.00251,-0.00186,0.00244,-0.00179,-0.00248
1755792000208333,41.14023,-104.82544,0.00181,-0.00243,0.00174,0.00251,-0.00186,0.00244,-0.00179,-0.00248
```

### Why corner values are required

Corner tags are optional in MISB ST 0601. A sensor can publish only its own position, attitude, field of view, and slant range, leaving the consumer to compute the ground footprint against a terrain model. This pipeline doesn't perform that derivation, so you must supply the corners directly.

Detections are located in image pixels. The frame center alone fixes a single point and conveys nothing about the image's scale, rotation, or perspective, so every detection in a frame would resolve to the same coordinate. The four corners provide the reference points needed to map any pixel in the frame to a ground position.

### Telemetry coverage

Telemetry should cover the whole video segment. If it stops early, only the covered portion of the video is analyzed, and the remainder is reported as uncovered. Partial coverage isn't an error.

### Rejection reasons

An item is rejected immediately, without retry, under the following conditions:

| Condition | Reason reported |
| --- | --- |
| Telemetry asset missing, or fewer than two rows | `Missingklv` |
| Required timestamp or corner columns absent | `InvalidklvSchema` |
| Timestamps unparseable or not strictly increasing | `NonMonotonicklv` |
| Telemetry span exceeds 60 seconds | `SegmentTooLong` |
| Telemetry span is zero | `NoTelemetryOverlap` |

## Related content

- [AI Workflow overview](./ai-workflow-overview.md)
- [Get started with AI Workflow](./get-started-ai-workflow.md)
- [Use AI Workflow to compare residential development](./use-ai-workflow.md)
