"""
geoai.public.aoi_constraint

Constraint class for AOI-based models (EO-OS, MARS).
"""

import logging
import os
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Union

from geoai.public.constraint import BaseConstraint

if TYPE_CHECKING:
    import geopandas

logger = logging.getLogger(__name__)


class Constraint(BaseConstraint):
    """
    Constraint - Spatial/temporal constraints for AOI-based models.

    Supports three modes:
    1. **Simple constraints**: Use bbox, geometry, or aois
    2. **Multi-AOI**: Use aois (GeoParquet file or GeoDataFrame)
    3. **STAC pass-through**: Use stac_search (pre-built pystac_client search)

    Examples:
        >>> # Single AOI with bbox
        >>> constraint = Constraint(
        ...     bbox=[-122.5, 37.5, -122.0, 38.0],
        ...     datetime="2024-01-01/2024-12-31"
        ... )
        >>>
        >>> # Single AOI with GeoJSON geometry
        >>> constraint = Constraint(
        ...     geometry={"type": "Polygon", "coordinates": [[...]]},
        ...     datetime="2024-01-01/2024-12-31"
        ... )
        >>>
        >>> # Multi-AOI with GeoParquet file
        >>> constraint = Constraint(
        ...     aois="buildings.geoparquet",  # 100 building footprints
        ...     datetime="2024-01-01/2024-12-31"
        ... )
        >>>
        >>> # Multi-AOI with GeoDataFrame
        >>> import geopandas as gpd
        >>> gdf = gpd.read_file("parcels.geojson")
        >>> constraint = Constraint(
        ...     aois=gdf,  # GeoDataFrame with multiple polygons
        ...     datetime="2024-01-01/2024-12-31"
        ... )
        >>>
        >>> # STAC pass-through (advanced) - for full control over STAC query
        >>> import pystac_client
        >>> # Build custom search with sorting, limiting, complex filters
        >>> search = pystac_client.Client.open("https://...").search(
        ...     collections=["naip"],
        ...     bbox=[-118.5, 33.9, -118.3, 34.1],  # Search large area
        ...     datetime="2020-01-01/2023-12-31",
        ...     query={"eo:cloud_cover": {"lt": 10}},
        ...     sortby=[{"field": "properties.datetime", "direction": "desc"}],  # Latest first
        ...     limit=50  # Only best 50 items
        ... )
        >>> # Reuse same search for multiple AOIs (efficient!)
        >>> constraint = Constraint(aois="buildings.geoparquet", stac_search=search)
    """

    def __init__(
        self,
        bbox: Optional[List[float]] = None,
        geometry: Optional[Dict] = None,
        aois: Optional[Union[str, "geopandas.GeoDataFrame"]] = None,
        datetime: Optional[str] = None,
        filter: Optional[Dict] = None,
        stac_search: Optional[Any] = None,
    ):
        """
        Initialize Constraint.

        :param bbox: Bounding box [minx, miny, maxx, maxy] in WGS84 (single AOI)
        :param geometry: GeoJSON geometry (single AOI)
        :param aois: GeoParquet file path or GeoDataFrame (multi-AOI)
        :param datetime: ISO 8601 datetime or range (e.g., "2024-01-01/2024-12-31")
        :param filter: CQL2 filter dict (e.g., {"eo:cloud_cover": {"lte": 20}})
        :param stac_search: Pre-built pystac_client.ItemSearch (advanced - for sorting, limiting, complex filters)

        Note:
        - AOI is always required (bbox, geometry, or aois)
        - When stac_search provided: datetime/filter ignored, search results used for all AOIs
        - Multi-AOI + stac_search: AOIs without intersecting items are skipped with warning

        :raises ValueError: If parameters are invalid or conflicting
        """
        super().__init__()

        # STAC pass-through mode requires geometry for chip creation
        if stac_search is not None:
            # Require bbox or geometry even in pass-through mode
            mode_count = sum([bbox is not None, geometry is not None, aois is not None])

            if mode_count == 0:
                raise ValueError(
                    "stac_search requires bbox or geometry for chip creation. "
                    "Example: Constraint(stac_search=search, bbox=[...])"
                )

            if mode_count > 1:
                raise ValueError("Provide only ONE of: bbox, geometry, or aois (with stac_search)")

            self.stac_search = stac_search

            # Set up geometry for chipping
            if bbox is not None:
                self.geometry = self._bbox_to_geometry(bbox)
                self.bbox = bbox
                self.aois = None
                self._mode = "single"
            elif geometry is not None:
                self.geometry = geometry
                self.bbox = self._geometry_to_bbox(geometry)
                self.aois = None
                self._mode = "single"
            elif aois is not None:
                self.geometry = None
                self.bbox = None
                self.aois = self._load_aois(aois)
                self._mode = "multi"

            # datetime and filter are ignored when stac_search is provided
            self.datetime = None
            self.filter = {}

            logger.info("STAC pass-through mode: using pre-built search, ignoring datetime/filter")
            self.validate()
            return

        # Normal mode (no STAC pass-through)
        # Determine mode: single vs multi-AOI
        mode_count = sum([bbox is not None, geometry is not None, aois is not None])

        if mode_count == 0:
            raise ValueError("Must provide bbox, geometry, aois, or stac_search")

        if mode_count > 1:
            raise ValueError("Provide only ONE of: bbox, geometry, aois, or stac_search")

        self.stac_search = None

        # Single AOI mode
        if bbox is not None:
            self.geometry = self._bbox_to_geometry(bbox)
            self.bbox = bbox
            self.aois = None
            self._mode = "single"
        elif geometry is not None:
            self.geometry = geometry
            self.bbox = self._geometry_to_bbox(geometry)
            self.aois = None
            self._mode = "single"
        # Multi-AOI mode
        elif aois is not None:
            self.geometry = None  # No single geometry in multi-AOI mode
            self.bbox = None
            self.aois = self._load_aois(aois)
            self._mode = "multi"

        self.datetime = datetime
        self.filter = filter or {}

        self.validate()

    @property
    def mode(self) -> str:
        """
        Get constraint mode: 'single' or 'multi'.

        :return: 'single' for single AOI, 'multi' for multiple AOIs
        """
        return self._mode

    def _load_aois(self, aois: Union[str, "geopandas.GeoDataFrame"]) -> List[Dict]:
        """
        Load multiple AOIs from GeoParquet file or GeoDataFrame.

        :param aois: GeoParquet file path or GeoDataFrame
        :return: List of AOI dictionaries with id, bbox, geometry, and properties
        """
        import geopandas as gpd

        from geoai.core.spatial.geometry_utils import geometry_to_bbox

        # Load GeoDataFrame
        if isinstance(aois, str):
            # File path (GeoParquet or GeoJSON)
            if not os.path.exists(aois):
                raise FileNotFoundError(f"AOI file not found: {aois}")

            try:
                # Use read_parquet for .parquet/.geoparquet files
                if aois.lower().endswith((".parquet", ".geoparquet")):
                    gdf = gpd.read_parquet(aois)
                else:
                    gdf = gpd.read_file(aois)
            except Exception as e:
                raise ValueError(f"Failed to read AOI file {aois}: {e}")
        elif hasattr(aois, "geometry"):  # GeoDataFrame
            gdf = aois
        else:
            raise TypeError(f"aois must be str (file path) or GeoDataFrame, got {type(aois)}")

        if gdf.empty:
            raise ValueError("AOI dataset is empty")

        # Ensure WGS84 (EPSG:4326)
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)

        # Convert to list of AOI dicts
        aoi_list = []
        for idx, row in gdf.iterrows():
            geom = row.geometry

            if geom is None or geom.is_empty:
                continue

            # Convert to GeoJSON
            geom_json = geom.__geo_interface__

            # Extract bbox
            bbox = list(geom.bounds)  # (minx, miny, maxx, maxy)

            # Extract properties (exclude geometry column)
            properties = {}
            for col in gdf.columns:
                if col != gdf.geometry.name:
                    val = row[col]
                    # Convert numpy types to Python types
                    if hasattr(val, "item"):
                        val = val.item()
                    properties[col] = val

            # Create AOI dict
            aoi_dict = {
                "id": f"aoi_{idx}",  # Default ID
                "bbox": bbox,
                "geometry": geom_json,
                "properties": properties,
            }

            # Use 'id' column if exists
            if "id" in properties:
                aoi_dict["id"] = str(properties["id"])
            elif "name" in properties:
                aoi_dict["id"] = str(properties["name"])

            aoi_list.append(aoi_dict)

        if not aoi_list:
            raise ValueError("No valid geometries found in AOI dataset")

        return aoi_list

    def iter_aois(self) -> Iterator[Dict]:
        """
        Iterate over AOIs.

        For single AOI mode, yields one AOI.
        For multi-AOI mode, yields each AOI.

        :yield: AOI dict with id, bbox, geometry, and properties

        Example:
            >>> for aoi in constraint.iter_aois():
            ...     print(f"Processing {aoi['id']}")
            ...     # Process this AOI
        """
        if self._mode == "single":
            # Single AOI - yield once
            yield {"id": "aoi_0", "bbox": self.bbox, "geometry": self.geometry, "properties": {}}
        else:
            # Multi-AOI - yield each
            for aoi in self.aois:
                yield aoi

    def _bbox_to_geometry(self, bbox: List[float]) -> Dict:
        """Convert bounding box to GeoJSON Polygon"""
        if len(bbox) != 4:
            raise ValueError("bbox must be [minx, miny, maxx, maxy]")

        minx, miny, maxx, maxy = bbox

        return {
            "type": "Polygon",
            "coordinates": [[[minx, miny], [maxx, miny], [maxx, maxy], [minx, maxy], [minx, miny]]],
        }

    def _geometry_to_bbox(self, geometry: Dict) -> List[float]:
        """Extract bounding box from GeoJSON geometry"""
        from shapely.geometry import shape

        geom = shape(geometry)
        return list(geom.bounds)

    def validate(self):
        """
        Validate constraint parameters.

        :raises ValueError: If parameters are invalid
        """
        if self._mode == "single":
            # Validate single AOI bbox
            if self.bbox:
                minx, miny, maxx, maxy = self.bbox
                if minx >= maxx:
                    raise ValueError(f"bbox: minx ({minx}) must be < maxx ({maxx})")
                if miny >= maxy:
                    raise ValueError(f"bbox: miny ({miny}) must be < maxy ({maxy})")
                if not (-180 <= minx <= 180) or not (-180 <= maxx <= 180):
                    raise ValueError(f"bbox: longitude must be in range [-180, 180]")
                if not (-90 <= miny <= 90) or not (-90 <= maxy <= 90):
                    raise ValueError(f"bbox: latitude must be in range [-90, 90]")
        else:
            # Validate multi-AOI
            if not self.aois or len(self.aois) == 0:
                raise ValueError("Multi-AOI mode requires at least one AOI")

            # Validate each AOI bbox
            for aoi in self.aois:
                minx, miny, maxx, maxy = aoi["bbox"]
                if minx >= maxx or miny >= maxy:
                    raise ValueError(f"Invalid bbox for AOI {aoi['id']}: {aoi['bbox']}")

    def __repr__(self):
        if self._mode == "single":
            return (
                f"Constraint(bbox={self.bbox}, "
                f"datetime='{self.datetime}', "
                f"filter={self.filter})"
            )
        else:
            return (
                f"Constraint(aois={len(self.aois)} AOIs, "
                f"datetime='{self.datetime}', "
                f"filter={self.filter})"
            )


# Alias for backward compatibility
AOIConstraint = Constraint
