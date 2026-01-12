import { defineConfig } from 'vite';
export default defineConfig({
  server: {
    port: parseInt(process.env.VITE_DEV_PORT) || 5173,
    open: true,
    headers: {
      // Required for MSAL popup authentication
      'Cross-Origin-Opener-Policy': 'same-origin-allow-popups',
    },
  },
});
