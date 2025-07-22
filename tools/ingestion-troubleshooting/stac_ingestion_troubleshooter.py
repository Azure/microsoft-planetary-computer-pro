#!/usr/bin/env python3
"""
STAC Item Ingestion Troubleshooter for Microsoft Planetary Computer Pro

This script helps troubleshoot ingestion issues when adding STAC items from 
Azure Blob Storage to a GeoCatalog collection, providing checks at each step.

Usage:
    python stac_ingestion_troubleshooter.py --geocatalog-url <URL> --collection-id <ID> \
        --storage-account <NAME> --container <NAME> [--blob <PATH>]

Requirements:
    - Python 3.8+
    - azure-identity, azure-storage-blob, requests
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import requests
import azure.storage.blob
from azure.identity import AzureCliCredential, DefaultAzureCredential
from azure.core.exceptions import ClientAuthenticationError

# Constants
MPCPRO_APP_ID = "https://geocatalog.spatio.azure.com"
API_VERSION = "2025-04-30-preview"

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Troubleshoot STAC item ingestion in Microsoft Planetary Computer Pro')
    parser.add_argument('--geocatalog-url', required=True, help='URL of your GeoCatalog (e.g., https://your-geocatalog.geocatalog.spatio.azure.com)')
    parser.add_argument('--collection-id', required=True, help='ID of your STAC collection')
    parser.add_argument('--storage-account', required=True, help='Storage account name (e.g., mystorageaccount)')
    parser.add_argument('--container', required=True, help='Container name (e.g., stacitems)')
    parser.add_argument('--blob', help='Blob name/path to STAC item JSON (e.g., path/to/item.json). If not provided, a dummy item will be created.')
    parser.add_argument('--create-dummy', action='store_true', help='Create dummy STAC item and assets for testing')
    parser.add_argument('--timeout', type=int, default=300, help='Timeout for monitoring ingestion operation in seconds (default: 300)')
    return parser.parse_args()

def setup_authentication():
    """Set up authentication for Azure."""
    print("\n=== Step 2: Setting up authentication ===")
    
    try:
        # Try AzureCliCredential first (for local development)
        credential = AzureCliCredential()
        # Test the credential
        token = credential.get_token(f"{MPCPRO_APP_ID}/.default")
        print("✓ Authentication using AzureCliCredential successful")
        return credential
    except (ClientAuthenticationError, Exception) as e:
        print(f"AzureCliCredential failed: {str(e)}")
        try:
            # Fall back to DefaultAzureCredential
            credential = DefaultAzureCredential()
            token = credential.get_token(f"{MPCPRO_APP_ID}/.default")
            print("✓ Authentication using DefaultAzureCredential successful")
            return credential
        except Exception as e:
            print(f"❌ ERROR: Authentication failed: {str(e)}")
            print("\nTroubleshooting tips:")
            print("  - Make sure you're logged in with 'az login'")
            print("  - Verify you have the right permissions to your GeoCatalog and storage account")
            print("  - Check your Azure subscription status")
            raise

def generate_sas_token(credential, storage_account_name, container_name):
    """Generate a SAS token for the specified container."""
    print("\n=== Step 3: Generating SAS token ===")
    
    try:
        # Create a BlobServiceClient
        account_url = f"https://{storage_account_name}.blob.core.windows.net"
        blob_service_client = azure.storage.blob.BlobServiceClient(
            account_url=account_url,
            credential=credential
        )
        
        # Get user delegation key
        now = datetime.now(timezone.utc).replace(microsecond=0)
        key = blob_service_client.get_user_delegation_key(
            key_start_time=now + timedelta(hours=-1),
            key_expiry_time=now + timedelta(hours=24)  # 24 hour expiry
        )
        
        # Generate SAS token
        sas_token = azure.storage.blob.generate_container_sas(
            account_name=storage_account_name,
            container_name=container_name,
            user_delegation_key=key,
            permission=azure.storage.blob.ContainerSasPermissions(read=True, list=True),
            start=now + timedelta(hours=-1),
            expiry=now + timedelta(hours=24)
        )
        
        print("✓ SAS token generated successfully")
        return sas_token, blob_service_client
    except Exception as e:
        print(f"❌ ERROR: Failed to generate SAS token: {str(e)}")
        print("\nTroubleshooting tips:")
        print("  - Verify your storage account name is correct")
        print("  - Confirm you have the right permissions on the storage account")
        print("  - Check if your account allows SAS token generation")
        raise

def create_ingestion_source(credential, geocatalog_url, container_url, sas_token):
    """Create an ingestion source in GeoCatalog."""
    print("\n=== Step 4: Creating ingestion source ===")
    
    try:
        # Obtain access token for GeoCatalog
        access_token = credential.get_token(f"{MPCPRO_APP_ID}/.default")
        
        # Payload for creating ingestion source
        payload = {
            "kind": "SasToken",
            "connectionInfo": {
                "containerUrl": container_url,
                "sasToken": sas_token,
            }
        }
        
        # Create ingestion source
        ingestion_sources_endpoint = f"{geocatalog_url}/inma/ingestion-sources"
        response = requests.post(
            ingestion_sources_endpoint,
            json=payload,
            headers={"Authorization": f"Bearer {access_token.token}"},
            params={"api-version": API_VERSION}
        )
        
        if response.status_code == 201:
            print("✓ Ingestion source created successfully")
            return response.json()["id"]
        else:
            print(f"⚠️ WARNING: Ingestion source creation returned status {response.status_code}")
            print(f"Response: {response.text}")
            
            # Check if source already exists
            print("Checking if an ingestion source already exists for this container...")
            
            response = requests.get(
                ingestion_sources_endpoint,
                headers={"Authorization": f"Bearer {access_token.token}"},
                params={"api-version": API_VERSION}
            )
            
            sources = response.json()["value"]
            existing_source = None
            
            for source in sources:
                source_detail = requests.get(
                    f"{ingestion_sources_endpoint}/{source['id']}",
                    headers={"Authorization": f"Bearer {access_token.token}"},
                    params={"api-version": API_VERSION}
                ).json()
                
                if source_detail["connectionInfo"].get("containerUrl") == container_url:
                    existing_source = source_detail
                    break
            
            if existing_source:
                print(f"✓ Found existing ingestion source with ID: {existing_source['id']}")
                return existing_source['id']
            else:
                print("❌ ERROR: Failed to create ingestion source and no existing source found")
                print("\nTroubleshooting tips:")
                print("  - Check your GeoCatalog URL is correct")
                print("  - Verify you have permission to create ingestion sources")
                raise Exception("Failed to create or find ingestion source")

    except Exception as e:
        print(f"❌ ERROR: Failed to set up ingestion source: {str(e)}")
        raise

def ensure_absolute_href(href, storage_account, container):
    """Ensure that the asset href is an absolute URL."""
    parsed_url = urlparse(href)
    if parsed_url.scheme and parsed_url.netloc:
        return href
    
    blob_path = href.lstrip('/')
    absolute_href = f"https://{storage_account}.blob.core.windows.net/{container}/{blob_path}"
    print(f"Converting relative href '{href}' to absolute: '{absolute_href}'")
    return absolute_href

def process_stac_item(stac_item, storage_account, container, collection_id, geocatalog_url):
    """Process a STAC item to ensure all asset hrefs are absolute URLs and collection links are correct."""
    # Update collection ID
    stac_item["collection"] = collection_id
    print(f"✓ Updated collection ID to: {collection_id}")

    # Ensure assets have absolute hrefs
    if "assets" in stac_item:
        for asset_key, asset in stac_item["assets"].items():
            if "href" in asset:
                asset["href"] = ensure_absolute_href(asset["href"], storage_account, container)
    
    # Ensure links array exists and collection link is correct
    if "links" not in stac_item:
        stac_item["links"] = []
        
    collection_link_exists = False
    for link in stac_item["links"]:
        if link.get("rel") == "collection":
            link["href"] = f"{geocatalog_url}/stac/collections/{collection_id}"
            collection_link_exists = True
            break
            
    if not collection_link_exists:
        stac_item["links"].append({
            "rel": "collection",
            "href": f"{geocatalog_url}/stac/collections/{collection_id}",
            "type": "application/json"
        })
    print("✓ Added/updated collection link in the STAC item")

    return stac_item

def read_stac_item(blob_service_client, container_name, blob_name, collection_id, geocatalog_url, storage_account_name):
    """Read and validate the STAC item from blob storage."""
    print("\n=== Step 5: Reading STAC item ===")
    
    try:
        # Create a blob client
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        
        # Download the blob
        stac_item_data = blob_client.download_blob().readall()
        
        # Parse the JSON
        stac_item = json.loads(stac_item_data)
        
        # Verify it's a valid STAC item
        required_fields = ["id", "type", "geometry", "properties", "assets"]
        missing_fields = [field for field in required_fields if field not in stac_item]
        
        if missing_fields:
            print(f"⚠️ WARNING: STAC item is missing required fields: {', '.join(missing_fields)}")
        else:
            print("✓ STAC item read successfully and contains required fields")
        
        # Process STAC item to ensure absolute hrefs and correct links
        stac_item = process_stac_item(stac_item, storage_account_name, container_name, collection_id, geocatalog_url)
        
        # Check for assets
        if not stac_item.get("assets"):
            print("⚠️ WARNING: STAC item has no assets defined")
        else:
            print(f"✓ Found {len(stac_item['assets'])} assets in the STAC item")
            
        # Verify assets have proper hrefs
        invalid_assets = []
        for asset_key, asset in stac_item.get("assets", {}).items():
            if "href" not in asset:
                invalid_assets.append(asset_key)
        
        if invalid_assets:
            print(f"⚠️ WARNING: Assets missing 'href' field: {', '.join(invalid_assets)}")
            
        return stac_item
            
    except Exception as e:
        print(f"❌ ERROR: Failed to read STAC item: {str(e)}")
        print("\nTroubleshooting tips:")
        print("  - Verify the blob name is correct")
        print("  - Check if the file is a valid JSON")
        print("  - Ensure the file exists in the specified container")
        raise

def ingest_stac_item(credential, geocatalog_url, collection_id, stac_item):
    """Ingest the STAC item into the collection."""
    print("\n=== Step 6: Ingesting STAC item ===")
    
    try:
        # Obtain access token for GeoCatalog
        access_token = credential.get_token(f"{MPCPRO_APP_ID}/.default")
        
        # Endpoint for adding items to a collection
        items_endpoint = f"{geocatalog_url}/stac/collections/{collection_id}/items"
        
        # Post the STAC item
        response = requests.post(
            items_endpoint,
            json=stac_item,
            headers={"Authorization": f"Bearer {access_token.token}"},
            params={"api-version": API_VERSION}
        )
        
        if response.status_code == 202:
            print("✓ STAC item accepted for ingestion")
            # Safely access the operation ID and location
            response_json = response.json()
            operation_id = response_json.get("operationId")
            operation_location = response.headers.get("location")
            
            if operation_id:
                print(f"  Operation ID: {operation_id}")
            else:
                print("  Note: No operation ID returned in response")
                
            if operation_location:
                print(f"  Operation location: {operation_location}")
            else:
                print("  Note: No operation location header returned")
                
            return operation_id, operation_location
        else:
            print(f"❌ ERROR: Failed to ingest STAC item. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            print("\nTroubleshooting tips:")
            print("  - Verify the collection ID exists in your GeoCatalog")
            print("  - Check that the STAC item is properly formatted")
            print("  - Ensure the assets in the STAC item are accessible via the ingestion source")
            raise Exception(f"STAC item ingestion failed with status code {response.status_code}")

    except Exception as e:
        print(f"❌ ERROR: Failed to ingest STAC item: {str(e)}")
        raise

def monitor_ingestion(credential, operation_location, geocatalog_url, collection_id, stac_item, timeout=300):
    """Monitor the ingestion operation."""
    print("\n=== Step 7: Monitoring ingestion operation ===")
    
    try:
        if not operation_location:
            print("⚠️ WARNING: No operation location provided, cannot monitor ingestion progress")
            print("Skipping to verification step...")
        else:
            print("\nMonitoring ingestion progress:")
            
            status = "Running"
            start_time = time.time()
            
            while status in ["Running", "Pending"] and time.time() - start_time < timeout:
                access_token = credential.get_token(f"{MPCPRO_APP_ID}/.default")
                response = requests.get(
                    operation_location,
                    headers={"Authorization": f"Bearer {access_token.token}"}
                )
                
                operation_status = response.json()
                status = operation_status.get("status")
                
                print(f"  Status: {status} - {datetime.now().strftime('%H:%M:%S')}")
                
                if status == "Succeeded":
                    print("\n✓ STAC item ingestion completed successfully!")
                    break
                elif status == "Failed":
                    error_message = operation_status.get("error", {}).get("message", "Unknown error")
                    error_code = operation_status.get("error", {}).get("code", "")
                    error_details = operation_status.get("error", {}).get("details", [])
                    
                    print(f"\n❌ ERROR: Ingestion operation failed: {error_message}")
                    if error_code:
                        print(f"  Error code: {error_code}")
                    if error_details:
                        print(f"  Error details: {json.dumps(error_details, indent=2)}")
                    
                    # Display detailed operation information
                    print("\nOperation details:")
                    print(json.dumps(operation_status, indent=2))
                    
                    print("\nTroubleshooting tips:")
                    print("  - Check if the assets are accessible from the ingestion source")
                    print("  - Verify the STAC item is correctly formatted")
                    print("  - Ensure the asset path 'href' values are correct relative to the container")
                    print("  - For dummy assets, verify the thumbnail file was uploaded successfully")
                    break
                
                time.sleep(10)  # Check every 10 seconds
                
            if status not in ["Succeeded", "Failed"]:
                print("\n⚠️ WARNING: Ingestion is still running after timeout period")
                print(f"  You can check the status later using the operation location: {operation_location}")
        
        # Verify the item was ingested
        item_id = stac_item["id"]
        item_endpoint = f"{geocatalog_url}/stac/collections/{collection_id}/items/{item_id}"
        
        access_token = credential.get_token(f"{MPCPRO_APP_ID}/.default")
        response = requests.get(
            item_endpoint,
            headers={"Authorization": f"Bearer {access_token.token}"},
            params={"api-version": API_VERSION}
        )
        
        if response.status_code == 200:
            print(f"✓ Verification: Found item with ID '{item_id}' in the collection")
            return True
        else:
            print(f"⚠️ WARNING: Could not verify item in collection. Status code: {response.status_code}")
            print("This might be because the ingestion is still in progress")
            print(f"Try checking the item directly later: {item_endpoint}?api-version={API_VERSION}")
            return False

    except Exception as e:
        print(f"❌ ERROR during monitoring: {str(e)}")
        return False

def create_dummy_stac_item(blob_service_client, container_name, blob_name, collection_id, geocatalog_url, storage_account_name):
    """Create a dummy STAC item for testing."""
    print("\n=== Creating a dummy STAC item for testing ===")
    
    try:
        # Extract directory path from blob_name if it exists
        blob_dir = ""
        if "/" in blob_name:
            blob_dir = blob_name.rsplit("/", 1)[0] + "/"
        
        # Create a text file as asset instead of an image - avoids conversion issues
        data_blob_name = f"{blob_dir}dummy-data.txt"
        
        # Create a simple STAC item with a text file as asset
        stac_item = {
            "type": "Feature",
            "stac_version": "1.0.0",
            "id": f"sample-item-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "properties": {
                "datetime": datetime.now(timezone.utc).isoformat(),
                "title": "Sample STAC Item",
                "description": "A sample STAC item for testing ingestion"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-122.4, 47.5],
                        [-122.2, 47.5],
                        [-122.2, 47.7],
                        [-122.4, 47.7],
                        [-122.4, 47.5]
                    ]
                ]
            },
            "bbox": [-122.4, 47.5, -122.2, 47.7],
            "links": [],
            "assets": {
                "data": {
                    "href": data_blob_name,
                    "title": "Dummy Data",
                    "description": "A text file for testing ingestion",
                    "type": "text/plain",
                    "roles": ["data"]
                }
            },
            "collection": collection_id
        }

        # Process STAC item to ensure absolute hrefs and correct links
        stac_item = process_stac_item(stac_item, storage_account_name, container_name, collection_id, geocatalog_url)
        
        # Create a blob client and upload the STAC item
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        blob_client.upload_blob(json.dumps(stac_item, indent=2), overwrite=True)
        
        # Create a dummy text file as the asset
        data_blob_client = blob_service_client.get_blob_client(container=container_name, blob=data_blob_name)
        
        # Simple text content
        text_content = "This is a dummy text file used for testing STAC item ingestion in Microsoft Planetary Computer Pro."
        data_blob_client.upload_blob(text_content, overwrite=True)
        
        print(f"✓ Created dummy STAC item: {blob_name}")
        print(f"✓ Created dummy text file asset: {data_blob_name}")
        
        # Verify the text file is accessible
        try:
            data_props = data_blob_client.get_blob_properties()
            print(f"✓ Verified text file exists: {data_blob_name} ({data_props.size} bytes)")
        except Exception as e:
            print(f"⚠️ WARNING: Could not verify text file accessibility: {str(e)}")
        
        return stac_item
        
    except Exception as e:
        print(f"❌ ERROR: Failed to create dummy STAC item: {str(e)}")
        raise

def main():
    """Main function orchestrating the troubleshooting steps."""
    args = parse_arguments()
    
    print("=== STAC Item Ingestion Troubleshooter ===")
    print("This script will help you troubleshoot ingestion issues with Microsoft Planetary Computer Pro.\n")
    
    # Step 1: Define variables
    print("=== Step 1: Defining variables ===")
    geocatalog_url = args.geocatalog_url.rstrip('/')
    collection_id = args.collection_id
    storage_account_name = args.storage_account
    container_name = args.container
    
    # If blob isn't provided or create_dummy flag is set, generate a default blob path
    create_dummy = args.create_dummy or not args.blob
    if not args.blob:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        blob_name = f"dummy-stac-item-{timestamp}.json"
        print(f"No blob path provided, will create dummy STAC item at: {blob_name}")
    else:
        blob_name = args.blob
    
    container_url = f"https://{storage_account_name}.blob.core.windows.net/{container_name}"
    
    print(f"GeoCatalog URL: {geocatalog_url}")
    print(f"Collection ID: {collection_id}")
    print(f"Storage Account: {storage_account_name}")
    print(f"Container: {container_name}")
    print(f"Blob: {blob_name}")
    print(f"Container URL: {container_url}")
    print("✓ Variables defined")
    
    try:
        # Step 2: Set up authentication
        credential = setup_authentication()
        
        # Step 3: Generate SAS token
        sas_token, blob_service_client = generate_sas_token(credential, storage_account_name, container_name)
        
        # Check if blob exists, create dummy if it doesn't exist or if dummy creation is requested
        blob_exists = False
        if not create_dummy:  # Only check if we're not already planning to create a dummy
            try:
                blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
                blob_client.get_blob_properties()
                blob_exists = True
                print(f"✓ Found existing blob: {blob_name}")
            except Exception as e:
                print(f"\n⚠️ WARNING: Blob {blob_name} not found: {str(e)}")
                create_dummy = True
        
        # Create dummy STAC item if needed
        if create_dummy:
            print("Creating dummy STAC item for testing...")
            stac_item = create_dummy_stac_item(blob_service_client, container_name, blob_name, collection_id, geocatalog_url, storage_account_name)
        
        # Step 4: Create an ingestion source
        ingestion_source_id = create_ingestion_source(credential, geocatalog_url, container_url, sas_token)
        
        # Step 5: Read the STAC item
        stac_item = read_stac_item(blob_service_client, container_name, blob_name, collection_id, geocatalog_url, storage_account_name)
        
        # Step 6: Ingest the STAC item
        operation_id, operation_location = ingest_stac_item(credential, geocatalog_url, collection_id, stac_item)
        
        # Step 7: Monitor the ingestion operation
        success = monitor_ingestion(credential, operation_location, geocatalog_url, collection_id, stac_item, args.timeout)
        
        # Summary
        print("\n=== Troubleshooting summary ===")
        if success:
            print("✅ Ingestion process completed successfully!")
        else:
            print("⚠️ Ingestion process completed with warnings.")
            
        print(f"\nYou can view your collection in the GeoCatalog Explorer: {geocatalog_url}/collections/{collection_id}")
        
    except Exception as e:
        print("\n=== Troubleshooting summary ===")
        print(f"❌ Ingestion process failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()