# JavaScript Quickstart: Build a Web Application with GeoCatalog

This sample demonstrates how to build a web application that connects to Microsoft Planetary Computer Pro GeoCatalog, following the [Build a web application quickstart](https://learn.microsoft.com/azure/planetary-computer/build-web-application).

## Features

- **Authentication** - Sign in with Microsoft Entra ID using MSAL.js
- **STAC API** - Browse collections and items using the STAC specification
- **Tile Visualization** - Display raster data on interactive maps with MapLibre GL JS
- **Search** - Spatial and temporal filtering across collections
- **Asset Downloads** - Get SAS tokens for direct asset access from Azure Blob Storage

## Prerequisites

- [Node.js](https://nodejs.org/) 18 or later
- A GeoCatalog resource deployed in Azure
- An app registration in Microsoft Entra ID (see [Application Authentication](https://learn.microsoft.com/azure/planetary-computer/application-authentication))

## Quick Start

### 1. Get the code

**Option A: Clone just this sample (recommended)**

```bash
git clone --filter=blob:none --sparse https://github.com/Azure/microsoft-planetary-computer-pro.git
cd microsoft-planetary-computer-pro
git sparse-checkout set tools/javascript-sample
cd tools/javascript-sample
```

**Option B: Download as ZIP**

1. Go to [this folder on GitHub](https://github.com/Azure/microsoft-planetary-computer-pro/tree/main/tools/javascript-sample)
2. Click the "Code" button → "Download ZIP", or use [download-directory.github.io](https://download-directory.github.io/?url=https://github.com/Azure/microsoft-planetary-computer-pro/tree/main/tools/javascript-sample)

**Option C: Clone the entire repository**

```bash
git clone https://github.com/Azure/microsoft-planetary-computer-pro.git
cd microsoft-planetary-computer-pro/tools/javascript-sample
```

### 2. Install dependencies

```bash
npm install
```

### 3. Configure environment

Copy the example environment file and fill in your values:

```bash
cp .env.example .env.local
```

Edit `.env.local` with your GeoCatalog configuration:

```env
# Your GeoCatalog endpoint URL
VITE_GEOCATALOG_URL=https://your-catalog.geocatalog.spatio.azure.com

# Microsoft Entra ID configuration
VITE_ENTRA_TENANT_ID=your-tenant-id
VITE_ENTRA_CLIENT_ID=your-app-registration-client-id

# API version (optional, defaults to 2025-04-30-preview)
VITE_GEOCATALOG_API_VERSION=2025-04-30-preview

# Development server port (optional, defaults to 5173)
VITE_DEV_PORT=5173
```

> **Note:** If you change `VITE_DEV_PORT`, update your app registration's redirect URI to match (e.g., `http://localhost:3000`).

### 4. Run the application

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

## Project Structure

```
├── src/
│   ├── main.js              # Application entry point
│   └── snippets/
│       ├── config.js        # Configuration from environment variables
│       ├── auth.js          # MSAL authentication (Step 4)
│       ├── stac-api.js      # STAC API functions (Step 5)
│       ├── tile-urls.js     # Tile URL construction (Steps 6 & 8)
│       ├── map-integration.js # MapLibre GL JS setup (Step 7)
│       └── sas-api.js       # SAS token API for downloads
├── index.html               # Main HTML file
├── .env.example             # Environment template
├── package.json
└── vite.config.js
```

## Code Snippets

Each file in `src/snippets/` corresponds to a step in the [Build a web application quickstart](https://learn.microsoft.com/azure/planetary-computer/build-web-application):

| File | Documentation Step | Description |
|------|-------------------|-------------|
| `config.js` | Step 3 | Configure environment variables |
| `auth.js` | Step 4 | Initialize MSAL and handle login/logout |
| `stac-api.js` | Step 5 | List collections, items, and search |
| `tile-urls.js` | Steps 6 & 8 | Build tile URLs for visualization |
| `map-integration.js` | Step 7 | Initialize MapLibre GL JS map |
| `sas-api.js` | - | Get SAS tokens for asset downloads |

## Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory, ready to deploy to any static hosting service.

## Learn More

- [Microsoft Planetary Computer Pro Documentation](https://learn.microsoft.com/azure/planetary-computer/)
- [Build a web application quickstart](https://learn.microsoft.com/azure/planetary-computer/build-web-application)
- [STAC Specification](https://stacspec.org/)
- [MapLibre GL JS](https://maplibre.org/)
- [MSAL.js Documentation](https://learn.microsoft.com/azure/active-directory/develop/msal-overview)

## License

MIT - See [LICENSE](../../LICENSE)
