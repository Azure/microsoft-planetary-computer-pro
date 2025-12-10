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

