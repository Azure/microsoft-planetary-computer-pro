/**
 * GeoCatalog Code Samples
 * 
 * Sample web application demonstrating GeoCatalog API integration.
 * See: https://learn.microsoft.com/azure/planetary-computer/build-web-application
 */

import { config } from './snippets/config.js';
import { initAuth, login, logout, getAccessToken, isAuthenticated, getAccount } from './snippets/auth.js';
import { listCollections, listItems, searchItems } from './snippets/stac-api.js';
import { buildTileUrl, buildMosaicTileUrl, registerMosaic } from './snippets/tile-urls.js';
import { initializeMap, addTileLayer, updateAccessToken } from './snippets/map-integration.js';
import { getCollectionSasToken, buildSignedAssetUrl, downloadFile, getAssetInfo } from './snippets/sas-api.js';
import maplibregl from 'maplibre-gl';

// State
let map = null;
let searchMap = null;
let collections = [];
let items = [];
let tileItems = [];
let sasItems = [];
let currentSasToken = null;
let currentAssetUrl = null;

// DOM helper
const $ = (id) => document.getElementById(id);

// Tab-specific logging
function log(tabId, message, type = 'info') {
  const output = $(`output-${tabId}`);
  if (!output) return;
  
  const entry = document.createElement('div');
  entry.className = `log-entry ${type}`;
  entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
  output.appendChild(entry);
  output.scrollTop = output.scrollHeight;
  console.log(`[${tabId}][${type.toUpperCase()}]`, message);
}

// Tab switching
function initTabs() {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      // Update tab styles
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      
      // Update content visibility
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      $(`tab-${tab.dataset.tab}`).classList.add('active');
      
      // Initialize map when tiles tab is shown
      if (tab.dataset.tab === 'tiles' && !map) {
        initMap();
      }
      
      // Initialize search map when search tab is shown
      if (tab.dataset.tab === 'search' && !searchMap) {
        initSearchMap();
      }
      
      // Update auth warnings on other tabs
      updateAuthWarnings();
    });
  });
}

function updateAuthWarnings() {
  const authenticated = isAuthenticated();
  $('stac-auth-warning').style.display = authenticated ? 'none' : 'block';
  $('tiles-auth-warning').style.display = authenticated ? 'none' : 'block';
  $('sas-auth-warning').style.display = authenticated ? 'none' : 'block';
  $('search-auth-warning').style.display = authenticated ? 'none' : 'block';
  
  // Enable/disable buttons based on auth
  $('btn-list-collections').disabled = !authenticated;
  
  // Sync collection selects
  if (collections.length > 0 && authenticated) {
    syncCollectionSelects();
  }
}

function syncCollectionSelects() {
  // Sync tile, sas, and search collection selects with stac collection select
  const tileSelect = $('tile-collection-select');
  const sasSelect = $('sas-collection-select');
  const searchSelect = $('search-collection-select');
  const stacSelect = $('collection-select');
  
  if (collections.length > 0) {
    tileSelect.innerHTML = stacSelect.innerHTML;
    tileSelect.disabled = false;
    sasSelect.innerHTML = stacSelect.innerHTML;
    sasSelect.disabled = false;
    searchSelect.innerHTML = stacSelect.innerHTML;
    searchSelect.disabled = false;
  }
}

// ========== Tab 1: MSAL Authentication ==========

function updateAuthUI() {
  const status = $('auth-status');
  const userInfo = $('user-info');
  
  if (isAuthenticated()) {
    const account = getAccount();
    status.textContent = '✓ Successfully authenticated';
    status.className = 'status success';
    
    // Show user info
    userInfo.style.display = 'flex';
    $('user-name').textContent = account.name || 'User';
    $('user-email').textContent = account.username || '';
    $('user-avatar').textContent = (account.name || 'U').charAt(0).toUpperCase();
    
    $('btn-login').disabled = true;
    $('btn-logout').disabled = false;
  } else {
    status.textContent = 'Click "Login with Microsoft" to authenticate';
    status.className = 'status info';
    userInfo.style.display = 'none';
    
    $('btn-login').disabled = false;
    $('btn-logout').disabled = true;
  }
  
  updateAuthWarnings();
}

async function handleLogin() {
  try {
    log('auth', 'Redirecting to Microsoft login...', 'info');
    await login();
    // Note: login() redirects away, so code below won't execute
    // Auth state is restored when page reloads via initAuth()
  } catch (error) {
    log('auth', `Login failed: ${error.message}`, 'error');
  }
}

async function handleLogout() {
  try {
    await logout();
    log('auth', 'Logged out successfully', 'info');
    collections = [];
    items = [];
    tileItems = [];
    
    // Reset all selects
    $('collection-select').innerHTML = '<option value="">-- Select a collection --</option>';
    $('tile-collection-select').innerHTML = '<option value="">-- Select a collection --</option>';
    $('tile-item-select').innerHTML = '<option value="">-- Select an item --</option>';
    
    updateAuthUI();
  } catch (error) {
    log('auth', `Logout failed: ${error.message}`, 'error');
  }
}

// ========== Tab 2: STAC API ==========

async function handleListCollections() {
  if (!isAuthenticated()) return;
  
  try {
    log('stac', 'Fetching collections...', 'info');
    const token = await getAccessToken();
    
    collections = await listCollections(token);
    
    const select = $('collection-select');
    select.innerHTML = '<option value="">-- Select a collection --</option>';
    collections.forEach(c => {
      const option = document.createElement('option');
      option.value = c.id;
      option.textContent = c.title || c.id;
      select.appendChild(option);
    });
    select.disabled = false;
    
    log('stac', `Found ${collections.length} collections`, 'success');
    
    // Sync to tiles tab
    syncCollectionSelects();
    
    updateStacButtons();
  } catch (error) {
    log('stac', `Failed: ${error.message}`, 'error');
  }
}

async function handleListItems() {
  const collectionId = $('collection-select').value;
  if (!collectionId || !isAuthenticated()) return;
  
  try {
    log('stac', `Fetching items from ${collectionId}...`, 'info');
    const token = await getAccessToken();
    
    items = await listItems(token, collectionId, 10);
    
    displayItemsTable(items);
    log('stac', `Found ${items.length} items`, 'success');
    updateStacButtons();
  } catch (error) {
    log('stac', `Failed: ${error.message}`, 'error');
  }
}

function displayItemsTable(itemList) {
  const table = $('results-table');
  const tbody = $('results-body');
  
  if (itemList.length === 0) {
    table.style.display = 'none';
    return;
  }
  
  tbody.innerHTML = '';
  itemList.forEach(item => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${item.id}</td>
      <td>${item.properties?.datetime || 'N/A'}</td>
      <td>${item.bbox ? item.bbox.map(n => n.toFixed(2)).join(', ') : 'N/A'}</td>
    `;
    tbody.appendChild(tr);
  });
  
  table.style.display = 'table';
}

function updateStacButtons() {
  const hasCollection = $('collection-select').value !== '';
  $('btn-list-items').disabled = !hasCollection;
}

// ========== Tab 3: STAC Search ==========

function initSearchMap() {
  if (searchMap) return;
  
  searchMap = new maplibregl.Map({
    container: 'search-map',
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
    zoom: 3,
  });
  
  searchMap.addControl(new maplibregl.NavigationControl(), 'top-right');
  
  // Add footprints source and layer (empty initially)
  searchMap.on('load', () => {
    searchMap.addSource('footprints', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    });
    
    // Fill layer for footprints
    searchMap.addLayer({
      id: 'footprints-fill',
      type: 'fill',
      source: 'footprints',
      paint: {
        'fill-color': '#0078d4',
        'fill-opacity': 0.2,
      },
    });
    
    // Outline layer for footprints
    searchMap.addLayer({
      id: 'footprints-outline',
      type: 'line',
      source: 'footprints',
      paint: {
        'line-color': '#0078d4',
        'line-width': 2,
      },
    });
    
    // Add bbox source and layer
    searchMap.addSource('search-bbox', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    });
    
    searchMap.addLayer({
      id: 'search-bbox-outline',
      type: 'line',
      source: 'search-bbox',
      paint: {
        'line-color': '#ff6600',
        'line-width': 3,
        'line-dasharray': [3, 2],
      },
    });
    
    // Add popup on click
    searchMap.on('click', 'footprints-fill', (e) => {
      if (e.features.length > 0) {
        const feature = e.features[0];
        const props = feature.properties;
        new maplibregl.Popup()
          .setLngLat(e.lngLat)
          .setHTML(`<strong>${props.id}</strong><br>${props.datetime || 'No date'}`)
          .addTo(searchMap);
      }
    });
    
    // Highlight on map hover - sync with list
    searchMap.on('mouseenter', 'footprints-fill', (e) => {
      searchMap.getCanvas().style.cursor = 'pointer';
      if (e.features.length > 0) {
        const itemId = e.features[0].properties.id;
        highlightFootprint(itemId);
        // Highlight corresponding list item
        document.querySelectorAll('.result-item').forEach(el => {
          el.classList.toggle('highlighted', el.dataset.id === itemId);
        });
      }
    });
    
    searchMap.on('mouseleave', 'footprints-fill', () => {
      searchMap.getCanvas().style.cursor = '';
      clearFootprintHighlight();
      document.querySelectorAll('.result-item').forEach(el => el.classList.remove('highlighted'));
    });
  });
  
  log('search', 'Search map initialized', 'success');
}

function handleUseMapBounds() {
  if (!searchMap) return;
  
  const bounds = searchMap.getBounds();
  $('bbox-west').value = bounds.getWest().toFixed(4);
  $('bbox-south').value = bounds.getSouth().toFixed(4);
  $('bbox-east').value = bounds.getEast().toFixed(4);
  $('bbox-north').value = bounds.getNorth().toFixed(4);
  
  updateSearchBboxLayer();
  updateSearchButtons();
  log('search', 'Bbox set from map bounds', 'info');
}

function updateSearchBboxLayer() {
  if (!searchMap || !searchMap.getSource('search-bbox')) return;
  
  const west = parseFloat($('bbox-west').value);
  const south = parseFloat($('bbox-south').value);
  const east = parseFloat($('bbox-east').value);
  const north = parseFloat($('bbox-north').value);
  
  if (isNaN(west) || isNaN(south) || isNaN(east) || isNaN(north)) {
    searchMap.getSource('search-bbox').setData({ type: 'FeatureCollection', features: [] });
    return;
  }
  
  const bboxFeature = {
    type: 'Feature',
    geometry: {
      type: 'Polygon',
      coordinates: [[
        [west, south],
        [east, south],
        [east, north],
        [west, north],
        [west, south],
      ]],
    },
  };
  
  searchMap.getSource('search-bbox').setData({
    type: 'FeatureCollection',
    features: [bboxFeature],
  });
}

async function handleSearchExecute() {
  const collectionId = $('search-collection-select').value;
  if (!collectionId || !isAuthenticated()) return;
  
  let west = parseFloat($('bbox-west').value);
  let south = parseFloat($('bbox-south').value);
  let east = parseFloat($('bbox-east').value);
  let north = parseFloat($('bbox-north').value);
  const limit = parseInt($('search-limit').value) || 20;
  
  const searchParams = {
    collections: [collectionId],
    limit,
  };
  
  // Add bbox if valid, clamping to valid ranges
  if (!isNaN(west) && !isNaN(south) && !isNaN(east) && !isNaN(north)) {
    // Clamp to valid WGS84 ranges
    west = Math.max(-180, Math.min(180, west));
    east = Math.max(-180, Math.min(180, east));
    south = Math.max(-90, Math.min(90, south));
    north = Math.max(-90, Math.min(90, north));
    searchParams.bbox = [west, south, east, north];
  }
  
  // Add datetime if set
  const startDate = $('date-start').value;
  const endDate = $('date-end').value;
  if (startDate || endDate) {
    const start = startDate || '..';
    const end = endDate || '..';
    searchParams.datetime = `${start}/${end}`;
  }
  
  try {
    log('search', `Searching ${collectionId}...`, 'info');
    const token = await getAccessToken();
    
    const results = await searchItems(token, searchParams);
    const features = results.features || [];
    
    log('search', `Found ${features.length} items`, 'success');
    
    // Update results count badge
    $('search-count-badge').textContent = features.length;
    
    // Populate results list
    populateResultsList(features);
    
    // Display footprints on map
    displayFootprints(features);
    
    // Fit to results if we have any
    if (features.length > 0 && !searchParams.bbox) {
      fitToFeatures(features);
    }
  } catch (error) {
    log('search', `Search failed: ${error.message}`, 'error');
  }
}

// Store search results for hover highlighting
let searchResults = [];

function populateResultsList(features) {
  const listEl = $('search-results-list');
  searchResults = features;
  
  if (features.length === 0) {
    listEl.innerHTML = '<div class="results-placeholder">No items found</div>';
    return;
  }
  
  listEl.innerHTML = features.map((item, index) => {
    const datetime = item.properties?.datetime;
    const dateStr = datetime ? new Date(datetime).toLocaleDateString() : 'No date';
    return `
      <div class="result-item" data-index="${index}" data-id="${item.id}">
        <span class="item-id">${item.id}</span>
        <span class="item-date">${dateStr}</span>
      </div>
    `;
  }).join('');
  
  // Add hover handlers
  listEl.querySelectorAll('.result-item').forEach(el => {
    el.addEventListener('mouseenter', () => handleResultHover(parseInt(el.dataset.index)));
    el.addEventListener('mouseleave', () => handleResultLeave());
    el.addEventListener('click', () => handleResultClick(parseInt(el.dataset.index)));
  });
}

function handleResultHover(index) {
  const feature = searchResults[index];
  if (!feature || !searchMap) return;
  
  // Highlight this item on the map
  highlightFootprint(feature.id);
  
  // Highlight the list item
  document.querySelectorAll('.result-item').forEach(el => el.classList.remove('highlighted'));
  document.querySelector(`.result-item[data-index="${index}"]`)?.classList.add('highlighted');
}

function handleResultLeave() {
  // Remove highlight
  clearFootprintHighlight();
  document.querySelectorAll('.result-item').forEach(el => el.classList.remove('highlighted'));
}

function handleResultClick(index) {
  const feature = searchResults[index];
  if (!feature || !searchMap) return;
  
  // Zoom to this item
  if (feature.bbox) {
    searchMap.fitBounds([
      [feature.bbox[0], feature.bbox[1]],
      [feature.bbox[2], feature.bbox[3]]
    ], { padding: 50, maxZoom: 14 });
  }
  
  log('search', `Selected: ${feature.id}`, 'info');
}

function highlightFootprint(itemId) {
  if (!searchMap) return;
  
  // Update the paint properties to highlight the hovered item
  searchMap.setPaintProperty('footprints-fill', 'fill-opacity', [
    'case',
    ['==', ['get', 'id'], itemId], 0.5,
    0.15
  ]);
  searchMap.setPaintProperty('footprints-outline', 'line-width', [
    'case',
    ['==', ['get', 'id'], itemId], 4,
    2
  ]);
  searchMap.setPaintProperty('footprints-outline', 'line-color', [
    'case',
    ['==', ['get', 'id'], itemId], '#ff6600',
    '#0078d4'
  ]);
}

function clearFootprintHighlight() {
  if (!searchMap) return;
  
  searchMap.setPaintProperty('footprints-fill', 'fill-opacity', 0.2);
  searchMap.setPaintProperty('footprints-outline', 'line-width', 2);
  searchMap.setPaintProperty('footprints-outline', 'line-color', '#0078d4');
}

function displayFootprints(features) {
  if (!searchMap || !searchMap.getSource('footprints')) return;
  
  // Convert STAC items to GeoJSON with properties for popup
  const geojson = {
    type: 'FeatureCollection',
    features: features.map(item => ({
      type: 'Feature',
      geometry: item.geometry,
      properties: {
        id: item.id,
        datetime: item.properties?.datetime || null,
        collection: item.collection,
      },
    })),
  };
  
  searchMap.getSource('footprints').setData(geojson);
}

function fitToFeatures(features) {
  if (!searchMap || features.length === 0) return;
  
  // Calculate bounds from all features
  let minLng = 180, minLat = 90, maxLng = -180, maxLat = -90;
  
  features.forEach(item => {
    if (item.bbox) {
      minLng = Math.min(minLng, item.bbox[0]);
      minLat = Math.min(minLat, item.bbox[1]);
      maxLng = Math.max(maxLng, item.bbox[2]);
      maxLat = Math.max(maxLat, item.bbox[3]);
    }
  });
  
  if (minLng < maxLng && minLat < maxLat) {
    searchMap.fitBounds([[minLng, minLat], [maxLng, maxLat]], { padding: 50 });
  }
}

function handleSearchClear() {
  if (searchMap && searchMap.getSource('footprints')) {
    searchMap.getSource('footprints').setData({ type: 'FeatureCollection', features: [] });
  }
  if (searchMap && searchMap.getSource('search-bbox')) {
    searchMap.getSource('search-bbox').setData({ type: 'FeatureCollection', features: [] });
  }
  
  $('bbox-west').value = '';
  $('bbox-south').value = '';
  $('bbox-east').value = '';
  $('bbox-north').value = '';
  $('date-start').value = '';
  $('date-end').value = '';
  
  // Clear results list
  searchResults = [];
  $('search-results-list').innerHTML = '<div class="results-placeholder">Run a search to see results</div>';
  $('search-count-badge').textContent = '';
  
  log('search', 'Results cleared', 'info');
}

function updateSearchButtons() {
  const hasCollection = $('search-collection-select').value !== '';
  $('btn-search-execute').disabled = !hasCollection || !isAuthenticated();
}

// ========== Tab 4: Tile Display ==========

function initMap() {
  if (map) return;
  
  map = initializeMap('map', null); // Will get fresh token when needed
  log('tiles', 'Map initialized', 'success');
}

async function handleTileCollectionChange() {
  const collectionId = $('tile-collection-select').value;
  if (!collectionId || !isAuthenticated()) {
    $('tile-item-select').innerHTML = '<option value="">-- Select an item --</option>';
    $('tile-item-select').disabled = true;
    updateTileButtons();
    return;
  }
  
  try {
    log('tiles', `Loading items from ${collectionId}...`, 'info');
    const token = await getAccessToken();
    
    tileItems = await listItems(token, collectionId, 20);
    
    const select = $('tile-item-select');
    select.innerHTML = '<option value="">-- Select an item --</option>';
    tileItems.forEach(item => {
      const option = document.createElement('option');
      option.value = item.id;
      option.textContent = item.id;
      select.appendChild(option);
    });
    select.disabled = false;
    
    log('tiles', `Found ${tileItems.length} items`, 'success');
    updateTileButtons();
  } catch (error) {
    log('tiles', `Failed to load items: ${error.message}`, 'error');
  }
}

async function handleShowTiles() {
  const collectionId = $('tile-collection-select').value;
  const itemId = $('tile-item-select').value;
  if (!collectionId || !itemId) return;
  
  const item = tileItems.find(i => i.id === itemId);
  if (!item) return;
  
  try {
    log('tiles', `Building tile URL for ${itemId}...`, 'info');
    
    // Find best asset
    const assetNames = Object.keys(item.assets || {});
    const preferred = ['visual', 'rendered_preview', 'image', 'rgb', 'data'];
    const asset = preferred.find(a => assetNames.includes(a)) || assetNames[0];
    log('tiles', `Using asset: ${asset}`, 'info');
    
    // Refresh token
    const token = await getAccessToken();
    updateAccessToken(token);
    
    // Build and display
    const tileUrl = buildTileUrl(collectionId, itemId, { assets: asset });
    log('tiles', `Tile URL built`, 'success');
    
    addTileLayer(map, tileUrl, item.bbox);
    log('tiles', `Tiles displayed on map`, 'success');
  } catch (error) {
    log('tiles', `Failed: ${error.message}`, 'error');
  }
}

async function handleShowMosaic() {
  const collectionId = $('tile-collection-select').value;
  if (!collectionId) return;
  
  try {
    log('tiles', `Registering mosaic for ${collectionId}...`, 'info');
    const token = await getAccessToken();
    
    const searchId = await registerMosaic(collectionId, token);
    log('tiles', `Mosaic registered: ${searchId}`, 'success');
    
    updateAccessToken(token);
    
    const mosaicUrl = buildMosaicTileUrl(searchId, collectionId, { assets: 'visual' });
    log('tiles', `Mosaic URL built`, 'success');
    
    addTileLayer(map, mosaicUrl, null);
    log('tiles', `Mosaic tiles displayed`, 'success');
  } catch (error) {
    log('tiles', `Failed: ${error.message}`, 'error');
  }
}

function updateTileButtons() {
  const hasCollection = $('tile-collection-select').value !== '';
  const hasItem = $('tile-item-select').value !== '';
  
  $('btn-show-tiles').disabled = !hasItem;
  $('btn-show-mosaic').disabled = !hasCollection;
}

// ========== Tab 5: SAS Downloads ==========

async function handleSasCollectionChange() {
  const collectionId = $('sas-collection-select').value;
  
  // Reset downstream selects
  $('sas-item-select').innerHTML = '<option value="">-- Select an item --</option>';
  $('sas-asset-select').innerHTML = '<option value="">-- Select an asset --</option>';
  $('sas-item-select').disabled = true;
  $('sas-asset-select').disabled = true;
  $('sas-info').style.display = 'none';
  currentSasToken = null;
  currentAssetUrl = null;
  updateSasButtons();
  
  if (!collectionId || !isAuthenticated()) return;
  
  try {
    log('sas', `Loading items from ${collectionId}...`, 'info');
    const token = await getAccessToken();
    
    sasItems = await listItems(token, collectionId, 20);
    
    const select = $('sas-item-select');
    select.innerHTML = '<option value="">-- Select an item --</option>';
    sasItems.forEach(item => {
      const option = document.createElement('option');
      option.value = item.id;
      option.textContent = item.id;
      select.appendChild(option);
    });
    select.disabled = false;
    
    log('sas', `Found ${sasItems.length} items`, 'success');
  } catch (error) {
    log('sas', `Failed: ${error.message}`, 'error');
  }
}

async function handleSasItemChange() {
  const itemId = $('sas-item-select').value;
  
  // Reset asset select
  $('sas-asset-select').innerHTML = '<option value="">-- Select an asset --</option>';
  $('sas-asset-select').disabled = true;
  $('sas-info').style.display = 'none';
  currentSasToken = null;
  currentAssetUrl = null;
  updateSasButtons();
  
  if (!itemId) return;
  
  const item = sasItems.find(i => i.id === itemId);
  if (!item) return;
  
  const assets = getAssetInfo(item);
  
  const select = $('sas-asset-select');
  select.innerHTML = '<option value="">-- Select an asset --</option>';
  assets.forEach(asset => {
    const option = document.createElement('option');
    option.value = asset.name;
    const sizeStr = asset.size ? ` (${formatBytes(asset.size)})` : '';
    option.textContent = `${asset.title}${sizeStr}`;
    select.appendChild(option);
  });
  select.disabled = false;
  
  log('sas', `Found ${assets.length} assets in item`, 'success');
  updateSasButtons();
}

async function handleGetSas() {
  const collectionId = $('sas-collection-select').value;
  const itemId = $('sas-item-select').value;
  const assetName = $('sas-asset-select').value;
  
  if (!collectionId || !itemId || !assetName) return;
  
  const item = sasItems.find(i => i.id === itemId);
  if (!item || !item.assets[assetName]) return;
  
  try {
    log('sas', `Getting SAS token for ${collectionId}...`, 'info');
    const accessToken = await getAccessToken();
    
    currentSasToken = await getCollectionSasToken(accessToken, collectionId);
    log('sas', `SAS token received`, 'success');
    
    const assetHref = item.assets[assetName].href;
    currentAssetUrl = buildSignedAssetUrl(assetHref, currentSasToken);
    
    // Show SAS URL info
    $('sas-url').textContent = currentAssetUrl.substring(0, 100) + '...';
    $('sas-info').style.display = 'block';
    
    log('sas', `Signed URL ready for download`, 'success');
    updateSasButtons();
  } catch (error) {
    log('sas', `Failed: ${error.message}`, 'error');
  }
}

function handleDownload() {
  if (!currentAssetUrl) return;
  
  const assetName = $('sas-asset-select').value;
  const itemId = $('sas-item-select').value;
  const item = sasItems.find(i => i.id === itemId);
  
  // Try to get filename from asset href
  const href = item?.assets[assetName]?.href || '';
  const filename = href.split('/').pop()?.split('?')[0] || `${itemId}_${assetName}`;
  
  log('sas', `Starting download: ${filename}`, 'info');
  downloadFile(currentAssetUrl, filename);
  log('sas', `Download initiated`, 'success');
}

function updateSasButtons() {
  const hasAsset = $('sas-asset-select').value !== '';
  const hasSasUrl = currentAssetUrl !== null;
  
  $('btn-get-sas').disabled = !hasAsset;
  $('btn-download').disabled = !hasSasUrl;
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// ========== Initialize ==========

document.addEventListener('DOMContentLoaded', async () => {
  console.log('GeoCatalog Code Samples');
  console.log(`Catalog: ${config.catalogUrl}`);
  
  initTabs();
  
  // Initialize auth and handle any redirect response
  try {
    await initAuth();
    if (isAuthenticated()) {
      const account = getAccount();
      log('auth', `Authenticated as: ${account.username || account.name || 'user'}`, 'success');
      const token = await getAccessToken();
      updateAccessToken(token);
      log('auth', 'Access token acquired', 'success');
    }
  } catch (e) {
    // No existing session, user will need to login
    console.log('No existing session:', e.message);
  }
  
  updateAuthUI();
  
  // Tab 1: Auth
  $('btn-login').addEventListener('click', handleLogin);
  $('btn-logout').addEventListener('click', handleLogout);
  
  // Tab 2: STAC
  $('btn-list-collections').addEventListener('click', handleListCollections);
  $('btn-list-items').addEventListener('click', handleListItems);
  $('collection-select').addEventListener('change', updateStacButtons);
  
  // Tab 3: STAC Search
  $('search-collection-select').addEventListener('change', updateSearchButtons);
  $('btn-search-execute').addEventListener('click', handleSearchExecute);
  $('btn-search-clear').addEventListener('click', handleSearchClear);
  $('btn-use-map-bounds').addEventListener('click', handleUseMapBounds);
  $('bbox-west').addEventListener('input', updateSearchBboxLayer);
  $('bbox-south').addEventListener('input', updateSearchBboxLayer);
  $('bbox-east').addEventListener('input', updateSearchBboxLayer);
  $('bbox-north').addEventListener('input', updateSearchBboxLayer);
  
  // Tab 4: Tiles
  $('tile-collection-select').addEventListener('change', handleTileCollectionChange);
  $('tile-item-select').addEventListener('change', updateTileButtons);
  $('btn-show-tiles').addEventListener('click', handleShowTiles);
  $('btn-show-mosaic').addEventListener('click', handleShowMosaic);
  
  // Tab 5: SAS Downloads
  $('sas-collection-select').addEventListener('change', handleSasCollectionChange);
  $('sas-item-select').addEventListener('change', handleSasItemChange);
  $('sas-asset-select').addEventListener('change', updateSasButtons);
  $('btn-get-sas').addEventListener('click', handleGetSas);
  $('btn-download').addEventListener('click', handleDownload);
});
