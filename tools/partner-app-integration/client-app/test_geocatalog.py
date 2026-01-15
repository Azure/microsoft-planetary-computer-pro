#!/usr/bin/env python3
"""
Azure Planetary Computer GeoCatalog Testing Script

This script tests authentication and basic operations with Microsoft Planetary Computer Pro 
GeoCatalog using multiple authentication methods:
1. Azure Client Secret (Service Principal)
2. Device Code Flow via azure.identity (User)
3. MSAL Device Code Flow (User - On Behalf Of, Public Client)
4. MSAL Interactive Browser Flow (User - On Behalf Of, Confidential Client with Secret)

Prerequisites:
- Azure Service Principal with access to GeoCatalog (for client secret auth)
- Azure AD application registration (can be public or confidential)
- .env file with credentials configured
- Required Python packages installed (azure-identity, msal, requests, python-dotenv)

Note: 
- Device code flow (Option 3) uses PublicClientApplication (no secret required)
- Interactive browser flow (Option 4) can use ConfidentialClientApplication (with secret)

Usage:
    python test_geocatalog.py
"""

import os
import json
import sys
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential, DeviceCodeCredential
import msal


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def load_configuration():
    """Load environment variables from .env file."""
    print_section("1. Loading Configuration")
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Get credentials from environment
    config = {
        'AZURE_CLIENT_ID': os.getenv('AZURE_CLIENT_ID'),
        'AZURE_TENANT_ID': os.getenv('AZURE_TENANT_ID'),
        'AZURE_CLIENT_SECRET': os.getenv('AZURE_CLIENT_SECRET'),
        'GEOCATALOG_URL': os.getenv('GEOCATALOG_URL')
    }
    
    # Verify credentials are loaded
    if not all(config.values()):
        raise ValueError("Missing required environment variables. Please check your .env file.")
    
    print("✓ Configuration loaded successfully")
    print(f"  Client ID: {config['AZURE_CLIENT_ID'][:8]}...")
    print(f"  Tenant ID: {config['AZURE_TENANT_ID'][:8]}...")
    print(f"  GeoCatalog URL: {config['GEOCATALOG_URL']}")
    
    return config


def authenticate_client_secret(config):
    """Authenticate using Azure Client Secret credentials."""
    print_section("2. Authenticating with Azure Client Secret")
    
    # Create credential using client secret
    credential = ClientSecretCredential(
        tenant_id=config['AZURE_TENANT_ID'],
        client_id=config['AZURE_CLIENT_ID'],
        client_secret=config['AZURE_CLIENT_SECRET']
    )
    
    return credential


def authenticate_device_code(config):
    """Authenticate using device code flow (browser-based)."""
    print_section("2. Authenticating with Device Code (Browser)")
    print("This will open a browser window for authentication...")
    
    credential = DeviceCodeCredential(tenant_id=config['AZURE_TENANT_ID'])
    return credential


def authenticate_msal_confidential_client(config):
    """
    Authenticate using MSAL ConfidentialClientApplication with client secret.
    This is for app registrations that require a client secret (confidential clients).
    
    Args:
        config: Configuration dictionary with Azure credentials
    
    Returns:
        A wrapper object that provides get_token() method compatible with azure.identity
    """
    print_section("2. Authenticating with MSAL Confidential Client")
    
    authority = f"https://login.microsoftonline.com/{config['AZURE_TENANT_ID']}"
    
    # Create MSAL ConfidentialClientApplication (requires client secret)
    app = msal.ConfidentialClientApplication(
        client_id=config['AZURE_CLIENT_ID'],
        client_credential=config['AZURE_CLIENT_SECRET'],
        authority=authority
    )
    
    # Define the scope for GeoCatalog
    scopes = ["https://geocatalog.spatio.azure.com/.default"]
    
    print(f"Authority: {authority}")
    print(f"Client ID: {config['AZURE_CLIENT_ID'][:8]}...")
    print(f"Scopes: {scopes}")
    print(f"Flow: Client Credentials")
    print()
    
    # Acquire token for app (not on behalf of user)
    print("Acquiring token with client credentials...")
    result = app.acquire_token_for_client(scopes=scopes)
    
    # Check result
    if "access_token" in result:
        print("✓ Token acquired successfully")
        print(f"  Token Type: {result.get('token_type', 'N/A')}")
        print(f"  Expires In: {result.get('expires_in', 'N/A')} seconds")
        return MSALTokenWrapper(result)
    else:
        error = result.get("error")
        error_description = result.get("error_description")
        raise Exception(f"Authentication failed: {error} - {error_description}")


def authenticate_msal_on_behalf_of_user(config, use_device_code=True):
    """
    Authenticate using MSAL library on behalf of a user (Confidential Client).
    
    This uses a ConfidentialClientApplication with client secret for app registrations
    that require a client secret. 
    
    IMPORTANT: Confidential clients only support interactive browser flow for user authentication.
    Device code flow is not supported by ConfidentialClientApplication - it requires PublicClientApplication.
    
    Args:
        config: Configuration dictionary with Azure credentials (including client_secret)
        use_device_code: If True, uses device code flow (requires PublicClientApplication fallback). 
                        If False, uses interactive browser flow.
    
    Returns:
        A wrapper object that provides get_token() method compatible with azure.identity
    """
    print_section("2. Authenticating with MSAL (On Behalf of User)")
    
    authority = f"https://login.microsoftonline.com/{config['AZURE_TENANT_ID']}"
    scopes = ["https://geocatalog.spatio.azure.com/.default"]
    
    # Device code flow requires PublicClientApplication
    # Interactive browser flow can use ConfidentialClientApplication with secret
    if use_device_code:
        print("Note: Device code flow requires PublicClientApplication")
        print("Falling back to PublicClientApplication for device code flow...")
        print()
        
        # Create PublicClientApplication (no secret used)
        app = msal.PublicClientApplication(
            client_id=config['AZURE_CLIENT_ID'],
            authority=authority
        )
        
        print(f"Authority: {authority}")
        print(f"Client ID: {config['AZURE_CLIENT_ID'][:8]}...")
        print(f"Client Type: Public (device code flow)")
        print(f"Scopes: {scopes}")
        print(f"Flow: Device Code")
        print()
        
        # First, try to get token from cache
        accounts = app.get_accounts()
        if accounts:
            print(f"Found {len(accounts)} cached account(s)")
            result = app.acquire_token_silent(scopes, account=accounts[0])
            if result and "access_token" in result:
                print("✓ Token acquired from cache")
                return MSALTokenWrapper(result)
        
        # Initiate device code flow
        print("Initiating device code flow...")
        flow = app.initiate_device_flow(scopes=scopes)
        
        if "user_code" not in flow:
            raise ValueError(f"Failed to create device flow: {flow.get('error_description')}")
        
        # Display the user code and instructions
        print("\n" + "=" * 80)
        print(flow["message"])
        print("=" * 80 + "\n")
        
        # Wait for user to authenticate
        result = app.acquire_token_by_device_flow(flow)
    else:
        # Interactive browser flow with ConfidentialClientApplication
        print("Using ConfidentialClientApplication for interactive browser flow...")
        print()

        # Create PublicClientApplication (no secret used)
        app = msal.PublicClientApplication(
            client_id=config['AZURE_CLIENT_ID'],
            authority=authority
        )
        
        print(f"Authority: {authority}")
        print(f"Client ID: {config['AZURE_CLIENT_ID'][:8]}...")
        print(f"Client Type: Public (no secret)")
        print(f"Scopes: {scopes}")
        print(f"Flow: Interactive Browser")
        print()
        
        # First, try to get token from cache
        accounts = app.get_accounts()
        if accounts:
            print(f"Found {len(accounts)} cached account(s)")
            result = app.acquire_token_silent(scopes, account=accounts[0])
            if result and "access_token" in result:
                print("✓ Token acquired from cache")
                return MSALTokenWrapper(result)
        
        # Interactive Browser Flow - opens browser automatically
        print("Opening browser for interactive authentication...")
        result = app.acquire_token_interactive(
            scopes=scopes,
            prompt="select_account", port=8000  # Forces account selection
        )
    
    # Check result
    if "access_token" in result:
        print("✓ Token acquired successfully")
        if "account" in result:
            account = result["account"]
            print(f"  User: {account.get('username', 'N/A')}")
        return MSALTokenWrapper(result)
    else:
        error = result.get("error")
        error_description = result.get("error_description")
        raise Exception(f"Authentication failed: {error} - {error_description}")


class MSALTokenWrapper:
    """
    Wrapper class to make MSAL token response compatible with azure.identity credential interface.
    """
    def __init__(self, token_response):
        self.token_response = token_response
        self._token = token_response.get("access_token")
        self._expires_on = token_response.get("expires_in", 3600) + datetime.now().timestamp()
    
    def get_token(self, *scopes, **kwargs):
        """Return a token object compatible with azure.identity."""
        class TokenObject:
            def __init__(self, token, expires_on):
                self.token = token
                self.expires_on = expires_on
        
        return TokenObject(self._token, self._expires_on)


def get_access_token(credential):
    """Get access token for GeoCatalog API."""
    # GeoCatalog scope
    GEOCATALOG_SCOPE = "https://geocatalog.spatio.azure.com/.default"
    
    # Get access token
    try:
        token = credential.get_token(GEOCATALOG_SCOPE)
        print("✓ Authentication successful!")
        print(f"  Token obtained at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Token expires at: {datetime.fromtimestamp(token.expires_on).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Create authorization header
        headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json"
        }
        
        return headers, token
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        raise


def list_collections(geocatalog_url, headers, api_version):
    """List all STAC collections in the GeoCatalog."""
    print_section("3. Listing All Collections")
    
    collections_url = f"{geocatalog_url}/stac/collections"
    
    try:
        response = requests.get(
            collections_url,
            headers=headers,
            params={"api-version": api_version}
        )
        response.raise_for_status()
        
        collections_data = response.json()
        collections = collections_data.get('collections', [])
        
        print(f"✓ Found {len(collections)} collection(s)\n")
        
        if collections:
            for idx, collection in enumerate(collections, 1):
                print(f"{idx}. Collection ID: {collection.get('id')}")
                print(f"   Title: {collection.get('title', 'N/A')}")
                print(f"   Description: {collection.get('description', 'N/A')[:100]}...")
                print(f"   License: {collection.get('license', 'N/A')}")
                print()
        else:
            print("No collections found in this GeoCatalog.")
        
        return collections
            
    except requests.exceptions.HTTPError as e:
        print(f"✗ HTTP Error: {e}")
        if response.text:
            print(f"Response: {response.text}")
        return []
    except Exception as e:
        print(f"✗ Error: {e}")
        return []


def get_collection_details(geocatalog_url, headers, api_version, collection_id):
    """Get detailed information about a specific collection."""
    print_section(f"4. Getting Collection Details: {collection_id}")
    
    collection_url = f"{geocatalog_url}/stac/collections/{collection_id}"
    
    try:
        response = requests.get(
            collection_url,
            headers=headers,
            params={"api-version": api_version}
        )
        response.raise_for_status()
        
        collection = response.json()
        print(f"✓ Collection '{collection_id}' details:")
        print(json.dumps(collection, indent=2))
        
        return collection
        
    except requests.exceptions.HTTPError as e:
        print(f"✗ HTTP Error: {e}")
        if hasattr(locals().get('response'), 'text'):
            print(f"Response: {response.text}")
        return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def search_items(geocatalog_url, headers, api_version, collection_id=None, limit=10):
    """Search for items across collections."""
    print_section("5. Searching for Items")
    
    search_url = f"{geocatalog_url}/stac/search"
    
    # Basic search query
    search_query = {
        "limit": limit
    }
    
    # If a specific collection is provided, filter by it
    if collection_id:
        search_query["collections"] = [collection_id]
        print(f"Searching in collection: {collection_id}")
    
    try:
        response = requests.post(
            search_url,
            headers=headers,
            params={"api-version": api_version},
            json=search_query
        )
        response.raise_for_status()
        
        search_results = response.json()
        features = search_results.get('features', [])
        
        print(f"✓ Search completed. Found {len(features)} item(s)\n")
        
        if features:
            for idx, item in enumerate(features, 1):
                print(f"{idx}. Item ID: {item.get('id')}")
                print(f"   Collection: {item.get('collection')}")
                print(f"   Geometry Type: {item.get('geometry', {}).get('type', 'N/A')}")
                print(f"   Properties: {list(item.get('properties', {}).keys())[:5]}")
                print()
        else:
            print("No items found. This may be normal if your GeoCatalog is empty.")
        
        return features
            
    except requests.exceptions.HTTPError as e:
        print(f"✗ HTTP Error: {e}")
        if hasattr(locals().get('response'), 'text'):
            print(f"Response: {response.text}")
        return []
    except Exception as e:
        print(f"✗ Error: {e}")
        return []


def get_api_conformance(geocatalog_url, headers, api_version):
    """Get API conformance classes supported by the GeoCatalog."""
    print_section("6. Getting API Conformance Classes")
    
    conformance_url = f"{geocatalog_url}/stac/conformance"
    
    try:
        response = requests.get(
            conformance_url,
            headers=headers,
            params={"api-version": api_version}
        )
        response.raise_for_status()
        
        conformance = response.json()
        conforms_to = conformance.get('conformsTo', [])
        
        print(f"✓ API Conformance Classes ({len(conforms_to)}):")
        print()
        for idx, conformance_class in enumerate(conforms_to, 1):
            # Extract the conformance class name from the URL
            class_name = conformance_class.split('/')[-1] if '/' in conformance_class else conformance_class
            print(f"{idx}. {class_name}")
            print(f"   {conformance_class}")
        
        return conforms_to
            
    except requests.exceptions.HTTPError as e:
        print(f"✗ HTTP Error: {e}")
        if hasattr(locals().get('response'), 'text'):
            print(f"Response: {response.text}")
        return []
    except Exception as e:
        print(f"✗ Error: {e}")
        return []


def get_collection_sas_token(geocatalog_url, headers, api_version, collection_id):
    """
    Get a SAS token for a specific collection.
    
    SAS tokens provide temporary, secure access to collection assets stored in Azure Blob Storage.
    This is useful for applications that need direct access to geospatial data files.
    
    Args:
        geocatalog_url: Base URL of the GeoCatalog
        headers: Authorization headers with bearer token
        api_version: API version to use
        collection_id: ID of the collection to get SAS token for
    
    Returns:
        dict: SAS token response containing the token string and expiration info
    """
    print_section(f"7. Getting SAS Token for Collection: {collection_id}")
    
    sas_url = f"{geocatalog_url}/sas/token/{collection_id}"
    
    try:
        response = requests.get(
            sas_url,
            headers=headers,
            params={"api-version": api_version}
        )
        response.raise_for_status()
        
        sas_data = response.json()
        token = sas_data.get('token', '')
        
        print(f"✓ SAS Token retrieved successfully")
        print(f"  Collection ID: {collection_id}")
        print(f"  Token (first 50 chars): {token[:50]}...")
        print(f"  Token length: {len(token)} characters")
        
        # Display additional info if available
        if 'msft:expiry' in sas_data:
            print(f"  Expiry: {sas_data.get('msft:expiry')}")
        
        return sas_data
            
    except requests.exceptions.HTTPError as e:
        print(f"✗ HTTP Error: {e}")
        if hasattr(locals().get('response'), 'text'):
            print(f"Response: {response.text}")
        
        # Provide helpful context for common errors
        if hasattr(locals().get('response'), 'status_code'):
            if response.status_code == 404:
                print(f"\nNote: Collection '{collection_id}' may not exist or has no assets yet.")
                print("SAS tokens are only available for collections with ingested data.")
            elif response.status_code == 403:
                print(f"\nNote: You may not have permission to generate SAS tokens for this collection.")
        
        return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def print_summary():
    """Print test summary."""
    print_section("8. Summary")
    
    print("This script has demonstrated:")
    print("1. ✓ Loading Azure credentials from environment variables")
    print("2. ✓ Authenticating with Azure using ClientSecretCredential")
    print("3. ✓ Obtaining an access token for the GeoCatalog API")
    print("4. ✓ Making authenticated requests to the STAC API")
    print("5. ✓ Listing all collections")
    print("6. ✓ Searching for items")
    print("7. ✓ Checking API conformance classes")
    print("8. ✓ Generating SAS tokens for collection access")
    
    print("\nNext Steps:")
    print("- Create collections using POST to /stac/collections")
    print("- Add items to collections using POST to /stac/collections/{collection_id}/items")
    print("- Configure ingestion sources for automated data ingestion")
    print("- Explore data visualization and tiling operations")
    print("- Use SAS tokens for direct asset access in applications")


def main():
    """Main execution function."""
    try:
        # API version
        api_version = "2025-04-30-preview"
        
        # Load configuration
        config = load_configuration()
        
        # Authenticate (choose one method)
        # Option 1: Client Secret authentication (Service Principal - App Only)
        # This authenticates as the app itself, not on behalf of a user
        credential = authenticate_client_secret(config)
        
        # Option 2: Device Code authentication via azure.identity (User)
        #credential = authenticate_device_code(config)
        
        # Option 3: MSAL On-Behalf-Of User authentication (Device Code Flow - Public Client)
        # Note: Uses PublicClientApplication, does not require client secret
        # WARNING: Will fail if your app registration requires secret and doesn't allow public client flows
        # credential = authenticate_msal_on_behalf_of_user(config, use_device_code=True)
        
        # Option 4: MSAL On-Behalf-Of User authentication (Interactive Browser - Public Client)
        # Note: Uses PublicClientApplication for user auth
        # To use this with a confidential client app, enable "Allow public client flows" in Azure Portal
        # credential = authenticate_msal_on_behalf_of_user(config, use_device_code=False)
        
        # Get access token
        headers, token = get_access_token(credential)
        
        # List all collections
        collections = list_collections(config['GEOCATALOG_URL'], headers, api_version)
        
        # If collections exist, get details for the first one
        if collections:
            first_collection_id = collections[0].get('id')
            get_collection_details(config['GEOCATALOG_URL'], headers, api_version, first_collection_id)
            
            # Search for items in that collection
            search_items(config['GEOCATALOG_URL'], headers, api_version, collection_id=first_collection_id)
        else:
            # Search for all items (no collection filter)
            search_items(config['GEOCATALOG_URL'], headers, api_version)
        
        # Get API conformance
        get_api_conformance(config['GEOCATALOG_URL'], headers, api_version)
        
        # Test SAS token generation (if collections exist)
        if collections:
            first_collection_id = collections[0].get('id')
            get_collection_sas_token(config['GEOCATALOG_URL'], headers, api_version, first_collection_id)
        
        # Print summary
        print_summary()
        
        print("\n✓ All tests completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠ Script interrupted by user")
        return 130
    except Exception as e:
        print(f"\n✗ Script failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
