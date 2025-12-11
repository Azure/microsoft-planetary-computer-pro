/**
 * Configuration - GeoCatalog Pro API settings
 * 
 * Loads from environment variables (Vite).
 */

export const config = {
  // Public configuration - these are safe and expected
  catalogUrl: import.meta.env.VITE_CATALOG_URL,
  tenantId: import.meta.env.VITE_TENANT_ID,
  clientId: import.meta.env.VITE_CLIENT_ID,
  apiVersion: import.meta.env.VITE_API_VERSION || '2025-04-30-preview',
  scope: 'https://geocatalog.spatio.azure.com/.default',
  };

// Validate required configuration
const missingVars = [];
if (!config.catalogUrl) missingVars.push('VITE_CATALOG_URL');
if (!config.tenantId) missingVars.push('VITE_TENANT_ID');
  if (!config.clientId) missingVars.push('VITE_CLIENT_ID');
if (missingVars.length > 0) {
  throw new Error(`Missing required environment variables: ${missingVars.join(', ')}. Copy .env.example to .env.local and fill in your GeoCatalog configuration.`);
}

