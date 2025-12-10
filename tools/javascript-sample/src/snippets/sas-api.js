/**
 * SAS Token API - Download data using signed URLs
 * 
 * Get temporary SAS tokens to download asset files directly from Azure Blob Storage.
 */

import { config } from './config.js';

/**
 * Get a SAS token for a collection
 * Returns a token that can be appended to asset URLs for download access.
 */
export async function getCollectionSasToken(accessToken, collectionId) {
  const url = `${config.catalogUrl}/sas/token/${collectionId}?api-version=${config.apiVersion}`;
  
  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to get SAS token: ${response.status} ${response.statusText} - ${errorText}`);
  }
  
  const data = await response.json();
  return data.token; // The SAS token string
}

/**
 * Build a signed URL for an asset using the SAS token
 * The asset href from the STAC item + the SAS token = downloadable URL
 */
export function buildSignedAssetUrl(assetHref, sasToken) {
  // Strip leading ? from SAS token if present
  const cleanToken = sasToken.startsWith('?') ? sasToken.slice(1) : sasToken;
  
  // If the asset URL already has query params, append with &
  // Otherwise append with ?
  const separator = assetHref.includes('?') ? '&' : '?';
  return `${assetHref}${separator}${cleanToken}`;
}

/**
 * Download a file using the signed URL
 * Triggers a browser download of the file
 */
export function downloadFile(signedUrl, filename) {
  const link = document.createElement('a');
  link.href = signedUrl;
  link.download = filename || 'download';
  link.target = '_blank'; // Open in new tab as fallback
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

/**
 * Get asset information from a STAC item
 * Returns an array of { name, href, type, size } objects
 */
export function getAssetInfo(item) {
  if (!item.assets) return [];
  
  return Object.entries(item.assets).map(([name, asset]) => ({
    name,
    href: asset.href,
    type: asset.type || 'unknown',
    title: asset.title || name,
    size: asset['file:size'] || null,
  }));
}
