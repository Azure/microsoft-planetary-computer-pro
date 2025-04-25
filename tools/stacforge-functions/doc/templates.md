# STACForge Templates

STACForge uses a templating system to generate STAC items. This allows users to create STAC items with a consistent structure and content. The templates are written in [Jinja2](https://jinja.palletsprojects.com/), a popular templating engine for Python. Jinja2 allows users to create templates with placeholders that are replaced with actual values when the template is rendered. The result of a Jinja2 template could be anything, but in the case of STACForge, the result is validated to ensure it is a valid STAC item.

## Template Design

The output of a STACForge template must be a valid STAC item as defined in the [STAC Item Specification](https://github.com/radiantearth/stac-spec/blob/master/item-spec/item-spec.md).

A minimal STAC item might look like this:

```json
{
  "type": "Feature",
  "stac_version": "1.0.0",
  "id": "example",
  "properties": {
    "datetime": "2020-01-01T00:00:00Z"
  },
  "geometry": {
    "type": "Polygon",
    "coordinates": [[
        [ 172.91173669923782, 1.3438851951615003 ],
        [ 172.95469614953714, 1.3438851951615003 ],
        [ 172.95469614953714, 1.3690476620161975 ],
        [ 172.91173669923782, 1.3690476620161975 ],
        [ 172.91173669923782, 1.3438851951615003 ]
      ]]
  },
  "bbox": [
    172.91173669923782,
    1.3438851951615003,
    172.95469614953714,
    1.3690476620161975
  ],
  "links": [],
  "assets": {
    "image": {
        "href": "https://example.com/image.tif",
        "type": "image/tiff; application=geotiff",
        "role": ["data"]
    }
  }
}
```

Part of this information is static and part dynamic. The dynamic parts should be replaced with placeholders in the template. For example, the `id` and `datetime` fields are dynamic and should be replaced with actual values when the template is rendered. The dynamic information is provided as a context variable named `scene_info`. The value of `scene_info` will depend on the source of the data and the method used to gather it. Currently, STACForge supports three methods for gathering information:

* **File crawler:** The file crawler method uses a crawler to gather the URL of the files contained in an Azure Storage Account container. When using this crawler, the information provided in the `scene_info` variable will be the URL of the file.
* **Directory crawler:** The directory crawler method uses a crawler to gather the URL of the directories contained in an Azure Storage Account container. When using this crawler, the information provided in the `scene_info` variable will be the URL of the directory.
* **Index crawler:** The index crawler takes a text file as input and returns every line as a scene. When using this crawler, the information provided in the `scene_info` variable will be the line of the text file. An special case of the index crawler is the NDJSON crawler, which takes a NDJSON file as input and returns every JSON object as a scene. In this case, the `scene_info` variable will be the JSON object.

Combining the static and dynamic parts, the template for the minimal STAC item would look like this:

```jinja
{# Assume scene_info contains the URL of a TIFF file #}
{# Extract the name of the TIFF file from the URL #}
{%- set filename = scene_info.split('/')[-1] %}
{# Set the id of the item the same as the file name minus the extension #}
{%- set id = filename.replace('.tif', '') %}
{# Get the relevant information from the TIFF file #}
{%- set info = get_raster_file_info(scene_info) %}
{
  "type": "Feature",
  "stac_version": "1.0.0",
  "id": "{{ id }}",
  "properties": {
    "datetime": "{{ now() }}"
  },
  "geometry": {{ info.geometry.footprint | tojson }},
  "bbox": {{ info.geometry.bbox | tojson }},
  "links": [],
  "assets": {
    "image": {
        "href": "{{ scene_info }}",
        "type": "image/tiff; application=geotiff",
        "roles": ["data"]
    }
  }
}
```
You will find more information about Jinja2 syntax in the [Template Designer Documentation](https://jinja.palletsprojects.com/en/latest/templates/). In addition to the Jinja2 syntax, STACForge provide some helper functions to make it easier to create STAC items. Those helpers are divided into:

* Functions: a code block that can be called from the template.
* Filters: a code block that can be used to modify the output of a variable.
* Tests: a code block that can be used to check the value of a variable.

## Functions

STACForge provides the following functions:

### now

```python
def now() -> str
```

Returns the current UTC date and time in ISO 8601 format.

#### Usage:

```jinja
"datetime": "{{ now() }}"
{# Output:
"datetime": "2024-10-01T15:06:33.230554Z"
#}
```

### affine_transform_from_bounds()

```python
def affine_transform_from_bounds(
    west: float,
    south: float,
    east: float,
    north: float,
    width: int,
    height: int,
) -> Affine
```

Return an Affine transformation given bounds, width and height.

Return an Affine transformation for a georeferenced raster given its bounds `west`, `south`, `east`, `north` and its `width` and `height` in number of pixels.

#### Usage:

```jinja
"transform": {{ affine_transform_from_bounds(info.bounds.west, info.bounds.south, info.bounds.east, info.bounds.north, info.width, info.height) | tojson }}
```

### affine_transform_from_origin

```python
def affine_transform_from_origin(
    west: float,
    north: float,
    xsize: float,
    ysize: float,
) -> Affine
```

Return an Affine transformation given upper left and pixel sizes.

Return an Affine transformation for a georeferenced raster given the coordinates of its upper left corner `west`, `north` and pixel sizes `xsize`, `ysize`.

#### Usage:

```jinja
"transform": {{ affine_transform_from_origin(info.bounds.west, info.bounds.north, info.width, info.height) | tojson }}
```

### get_text

```python
def get_text(
  url: str,
) -> str
```

Return the content of a text file at the given URL.

#### Usage:

```jinja
{% set info = get_text(scene_info.replace('.tif', '.txt')) %}
"properties": {
  "description": "{{ info }}"
}
```

### get_xml

```python
def get_xml(
  url: str,
  **kwargs,
) -> Dict[str, Any]
```

Return the content of an XML file at the given URL as a dictionary.

#### Usage:

```jinja
{% set info = get_xml(scene_info) %}
"id": "{{ info.id }}"
```

### get_json

```python
def get_json(
  url: str,
) -> Dict[str, Any]
```

Return the content of a JSON file at the given URL as a dictionary.

#### Usage:

```jinja
{% set info = get_json(scene_info) %}
"id": "{{ info.id }}"
```

### get_rasterio_dataset

```python
def get_rasterio_dataset(
    url: str,
    options: Dict[str, Any] = {},
) -> rasterio.DatasetReader
```

Open a rasterio dataset from a URL.

#### Usage:

```jinja
{% set dataset = get_rasterio_dataset(scene_info) %}
{% set geometry = dataset | geometry_info %}
"geometry": {{ geometry.footprint | tojson}}
```

### get_raster_file_info

```python
def get_raster_file_info(
    url: str,
    options: Dict[str, Any] = {},
) -> Dict[str, Any]
```

Get raster file metadata.

It returns a dictionary with the following keys:

* `projection`: projection metadata. It's the same information returned by `projection_info` filter.
* `geometry`: raster footprint. It's the same information returned by `geometry_info` filter.
* `raster_bands`: raster metadata. It's the same information returned by `raster_info` filter.
* `eo_bands`: electro-optical bands metadata. It's the same information returned by `eo_bands_info` filter.
* `tags`: raster tags.

#### Usage:

```jinja
{% set info = get_raster_file_info(scene_info) %}
"bbox": {{ info.geometry.bbox | tojson }}
```

## Filters

STACForge provides the following filters:

### regex_match

```python
def regex_match(
    string: str,
    pattern: str,
    flags: int = 0,
) -> re.Match[str] | None
```

Try to apply the pattern at the start of the string, returning a `Match` object, or `None` if no match was found.

For more information about this filter, see [`re.match` function documentation](https://docs.python.org/3.11/library/re.html#re.match).

#### Usage:

```jinja
{% set match = 'example.tif' | regex_match('(.*)\.TIF', flags=RE_IGNORECASE) %}
{{ match.groups(0) }}{# Output: example.tif #}
{{ match.groups(1) }}{# Output: example #}
```

### regex_fullmatch

```python
def regex_fullmatch(
    string: str,
    pattern: str,
    flags: int = 0,
) -> re.Match[str] | None
```

Try to apply the pattern to all of the string, returning a `Match` object, or `None` if no match was found.

For more information about this filter, see [`re.fullmatch` function documentation](https://docs.python.org/3.11/library/re.html#re.fullmatch).

#### Usage:

```jinja
{% set match = 'example.tif' | regex_fullmatch('(.*)\.TIF', flags=RE_IGNORECASE) %}
{{ match.groups(0) }}{# Output: example.tif #}
{{ match.groups(1) }}{# Output: example #}
```

### regex_search

```python
def regex_search(
    string: str,
    pattern: str,
    flags: int = 0,
) -> re.Match[str] | None
```

Scan through string looking for a match to the pattern, returning a Match object, or `None` if no match was found.

For more information about this filter, see [`re.search` function documentation](https://docs.python.org/3.11/library/re.html#re.search).

#### Usage:

```jinja
{% set match = 'example.tif' | regex_search('(.*)\.TIF', flags=RE_IGNORECASE) %}
{{ match.groups(0) }}{# Output: example.tif #}
{{ match.groups(1) }}{# Output: example #}
```

### regex_sub

```python
def regex_sub(
    string: str,
    pattern: str,
    repl: str,
    count: int = 0,
    flags: int = 0,
) -> str
```

Return the string obtained by replacing the leftmost non-overlapping occurrences of the pattern in string by the replacement `repl`. Backslash escapes in `repl` are processed.

For more information about this filter, see [`re.sub` function documentation](https://docs.python.org/3.11/library/re.html#re.sub).

#### Usage:

```jinja
{{ 'Baked Beans And Spam' | regex_sub('\sAND\s', ' & ', flags=RE_IGNORECASE) }}
{# Output: Baked Beans & Spam #}
```

### regex_subn

```python
def regex_subn(
    string: str,
    pattern: str,
    repl: str,
    count: int = 0,
    flags: int = 0,
) -> tuple[str, int]
```

Perform the same operation as `regex_sub`, but return a tuple containing the new string value and the number of replacements made.

For more information about this filter, see [`re.subn` function documentation](https://docs.python.org/3.11/library/re.html#re.subn).

```jinja
{{ 'Baked Beans And Spam' | regex_sub('\sAND\s', ' & ', flags=RE_IGNORECASE) }}
{# Output: ('Baked Beans & Spam', 1) #}
```

### regex_split

```python
def regex_split(
    string: str,
    pattern: str,
    maxsplit: int = 0,
    flags: int = 0,
) -> List[str | Any]
```

Split the source string by the occurrences of the pattern, returning a list containing the resulting substrings.  If capturing parentheses are used in pattern, then the text of all groups in the pattern are also returned as part of the resulting list.  If `maxsplit` is nonzero, at most `maxsplit` splits occur, and the remainder of the string is returned as the final element of the list.

For more information about this filter, see [`re.split` function documentation](https://docs.python.org/3.11/library/re.html#re.split).

#### Usage:

```jinja
{{ 'Baked Beans And Spam' | regex_split('\sAND\s', flags=RE_IGNORECASE) }}
{# Output: ['Baked Beans', 'Spam'] #}
```

### regex_findall

```python
def regex_findall(
    string: str,
    pattern: str,
    flags: int = 0,
) -> List[Any]
```

Return a list of all non-overlapping matches in the string. If one or more capturing groups are present in the pattern, return a list of groups; this will be a list of tuples if the pattern has more than one group.  Empty matches are included in the result.

For more information about this filter, see [`re.findall` function documentation](https://docs.python.org/3.11/library/re.html#re.findall).

#### Usage:

```jinja
{{ 'which foot or hand fell fastest' | regex_findall('f[a-z]*', flags=RE_IGNORECASE) }}
{# Output: ['foot', 'fell', 'fastest'] #}
```

### regex_finditer

```python
def regex_finditer(
    string: str,
    pattern: str,
    flags: int = 0,
) -> Iterator[re.Match[str]]
```

Return an iterator yielding `Match` objects over all non-overlapping matches for the RE pattern in string.

For more information about this filter, see [`re.finditer` function documentation](https://docs.python.org/3.11/library/re.html#re.finditer).

#### Usage:

```jinja
{% for match in 'which foot or hand fell fastest' | regex_finditer('f[a-z]*', flags=RE_IGNORECASE) %}
match -> {{ match.group() }}
{% endfor %}
{# Output:
match -> foot
match -> fell
match -> fastest
#}
```


### shape_from_footprint

```python
def shape_from_footprint(
    footprint: List[float],
    rounding: int = 6,
) -> BaseGeometry
```

Create a shape from a list of coordinates representing a footprint.

#### Usage:

```jinja
{% set fp = [40.64479480422486, 115.81682739339685, 40.65079881136531, 117.1154430676197, 39.66155122739065, 117.11377991452629, 39.655752572676114, 115.83386830444628, 40.64479480422486, 115.81682739339685] %}
{% set shape = fp | shape_from_footprint %}
"geometry": {{ shape | tojson }}
{# Output:
"geometry": {"coordinates": [[[115.81682699999999, 40.644795], [115.833868, 39.655753], [117.11378000000002, 39.661551], [117.11544300000003, 40.650799], [115.81682699999999, 40.644795]]], "type": "Polygon"}
#}
```


### bbox

```python
def bbox(
    geo_json: Dict[str, Any] | BaseGeometry,
) -> List[float]
```

"Calculates a GeoJSON-spec conforming bounding box for a GeoJSON shape.

#### Usage:

```jinja
{% set poly = {"coordinates": [[[115.81682699999999, 40.644795], [115.833868, 39.655753], [117.11378000000002, 39.661551], [117.11544300000003, 40.650799], [115.81682699999999, 40.644795]]], "type": "Polygon"} %}
"bbox": {{ poly | bbox | tojson }}
{# Output: "bbox": [115.81682699999999, 39.655753, 117.11544300000003, 40.650799] #}
```

### tojson

```python
def tojson(
    eval_ctx: jinja2.nodes.EvalContext,
    obj: Any,
    indent: int | None = None,
) -> Markup:
```

Serialize `obj` to a JSON formatted `str`.

#### Usage:

```jinja
{% set obj = {"foo": "bar", "baz": 123} %}
{{ obj | tojson }}
{# Output: {"foo": "bar", "baz": 123} #}
```

### centroid

```python
def centroid(
    geo_json: Dict[str, Any] | BaseGeometry,
) -> Point
```

Calculates the centroid for a polygon or multipolygon.

#### Usage:

```jinja
{% set poly = {"coordinates": [[[115.81682699999999, 40.644795], [115.833868, 39.655753], [117.11378000000002, 39.661551], [117.11544300000003, 40.650799], [115.81682699999999, 40.644795]]], "type": "Polygon"} %}
{{ poly | centroid | tojson }}
{# Output: {"coordinates": [116.46998328000785, 40.15442045493268], "type": "Point"} #}
```

### simplify

```python
def simplify(
    geometry: Dict[str, Any] | BaseGeometry,
    tolerance: float,
    preserve_topology: bool = True,
) -> BaseGeometry
```

Returns a simplified version of an input geometry using the Douglas-Peucker algorithm.

#### Usage:

```jinja
{% set poly = {"coordinates": [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]], "holes": [[[2, 2], [2, 4], [4, 4], [4, 2], [2, 2]]], "type": "Polygon"} %}
{{ poly | simplify(0.9) | tojson }}
{# Output: {"coordinates": [[[0.0, 0.0], [0.0, 10.0], [10.0, 10.0], [10.0, 0.0], [0.0, 0.0]]], "type": "Polygon"} #}
```

### transform

```python
def transform(
    geometry: Dict[str, Any] | BaseGeometry,
    src_crs: str | int,
    dst_crs: str | int,
    precision: int = -1,
) -> BaseGeometry
```

Transform a geometry from source coordinate reference system into target.

#### Usage:

```jinja
{% set poly = {"coordinates": [[[0, 0], [1, 1], [1, 0], [0,1], [0, 0]]], "type": "Polygon"} %}
{{ poly | transform('EPSG:32633', 'EPSG:4326') | tojson }}
{# Output: {"coordinates": [[[10.511256115612781, 0.0], [10.511256115612724, 9.019375809373756e-06], [10.511265074609526, 0.0], [10.511265074609469, 9.01937592083914e-06], [10.511256115612781, 0.0]]], "type": "Polygon"} #}
```

### projection_info

```python
def projection_info(
  dataset: rasterio.DatasetReader,
) -> Dict
```

Get projection metadata.

The STAC projection extension allows for three different ways to describe the coordinate reference system associated with a raster :
* EPSG code
* WKT2
* PROJJSON

All are optional, and they can be provided altogether as well. Therefore, as long as one can be obtained from the data, we add it to the returned dictionary.

See: https://github.com/stac-extensions/projection

#### Usage:

```jinja
{%- set dataset = get_rasterio_dataset(scene_info) %}
"properties": {
{%- with projection = dataset | projection_info %}
    "proj:epsg": {{ projection.epsg }},
    "proj:geometry": {{ projection.geometry | tojson }},
    "proj:bbox": {{ projection.bbox | tojson }},
    "proj:shape": {{ projection.shape | tojson }},
    "proj:projjson": {{ projection.projjson | tojson }},
    "proj:wkt2": "{{ projection.wkt2.replace('"', '\\"') }}"
{%- endwith %}
}
```

### geometry_info

```python
def geometry_info(
    dataset: rasterio.DatasetReader,
    densify_pts: int = 0,
    precision: int = -1,
) -> Dict
```

Get Raster Footprint.

#### Usage:

```jinja
{%- set dataset = get_rasterio_dataset(scene_info) %}
{%- with geom = dataset | geometry_info %}
  "geometry": {{ geom.footprint | tojson }},
  "bbox": {{ geom.bbox | tojson }},
{%- endwith %}
```

### raster_info

```python
def raster_info(
    dataset: rasterio.DatasetReader,
    max_size: int = 1024,
) -> List[Dict]
```

Get raster metadata.
See: https://github.com/stac-extensions/raster#raster-band-object

#### Usage:

```jinja
{%- set dataset = get_rasterio_dataset(scene_info) %}
"assets": {
  "image": {
    "raster:bands": {{ dataset | raster_info | tojson }}
  }
}
```

### eo_bands_info

```python
def eo_bands_info(
  dataset: rasterio.DatasetReader,
) -> List[Dict]
```

Get eo:bands metadata.
See: https://github.com/stac-extensions/eo#item-properties-or-asset-fields

#### Usage:

```jinja
{%- set dataset = get_rasterio_dataset(scene_info) %}
"assets": {
  "image": {
    "eo:bands": {{ dataset | eo_bands_info | tojson }}
  }
}
```

## Tests

STACForge provides the following tests:

### starts_with

```python
def starts_with(
  string: str,
  prefix: str,
) -> bool
```

Return `True` if the string starts with the prefix, `False` otherwise.

#### Usage:

```jinja
{{ 'which foot or hand fell fastest'.split(' ') | select('starts_with', 'f') | join(' ') }}
{# Output: foot fell fastest #}
```

### ends_with

```python
def ends_with(
  string: str,
  suffix: str,
) -> bool
```

Return `True` if the string ends with the suffix, `False` otherwise.

#### Usage:

```jinja
{{ 'which foot or hand fell fastest'.split(' ') | select('ends_with', 't') | join(' ') }}
{# Output: foot fastest #}
```

### contains

```python
def contains(
  string: str,
  substring: str,
) -> bool
```

Return `True` if the string contains the substring, `False` otherwise.

#### Usage:

```jinja
{{ 'which foot or hand fell fastest'.split(' ') | select('contains', 'and') | join(' ') }}
{# Output: hand #}
```
