# Azure Planetary Computer Multi-Tenant Application# Azure Planetary Computer GeoCatalog Testing Application



This repository demonstrates a complete multi-tenant architecture for Azure Planetary Computer GeoCatalog access, organized into three main components:This repository contains a Jupyter notebook for testing Azure Planetary Computer Pro GeoCatalog operations using multiple authentication methods.



## 📁 Repository Structure

### 🖥️ client-app/

The client application that tests and demonstrates GeoCatalog infrastructure.- Authenticate with Azure using multiple methods:

- Tests authentication flows (Service Principal, Device Code, MSAL)  - Service Principal (Client Secret)
- Demonstrates STAC API operations  - Device Code Flow (azure.identity)
- Validates GeoCatalog connectivity  - MSAL Device Code Flow (on-behalf-of-user)
- See [client-app/README.md](./client-app/README.md) for details  - MSAL Interactive Browser (on-behalf-of-user)
- Connect to a Microsoft Planetary Computer Pro GeoCatalog

### 🏢 provider-app/

The provider/ISV application setup and management code.- List collections and search for items

- Sets up Azure App Registration for enterprise application- Retrieve API conformance information
- Configures multi-tenant settings
- Manages provider service principal
- Provisions shareable enterprise application
- See [provider-app/README.md](./provider-app/README.md) for details. 

### 👥 customer-app/

- Registers provider app in customer tenant   - Client Secret
- Assigns appropriate permissions3. **GeoCatalog Access**: Access to a Planetary Computer Pro GeoCatalog resource
- Manages customer-side access control4. **Python**: Python 3.10 or higher
- See [customer-app/README.md](./customer-app/README.md) for details

## 📖 Documentation

- [Quickstart](./QUICK_REFERENCE.md)
- [Architecture](./ARCHITECTURE.md)
- [Client App Documentation](./client-app/README.md)
- [Provider App Documentation](./provider-app/README.md)
- [Customer App Documentation](./customer-app/README.md)

## 📄 License

See [LICENSE](./LICENSE) for details.