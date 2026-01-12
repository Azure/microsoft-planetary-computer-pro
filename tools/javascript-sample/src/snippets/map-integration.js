/**
 * Map Integration
 * 
 * MapLibre GL integration with authorization headers for tile requests.
 * See: https://learn.microsoft.com/azure/planetary-computer/build-web-application
 */

import maplibregl from 'maplibre-gl';

let currentAccessToken = null;

/**
 * Initialize map with transformRequest for auth headers - exact pattern from Step 7
 */
export function initializeMap(containerId, accessToken) {
  currentAccessToken = accessToken;
  
  const map = new maplibregl.Map({
    container: containerId,
    style: {
      version: 8,
      sources: {
        osm: {
          type: 'raster',
          tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
          tileSize: 256,
          attribution: '© OpenStreetMap contributors',
        },
      },
      layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
    },
    center: [-98, 39],
    zoom: 4,
    transformRequest: (url, resourceType) => {
      if (url.includes('geocatalog.spatio.azure.com') && currentAccessToken) {
        return {
          url,
          headers: { 'Authorization': `Bearer ${currentAccessToken}` },
        };
      }
      return { url };
    },
  });
  
  map.addControl(new maplibregl.NavigationControl(), 'top-right');
  
  return map;
}

/**
 * Update the access token used by transformRequest.
 */
export function updateAccessToken(token) {
  currentAccessToken = token;
}

/**
 * Add a tile layer to the map - exact pattern from Step 7
 */
export function addTileLayer(map, tileUrl, bounds) {
  if (map.getLayer('data-layer')) {
    map.removeLayer('data-layer');
  }
  if (map.getSource('data-tiles')) {
    map.removeSource('data-tiles');
  }
  
  map.addSource('data-tiles', {
    type: 'raster',
    tiles: [tileUrl],
    tileSize: 256,
    minzoom: 0,
    maxzoom: 18,
  });
  
  map.addLayer({
    id: 'data-layer',
    type: 'raster',
    source: 'data-tiles',
    paint: {
      'raster-opacity': 0.9,
    },
  });
  
  if (bounds && bounds.length === 4) {
    const isWorldBounds = 
      bounds[0] <= -179 && bounds[1] <= -89 && 
      bounds[2] >= 179 && bounds[3] >= 89;
    
    if (!isWorldBounds) {
      map.fitBounds(
        [[bounds[0], bounds[1]], [bounds[2], bounds[3]]], 
        { padding: 50, maxZoom: 14 }
      );
    }
  }
}

/**
 * Remove the data tile layer from the map.
 */
export function removeTileLayer(map) {
  if (map.getLayer('data-layer')) {
    map.removeLayer('data-layer');
  }
  if (map.getSource('data-tiles')) {
    map.removeSource('data-tiles');
  }
}
