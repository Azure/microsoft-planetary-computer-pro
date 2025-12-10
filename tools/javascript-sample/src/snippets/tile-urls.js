/**
 * Tile URL Functions
 * 
 * Build tile URLs for map visualization.
 * See: https://learn.microsoft.com/azure/planetary-computer/build-web-application
 */

import { config } from './config.js';

/**
 * Build a tile URL template for a STAC item - exact pattern from Step 6
 * Returns a URL with {z}/{x}/{y} placeholders for use with map libraries.
 */
export function buildTileUrl(collectionId, itemId, options = {}) {
  const { assets = 'visual', colormap, rescale, asset_bidx } = options;
  
  const base = `${config.catalogUrl}/data/collections/${collectionId}/items/${itemId}/tiles/{z}/{x}/{y}@1x.png`;
  
  const params = new URLSearchParams();
  params.set('api-version', config.apiVersion);
  params.set('tileMatrixSetId', 'WebMercatorQuad');
  params.set('assets', assets);
  
  if (colormap) params.set('colormap_name', colormap);
  if (rescale) params.set('rescale', rescale);
  if (asset_bidx) params.set('asset_bidx', asset_bidx);
  
  return `${base}?${params.toString()}`;
}

/**
 * Register a mosaic search for a collection - exact pattern from Step 8
 * Returns a search ID that can be used to fetch mosaic tiles.
 */
export async function registerMosaic(collectionId, accessToken) {
  const url = `${config.catalogUrl}/data/mosaic/register?api-version=${config.apiVersion}`;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      collections: [collectionId],
    }),
  });
  
  if (!response.ok) {
    throw new Error(`Failed to register mosaic: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data.searchid;
}

/**
 * Build a mosaic tile URL template - exact pattern from Step 8
 */
export function buildMosaicTileUrl(searchId, collectionId, options = {}) {
  const { assets = 'visual' } = options;
  
  const base = `${config.catalogUrl}/data/mosaic/${searchId}/tiles/{z}/{x}/{y}@1x.png`;
  
  const params = new URLSearchParams();
  params.set('api-version', config.apiVersion);
  params.set('tileMatrixSetId', 'WebMercatorQuad');
  params.set('collection', collectionId);
  params.set('assets', assets);
  
  return `${base}?${params.toString()}`;
}
