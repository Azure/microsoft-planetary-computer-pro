/**
 * STAC API Functions
 * 
 * Query collections, items, and search the GeoCatalog.
 * See: https://learn.microsoft.com/azure/planetary-computer/build-web-application
 */

import { config } from './config.js';

/**
 * List collections - exact pattern from Step 5
 */
export async function listCollections(accessToken) {
  const url = `${config.catalogUrl}/stac/collections?api-version=${config.apiVersion}`;
  
  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  });
  
  if (!response.ok) {
    throw new Error(`Failed to list collections: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data.collections;
}

/**
 * List items in a collection - exact pattern from Step 5
 */
export async function listItems(accessToken, collectionId, limit = 10) {
  const url = `${config.catalogUrl}/stac/collections/${collectionId}/items?limit=${limit}&api-version=${config.apiVersion}`;
  
  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  });
  
  if (!response.ok) {
    throw new Error(`Failed to list items: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data.features;
}

/**
 * Search across collections - exact pattern from Step 5
 */
export async function searchItems(accessToken, searchParams) {
  const url = `${config.catalogUrl}/stac/search?api-version=${config.apiVersion}`;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(searchParams),
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Search failed: ${response.status} - ${errorText}`);
  }
  
  return await response.json();
}

/**
 * Get a single item by ID
 */
export async function getItem(accessToken, collectionId, itemId) {
  const url = `${config.catalogUrl}/stac/collections/${collectionId}/items/${itemId}?api-version=${config.apiVersion}`;
  
  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  });
  
  if (!response.ok) {
    throw new Error(`Failed to get item: ${response.statusText}`);
  }
  
  return await response.json();
}
