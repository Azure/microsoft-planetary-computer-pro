import { defineConfig } from 'vite';
export default defineConfig({
  server: {
    port: 5173,
    open: true,
    headers: {
      // Required for MSAL popup authentication
      'Cross-Origin-Opener-Policy': 'same-origin-allow-popups',
    },
  },
});
