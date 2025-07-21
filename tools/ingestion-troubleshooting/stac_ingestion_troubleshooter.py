#!/usr/bin/env python3
"""
STAC Item Ingestion Troubleshooter for Microsoft Planetary Computer Pro

This script helps troubleshoot ingestion issues when adding STAC items from 
Azure Blob Storage to a GeoCatalog collection, providing validation and 
comprehensive checks at each step.

Usage:
    python stac_ingestion_troubleshooter.py --geocatalog-url <URL> --collection-id <ID> \
        --storage-account <NAME> --container <NAME> [--blob <PATH>]

Requirements:
    - Python 3.8+
    - azure-identity, azure-storage-blob, requests
"""

import argparse
import json
import socket
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
    parser.add_argument('--storage-account', required=True, help='Storage account name (e.g., mystorageaccount)')
    parser.add_argument('--container', help='Container name (default: troubleshooting-container will be created automatically)')
    parser.add_argument('--collection-id', help='ID of your STAC collection (default: troubleshooting-collection will be created automatically)')
    parser.add_argument('--blob', help='Blob name/path to STAC item JSON (e.g., path/to/item.json). If not provided, a dummy item will be created.')
    parser.add_argument('--use-relative-links', action='store_true', help='Use relative links in STAC asset hrefs instead of absolute URLs (for troubleshooting)')
    parser.add_argument('--asset-type', choices=['txt', 'jpg'], default='txt', help='Type of asset to create for dummy STAC item (default: txt)')
    parser.add_argument('--asset-role', choices=['data', 'thumbnail'], default=None, help='Role of the asset (default: data for txt, thumbnail for jpg)')
    parser.add_argument('--timeout', type=int, default=300, help='Timeout for monitoring ingestion operation in seconds (default: 300)')
    parser.add_argument('--keep-artifacts', action='store_true', help='Keep artifacts (containers, collections, dummy data) after completion. Default: cleanup all artifacts.')
    return parser.parse_args()

def check_collection_exists(token, geocatalog_url, collection_id):
    """Check if a STAC collection exists."""
    collection_url = f"{geocatalog_url}/stac/collections/{collection_id}"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    params = {'api-version': '2025-04-30-preview'}
    
    try:
        response = requests.get(collection_url, headers=headers, params=params)
        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False
        else:
            print(f"Warning: Unexpected status code {response.status_code} when checking collection: {response.text}")
            return False
    except Exception as e:
        print(f"Error checking collection existence: {e}")
        return False

def create_stac_collection(token, geocatalog_url, collection_id):
    """Create a new STAC collection for troubleshooting."""
    collection_url = f"{geocatalog_url}/stac/collections"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    params = {'api-version': '2025-04-30-preview'}
    
    # Create a minimal STAC collection for troubleshooting
    collection_data = {
        "type": "Collection",
        "stac_version": "1.0.0",
        "id": collection_id,
        "title": f"Troubleshooting Collection ({collection_id})",
        "description": f"Automatically created collection for STAC ingestion troubleshooting and testing purposes. Collection ID: {collection_id}",
        "keywords": ["troubleshooting", "testing", "auto-created"],
        "license": "proprietary",
        "extent": {
            "spatial": {
                "bbox": [[-180, -90, 180, 90]]
            },
            "temporal": {
                "interval": [["1900-01-01T00:00:00Z", None]]
            }
        },
        "providers": [
            {
                "name": "STAC Ingestion Troubleshooter",
                "roles": ["processor"],
                "description": "Automatically created for testing STAC item ingestion"
            }
        ]
    }
    
    try:
        response = requests.post(collection_url, headers=headers, params=params, json=collection_data)
        if response.status_code == 201:
            print(f"✅ Successfully created collection '{collection_id}'")
            return True
        elif response.status_code == 202:
            print(f"✅ Collection creation accepted and is in progress for '{collection_id}'")
            print("⏳ Waiting for collection creation to complete...")
            
            # Get operation ID to monitor creation progress
            response_data = response.json()
            operation_id = response_data.get("id")
            
            if operation_id:
                print(f"   Operation ID: {operation_id}")
                
                # Monitor the collection creation operation
                max_wait_time = 60  # Wait up to 60 seconds
                start_time = time.time()
                
                while time.time() - start_time < max_wait_time:
                    time.sleep(5)  # Check every 5 seconds
                    
                    # Check if collection now exists
                    if check_collection_exists(token, geocatalog_url, collection_id):
                        print(f"✅ Collection '{collection_id}' creation completed successfully")
                        return True
                    
                print(f"⏳ Collection creation is taking longer than expected, continuing anyway...")
                print(f"   You can check the status manually if needed")
                return True
            else:
                print(f"✅ Collection creation accepted (no operation ID returned)")
                return True
        elif response.status_code == 409:
            print(f"ℹ️  Collection '{collection_id}' already exists")
            return True
        else:
            print(f"❌ Failed to create collection. Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating collection: {e}")
        return False

def ensure_collection_exists(token, geocatalog_url, collection_id):
    """Ensure a collection exists, create it if it doesn't."""
    print(f"🔍 Checking if collection '{collection_id}' exists...")
    
    if check_collection_exists(token, geocatalog_url, collection_id):
        print(f"✅ Collection '{collection_id}' already exists")
        return True
    else:
        print(f"📝 Collection '{collection_id}' not found, creating it...")
        return create_stac_collection(token, geocatalog_url, collection_id)

def check_container_exists(blob_service_client, container_name):
    """Check if a storage container exists."""
    try:
        container_client = blob_service_client.get_container_client(container_name)
        container_client.get_container_properties()
        return True
    except Exception:
        return False

def create_storage_container(blob_service_client, container_name):
    """Create a new storage container."""
    try:
        container_client = blob_service_client.get_container_client(container_name)
        container_client.create_container()
        print(f"✅ Successfully created container '{container_name}'")
        return True
    except Exception as e:
        if "ContainerAlreadyExists" in str(e):
            print(f"ℹ️  Container '{container_name}' already exists")
            return True
        else:
            print(f"❌ Error creating container: {e}")
            return False

def ensure_container_exists(blob_service_client, container_name, user_specified=False):
    """Ensure a container exists, create it if it doesn't (unless user specified and it doesn't exist)."""
    if user_specified:
        print(f"🔍 Verifying user-specified container '{container_name}' exists...")
        if check_container_exists(blob_service_client, container_name):
            print(f"✅ Container '{container_name}' exists")
            return True
        else:
            print(f"❌ User-specified container '{container_name}' not found")
            print("\nTroubleshooting tips:")
            print("  - Verify the container name is correct")
            print("  - Check if the container exists in your storage account")
            print("  - Ensure you have the right permissions to access the container")
            return False
    else:
        print(f"🔍 Checking if container '{container_name}' exists...")
        if check_container_exists(blob_service_client, container_name):
            print(f"✅ Container '{container_name}' already exists")
            return True
        else:
            print(f"📝 Container '{container_name}' not found, creating it...")
            return create_storage_container(blob_service_client, container_name)

def delete_stac_collection(token, geocatalog_url, collection_id):
    """Delete a STAC collection."""
    collection_url = f"{geocatalog_url}/stac/collections/{collection_id}"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    params = {'api-version': '2025-04-30-preview'}
    
    try:
        response = requests.delete(collection_url, headers=headers, params=params)
        if response.status_code in [200, 204]:
            print(f"✅ Successfully deleted STAC collection '{collection_id}'")
            return True
        elif response.status_code == 202:
            print(f"✅ STAC collection deletion accepted and is in progress for '{collection_id}'")
            # For cleanup purposes, accept async deletion as success
            # The collection will be deleted eventually
            return True
        elif response.status_code == 404:
            print(f"ℹ️  STAC collection '{collection_id}' not found (already deleted)")
            return True
        else:
            print(f"⚠️ WARNING: Failed to delete STAC collection. Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"⚠️ WARNING: Error deleting STAC collection: {e}")
        return False

def delete_stac_item(token, geocatalog_url, collection_id, item_id):
    """Delete a STAC item from a collection."""
    item_url = f"{geocatalog_url}/stac/collections/{collection_id}/items/{item_id}"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    params = {'api-version': '2025-04-30-preview'}
    
    try:
        response = requests.delete(item_url, headers=headers, params=params)
        if response.status_code in [200, 204]:
            print(f"✅ Successfully deleted STAC item '{item_id}'")
            return True
        elif response.status_code == 202:
            print(f"✅ STAC item deletion accepted and is in progress for '{item_id}'")
            # For cleanup purposes, accept async deletion as success
            # The item will be deleted eventually
            return True
        elif response.status_code == 404:
            print(f"ℹ️  STAC item '{item_id}' not found (already deleted)")
            return True
        else:
            print(f"⚠️ WARNING: Failed to delete STAC item. Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"⚠️ WARNING: Error deleting STAC item: {e}")
        return False

def delete_storage_container(blob_service_client, container_name):
    """Delete a storage container and all its contents."""
    try:
        container_client = blob_service_client.get_container_client(container_name)
        container_client.delete_container()
        print(f"✅ Successfully deleted container '{container_name}' and all its contents")
        return True
    except Exception as e:
        if "ContainerNotFound" in str(e):
            print(f"ℹ️  Container '{container_name}' not found (already deleted)")
            return True
        else:
            print(f"⚠️ WARNING: Error deleting container: {e}")
            return False

def delete_blob(blob_service_client, container_name, blob_name):
    """Delete a specific blob from a container."""
    try:
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        blob_client.delete_blob()
        print(f"✅ Successfully deleted blob '{blob_name}'")
        return True
    except Exception as e:
        if "BlobNotFound" in str(e):
            print(f"ℹ️  Blob '{blob_name}' not found (already deleted)")
            return True
        else:
            print(f"⚠️ WARNING: Error deleting blob '{blob_name}': {e}")
            return False

def cleanup_artifacts(cleanup_info, args):
    """
    Clean up test artifacts based on what was created and user preferences.
    
    Data Protection Behavior:
    - If we created a new container, we delete the entire container
    - If container existed before, we only delete our dummy blobs (preserves user data)
    - If we created a new collection, we delete the entire collection  
    - If collection existed before, we only delete our dummy STAC items (preserves user data)
    """
    if args.keep_artifacts:
        print("\n=== Keeping Artifacts (--keep-artifacts specified) ===")
        print("The following artifacts have been preserved for your inspection:")
        
        if cleanup_info.get('container_created'):
            print(f"📦 Container: {cleanup_info['container_name']}")
            print(f"   URL: https://{cleanup_info['storage_account']}.blob.core.windows.net/{cleanup_info['container_name']}")
            
        if cleanup_info.get('collection_created'):
            print(f"📚 Collection: {cleanup_info['collection_id']}")
            print(f"   URL: {cleanup_info['geocatalog_url']}/collections/{cleanup_info['collection_id']}")
            
        if cleanup_info.get('dummy_created'):
            print(f"📄 Dummy STAC item: {cleanup_info['item_id']}")
            print(f"   Blob: {cleanup_info['blob_name']}")
            if cleanup_info.get('asset_blob_name'):
                print(f"   Asset: {cleanup_info['asset_blob_name']}")
        
        print("\n💡 Remember to clean up these artifacts manually when you're done!")
        return True
    
    print("\n=== Cleaning Up Artifacts ===")
    print("Removing artifacts to keep your environment clean...")
    
    cleanup_success = True
    
    try:
        # Get necessary credentials
        credential = cleanup_info['credential']
        token = credential.get_token("https://geocatalog.spatio.azure.com/.default").token
        blob_service_client = cleanup_info['blob_service_client']
        
        # Delete STAC item if it was created (regardless of whether collection was created by us)
        if cleanup_info.get('dummy_created') and cleanup_info.get('item_id'):
            print(f"🗑️  Deleting STAC item '{cleanup_info['item_id']}' (dummy data created by this script)...")
            success = delete_stac_item(token, cleanup_info['geocatalog_url'], 
                                     cleanup_info['collection_id'], cleanup_info['item_id'])
            if not success:
                cleanup_success = False
        
        # Give a moment for async operations to start
        import time
        time.sleep(1)
        
        # Delete collection if it was created by us (only if we created the entire collection)
        if cleanup_info.get('collection_created'):
            print(f"🗑️  Deleting collection '{cleanup_info['collection_id']}' (created by this script)...")
            success = delete_stac_collection(token, cleanup_info['geocatalog_url'], 
                                           cleanup_info['collection_id'])
            if not success:
                cleanup_success = False
        
        # Handle container cleanup: only delete entire container if we created it
        # If container existed before, only delete our dummy blobs
        if cleanup_info.get('container_created'):
            # We created the container, so delete the entire container
            print(f"🗑️  Deleting container '{cleanup_info['container_name']}' (created by this script)...")
            success = delete_storage_container(blob_service_client, cleanup_info['container_name'])
            if not success:
                cleanup_success = False
        elif cleanup_info.get('dummy_created'):
            # Container existed before, only delete the dummy blobs we created
            print(f"🗑️  Deleting dummy blobs from existing container '{cleanup_info['container_name']}' (preserving other data)...")
            
            # Delete the STAC item blob
            if cleanup_info.get('blob_name'):
                success = delete_blob(blob_service_client, cleanup_info['container_name'], cleanup_info['blob_name'])
                if not success:
                    cleanup_success = False
            
            # Delete the asset blob if it exists
            if cleanup_info.get('asset_blob_name'):
                success = delete_blob(blob_service_client, cleanup_info['container_name'], cleanup_info['asset_blob_name'])
                if not success:
                    cleanup_success = False
        
        if cleanup_success:
            print("✅ All artifacts cleaned up successfully!")
            print("   (Note: Some deletions may still be processing asynchronously)")
        else:
            print("⚠️ Some artifacts could not be cleaned up automatically.")
            print("   Please check and clean them manually if needed.")
            
        return cleanup_success
        
    except Exception as e:
        print(f"⚠️ WARNING: Error during cleanup: {e}")
        print("Some artifacts may need to be cleaned up manually.")
        return False


def validate_storage_account_access(credential, storage_account_name):
    """Validate that the storage account exists and is accessible."""
    print(f"\n=== Validating storage account access ===")
    print(f"Checking access to storage account: {storage_account_name}")
    
    try:
        # DNS resolution and connectivity check
        hostname = f"{storage_account_name}.blob.core.windows.net"
        
        # Set a short timeout for DNS resolution
        socket.setdefaulttimeout(5)
        try:
            socket.gethostbyname(hostname)
            print(f"✓ Storage account endpoint accessible")
        except socket.gaierror as dns_error:
            print(f"❌ ERROR: Storage account '{storage_account_name}' does not exist or DNS resolution failed")
            print(f"DNS error: {dns_error}")
            print("\nTroubleshooting tips:")
            print(f"  - Verify the storage account name '{storage_account_name}' is correct")
            print("  - Check if the storage account exists in your Azure subscription")
            print("  - Ensure you're connected to the correct Azure subscription")
            raise Exception(f"Storage account '{storage_account_name}' does not exist")
        finally:
            socket.setdefaulttimeout(None)  # Reset to default
        
        # Azure SDK authentication test
        print("Checking Azure authentication and permissions...")
        account_url = f"https://{storage_account_name}.blob.core.windows.net"
        blob_service_client = azure.storage.blob.BlobServiceClient(
            account_url=account_url,
            credential=credential
        )
        
        # Try to list containers with a simple approach
        try:
            # This should fail fast if there are permission issues
            container_list = list(blob_service_client.list_containers(results_per_page=1))
            print(f"✓ Successfully accessed storage account '{storage_account_name}'")
            return blob_service_client
        except Exception as list_error:
            error_msg = str(list_error).lower()
            if "forbidden" in error_msg or "unauthorized" in error_msg or "access denied" in error_msg:
                print(f"❌ ERROR: Access denied to storage account '{storage_account_name}'")
                print("\nTroubleshooting tips:")
                print("  - Verify you have the required permissions on the storage account")
                print("  - You need 'Storage Blob Data Contributor' role or equivalent")
                print("  - Check with your Azure administrator about storage account permissions")
                raise Exception(f"Access denied to storage account '{storage_account_name}'")
            else:
                # For other errors, try a simpler test
                print("List containers failed, trying account information check...")
                try:
                    account_info = blob_service_client.get_account_information()
                    print(f"✓ Successfully accessed storage account '{storage_account_name}' (account info check)")
                    return blob_service_client
                except Exception as account_error:
                    print(f"❌ ERROR: Failed to access storage account: {account_error}")
                    raise Exception(f"Cannot access storage account '{storage_account_name}': {account_error}")
        
    except Exception as e:
        if "does not exist" in str(e) or "DNS resolution failed" in str(e) or "Connection timeout" in str(e) or "Access denied" in str(e):
            # Re-raise our custom exceptions with clean messages
            raise
        
        error_message = str(e).lower()
        
        # Check for specific error types
        if "does not exist" in error_message or "could not be resolved" in error_message:
            print(f"❌ ERROR: Storage account '{storage_account_name}' does not exist")
            print("\nTroubleshooting tips:")
            print(f"  - Verify the storage account name '{storage_account_name}' is correct")
            print("  - Check if the storage account exists in your Azure subscription")
            print("  - Ensure you're connected to the correct Azure subscription")
        elif "forbidden" in error_message or "unauthorized" in error_message or "access denied" in error_message:
            print(f"❌ ERROR: Access denied to storage account '{storage_account_name}'")
            print("\nTroubleshooting tips:")
            print("  - Verify you have the required permissions on the storage account")
            print("  - You need 'Storage Blob Data Contributor' role or equivalent")
            print("  - Check with your Azure administrator about storage account permissions")
        elif "timeout" in error_message:
            print(f"❌ ERROR: Connection timeout when accessing storage account '{storage_account_name}'")
            print("\nTroubleshooting tips:")
            print("  - Check your network connection")
            print("  - Verify the storage account name is correct")
            print("  - Try again in a few minutes")
        else:
            print(f"❌ ERROR: Failed to access storage account '{storage_account_name}': {str(e)}")
            print("\nTroubleshooting tips:")
            print("  - Verify the storage account name is correct")
            print("  - Check your permissions on the storage account")
            print("  - Ensure you're logged into the correct Azure subscription")
        
        raise Exception(f"Cannot access storage account '{storage_account_name}'")

def validate_geocatalog_access(credential, geocatalog_url):
    """Validate that the GeoCatalog exists and is accessible."""
    print(f"\n=== Validating GeoCatalog access ===")
    print(f"Checking access to GeoCatalog: {geocatalog_url}")
    
    try:
        # Parse and validate URL format
        parsed_url = urlparse(geocatalog_url)
        
        if not parsed_url.scheme or not parsed_url.netloc:
            print(f"❌ ERROR: Invalid GeoCatalog URL format: {geocatalog_url}")
            print("\nTroubleshooting tips:")
            print("  - Ensure the URL includes https:// protocol")
            print("  - Verify the URL format: https://your-geocatalog.geocatalog.spatio.azure.com")
            print("  - Check for typos in the GeoCatalog URL")
            raise Exception(f"Invalid GeoCatalog URL format")
        
        hostname = parsed_url.netloc
        
        # DNS resolution and connectivity check
        socket.setdefaulttimeout(5)
        try:
            socket.gethostbyname(hostname)
            print(f"✓ GeoCatalog endpoint accessible")
        except socket.gaierror as dns_error:
            print(f"❌ ERROR: GeoCatalog hostname '{hostname}' does not resolve")
            print(f"DNS error: {dns_error}")
            print("\nTroubleshooting tips:")
            print(f"  - Verify the GeoCatalog URL '{geocatalog_url}' is correct")
            print("  - Check if the GeoCatalog instance exists and is running")
            print("  - Ensure you have the correct GeoCatalog URL from your administrator")
            raise Exception(f"GeoCatalog hostname '{hostname}' does not exist")
        finally:
            socket.setdefaulttimeout(None)
        
        # Authentication and API access test
        print("Checking GeoCatalog API authentication and permissions...")
        try:
            # Get access token
            access_token = credential.get_token(f"{MPCPRO_APP_ID}/.default")
            
            # Try to access a simple API endpoint (collections list)
            collections_url = f"{geocatalog_url}/stac/collections"
            headers = {
                'Authorization': f'Bearer {access_token.token}',
                'Content-Type': 'application/json'
            }
            params = {'api-version': API_VERSION}
            
            response = requests.get(collections_url, headers=headers, params=params, timeout=15)
            
            if response.status_code == 200:
                print(f"✓ Successfully authenticated and accessed GeoCatalog API")
                collections_data = response.json()
                collection_count = len(collections_data.get('value', []))
                print(f"  Found {collection_count} existing collections")
                return True
            elif response.status_code == 401:
                print(f"❌ ERROR: Authentication failed for GeoCatalog")
                print("\nTroubleshooting tips:")
                print("  - Verify you have access to this GeoCatalog instance")
                print("  - Check if your Azure account has the required permissions")
                print("  - Ensure you're logged into the correct Azure tenant")
                raise Exception(f"Authentication failed for GeoCatalog")
            elif response.status_code == 403:
                print(f"❌ ERROR: Access denied to GeoCatalog")
                print("\nTroubleshooting tips:")
                print("  - Verify you have the required permissions for this GeoCatalog")
                print("  - Check with your GeoCatalog administrator about access rights")
                print("  - Ensure your account has the necessary roles assigned")
                raise Exception(f"Access denied to GeoCatalog")
            elif response.status_code == 404:
                print(f"❌ ERROR: GeoCatalog API endpoint not found")
                print(f"Response: {response.text}")
                print("\nTroubleshooting tips:")
                print("  - Verify the GeoCatalog URL is correct")
                print("  - Check if this is a valid GeoCatalog instance")
                print("  - The API version might be incompatible")
                raise Exception(f"GeoCatalog API endpoint not found")
            else:
                print(f"❌ ERROR: Unexpected response from GeoCatalog API: {response.status_code}")
                print(f"Response: {response.text}")
                raise Exception(f"Unexpected GeoCatalog API response: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"❌ ERROR: GeoCatalog API request timeout")
            print("\nTroubleshooting tips:")
            print("  - The GeoCatalog instance might be overloaded or slow")
            print("  - Check your network connection stability")
            print("  - Try again in a few minutes")
            raise Exception(f"GeoCatalog API timeout")
        except Exception as api_error:
            if "Authentication failed" in str(api_error) or "Access denied" in str(api_error) or "API endpoint not found" in str(api_error) or "API timeout" in str(api_error):
                # Re-raise our custom exceptions
                raise
            
            print(f"❌ ERROR: Failed to access GeoCatalog API: {api_error}")
            print("\nTroubleshooting tips:")
            print("  - Verify the GeoCatalog URL is correct")
            print("  - Check your authentication credentials")
            print("  - Ensure the GeoCatalog instance is running")
            raise Exception(f"Cannot access GeoCatalog API: {api_error}")
            
    except Exception as e:
        if "Invalid GeoCatalog URL format" in str(e) or "does not exist" in str(e) or "Connection timeout" in str(e) or "Authentication failed" in str(e) or "Access denied" in str(e) or "API endpoint not found" in str(e) or "API timeout" in str(e):
            # Re-raise our custom exceptions with clean messages
            raise
        
        print(f"❌ ERROR: GeoCatalog validation failed: {str(e)}")
        print("\nTroubleshooting tips:")
        print("  - Verify the GeoCatalog URL is correct")
        print("  - Check your network connection")
        print("  - Ensure you have proper access to the GeoCatalog")
        raise Exception(f"Cannot access GeoCatalog: {str(e)}")

def setup_authentication():
    """Set up authentication for Azure."""
    print("\n=== Setting up authentication ===")
    
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
    print("\n=== Generating SAS token ===")
    
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
    print("\n=== Creating ingestion source ===")
    
    try:
        # Obtain access token for GeoCatalog
        access_token = credential.get_token(f"{MPCPRO_APP_ID}/.default")
        
        # First, check if an ingestion source already exists for this container
        print("Checking for existing ingestion source...")
        ingestion_sources_endpoint = f"{geocatalog_url}/inma/ingestion-sources"
        
        response = requests.get(
            ingestion_sources_endpoint,
            headers={"Authorization": f"Bearer {access_token.token}"},
            params={"api-version": API_VERSION}
        )
        
        existing_source = None
        if response.status_code == 200:
            sources = response.json()["value"]
            
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
            
            # Check if the SAS token is expired or will expire soon (within 1 hour)
            should_refresh = False
            try:
                # Get expiration from the API response (much more reliable than parsing SAS token)
                connection_info = existing_source.get("connectionInfo", {})
                expiration_str = connection_info.get("expiration")
                
                if expiration_str:
                    # Parse the expiration time (format: 2024-10-06T11:17:00.0000000Z)
                    sas_expiry = datetime.fromisoformat(expiration_str.replace("Z", "+00:00"))
                    
                    current_time = datetime.now(timezone.utc)
                    time_until_expiry = sas_expiry - current_time
                    
                    if time_until_expiry.total_seconds() <= 3600:  # Less than 1 hour
                        minutes_left = max(0, int(time_until_expiry.total_seconds() / 60))
                        if minutes_left <= 0:
                            print("⏰ SAS token has expired, refreshing...")
                        else:
                            print(f"⏰ SAS token expires in {minutes_left} minutes, refreshing...")
                        should_refresh = True
                    else:
                        hours_left = int(time_until_expiry.total_seconds() / 3600)
                        print(f"✓ Existing SAS token is valid (expires in {hours_left} hours)")
                        return existing_source['id']
                else:
                    # No expiration found in API response, refresh to be safe
                    print("⏰ Cannot find SAS token expiration in API response, refreshing to be safe...")
                    should_refresh = True
                        
            except Exception as parse_error:
                # If we can't parse the expiry, assume it might be expired and refresh
                print(f"⏰ Cannot determine SAS token expiry ({parse_error}), refreshing to be safe...")
                should_refresh = True
            
            if should_refresh:
                # Delete the existing source
                delete_response = requests.delete(
                    f"{ingestion_sources_endpoint}/{existing_source['id']}",
                    headers={"Authorization": f"Bearer {access_token.token}"},
                    params={"api-version": API_VERSION}
                )
                
                if delete_response.status_code in [200, 204]:
                    print("✓ Successfully deleted existing ingestion source")
                else:
                    print("⚠️ WARNING: Could not delete existing ingestion source, will try to create new one anyway...")
        else:
            print("ℹ️ No existing ingestion source found for this container")
        
        # Create new ingestion source
        print("Creating new ingestion source...")
        payload = {
            "kind": "SasToken",
            "connectionInfo": {
                "containerUrl": container_url,
                "sasToken": sas_token,
            }
        }
        
        create_response = requests.post(
            ingestion_sources_endpoint,
            json=payload,
            headers={"Authorization": f"Bearer {access_token.token}"},
            params={"api-version": API_VERSION}
        )
        
        if create_response.status_code == 201:
            new_source_id = create_response.json()["id"]
            print(f"✓ Successfully created ingestion source with ID: {new_source_id}")
            return new_source_id
        else:
            print(f"❌ ERROR: Failed to create ingestion source: {create_response.status_code}")
            print(f"Response: {create_response.text}")
            print("\nTroubleshooting tips:")
            print("  - Check your GeoCatalog URL is correct")
            print("  - Verify you have permission to create ingestion sources")
            print("  - Ensure the SAS token is valid and has the required permissions")
            raise Exception("Failed to create ingestion source")

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

def process_stac_item(stac_item, storage_account, container, collection_id, geocatalog_url, use_relative_links=False):
    """Process a STAC item to ensure all asset hrefs are absolute URLs and collection links are correct."""
    # Update collection ID
    stac_item["collection"] = collection_id
    print(f"✓ Updated collection ID to: {collection_id}")

    # Ensure assets have absolute hrefs (unless relative links are specifically requested)
    if "assets" in stac_item:
        for asset_key, asset in stac_item["assets"].items():
            if "href" in asset:
                if use_relative_links:
                    # Keep relative link if it's already relative, or make it relative if it's absolute
                    parsed_url = urlparse(asset["href"])
                    if parsed_url.scheme and parsed_url.netloc:
                        # Extract just the blob path from absolute URL
                        blob_path = parsed_url.path.lstrip('/')
                        # Remove container name from path if present
                        if blob_path.startswith(f"{container}/"):
                            blob_path = blob_path[len(f"{container}/"):]
                        asset["href"] = blob_path
                        print(f"Converting absolute href to relative: '{blob_path}'")
                    else:
                        print(f"Keeping relative href: '{asset['href']}'")
                else:
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

def read_stac_item(blob_service_client, container_name, blob_name, collection_id, geocatalog_url, storage_account_name, use_relative_links=False):
    """Read and validate the STAC item from blob storage."""
    print("\n=== Reading STAC item ===")
    
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
        stac_item = process_stac_item(stac_item, storage_account_name, container_name, collection_id, geocatalog_url, use_relative_links)
        
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
    print("\n=== Ingesting STAC item ===")
    
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
    print("\n=== Monitoring ingestion operation ===")
    
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

def create_dummy_stac_item(blob_service_client, container_name, blob_name, collection_id, geocatalog_url, storage_account_name, use_relative_links=False, asset_type='txt', asset_role=None):
    """Create a dummy STAC item for testing."""
    print("\n=== Creating a dummy STAC item ===")
    
    try:
        # Extract directory path from blob_name if it exists
        blob_dir = ""
        if "/" in blob_name:
            blob_dir = blob_name.rsplit("/", 1)[0] + "/"
        
        # Determine asset role if not specified
        if asset_role is None:
            asset_role = 'thumbnail' if asset_type == 'jpg' else 'data'
        
        # Create asset based on type and role
        if asset_type == 'jpg':
            asset_blob_name = f"{blob_dir}dummy-{asset_role}.jpg"
            asset_config = {
                "href": asset_blob_name,
                "title": f"Dummy {asset_role.title()}",
                "description": f"A JPG image for testing ingestion as {asset_role}",
                "type": "image/jpeg",
                "roles": [asset_role]
            }
            asset_key = asset_role
        else:  # default to txt
            asset_blob_name = f"{blob_dir}dummy-{asset_role}.txt"
            asset_config = {
                "href": asset_blob_name,
                "title": f"Dummy {asset_role.title()}",
                "description": f"A text file for testing ingestion as {asset_role}",
                "type": "text/plain",
                "roles": [asset_role]
            }
            asset_key = asset_role
        
        # Create a simple STAC item with the specified asset type
        stac_item = {
            "type": "Feature",
            "stac_version": "1.0.0",
            "id": f"sample-item-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "properties": {
                "datetime": datetime.now(timezone.utc).isoformat(),
                "title": "Sample STAC Item",
                "description": f"A sample STAC item for testing ingestion with {asset_type.upper()} asset as {asset_role}"
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
                asset_key: asset_config
            },
            "collection": collection_id
        }

        # Process STAC item to ensure absolute hrefs and correct links
        stac_item = process_stac_item(stac_item, storage_account_name, container_name, collection_id, geocatalog_url, use_relative_links)
        
        # Create a blob client and upload the STAC item
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        blob_client.upload_blob(json.dumps(stac_item, indent=2), overwrite=True)
        
        # Create the asset file
        asset_blob_client = blob_service_client.get_blob_client(container=container_name, blob=asset_blob_name)
        
        if asset_type == 'jpg':
            # Create a minimal valid JPG file (1x1 pixel red image)
            # JPG header for a 1x1 red pixel image
            jpg_data = bytes([
                0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01, 0x01, 0x00, 0x48,
                0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43, 0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08,
                0x07, 0x07, 0x07, 0x09, 0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
                0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20, 0x24, 0x2E, 0x27, 0x20,
                0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29, 0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27,
                0x39, 0x3D, 0x38, 0x32, 0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x11, 0x08, 0x00, 0x01,
                0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0x02, 0x11, 0x01, 0x03, 0x11, 0x01, 0xFF, 0xC4, 0x00, 0x14,
                0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x08, 0xFF, 0xC4, 0x00, 0x14, 0x10, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xDA, 0x00, 0x0C, 0x03, 0x01, 0x00, 0x02,
                0x11, 0x03, 0x11, 0x00, 0x3F, 0x00, 0x50, 0xFF, 0xD9
            ])
            asset_blob_client.upload_blob(jpg_data, overwrite=True)
            print(f"✓ Created dummy JPG {asset_role} asset: {asset_blob_name}")
        else:
            # Simple text content
            text_content = f"This is a dummy text file used for testing STAC item ingestion in Microsoft Planetary Computer Pro as {asset_role}."
            asset_blob_client.upload_blob(text_content, overwrite=True)
            print(f"✓ Created dummy text {asset_role} asset: {asset_blob_name}")
        
        # Upload the STAC item to blob storage
        stac_item_json = json.dumps(stac_item, indent=2)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        blob_client.upload_blob(stac_item_json, overwrite=True)
        print(f"✓ Created dummy STAC item: {blob_name}")
        
        # Verify the asset file is accessible
        try:
            asset_props = asset_blob_client.get_blob_properties()
            print(f"✓ Verified {asset_type.upper()} asset exists: {asset_blob_name} ({asset_props.size} bytes)")
        except Exception as e:
            print(f"⚠️ WARNING: Could not verify {asset_type.upper()} asset accessibility: {str(e)}")
        
        return stac_item, asset_blob_name
        
    except Exception as e:
        print(f"❌ ERROR: Failed to create dummy STAC item: {str(e)}")
        raise

def main():
    """Main function orchestrating the troubleshooting steps."""
    args = parse_arguments()
    
    print("=== STAC Item Ingestion Troubleshooter ===")
    print("This script will help you troubleshoot ingestion issues with Microsoft Planetary Computer Pro.\n")
    
    # Initialize cleanup tracking
    cleanup_info = {
        'container_created': False,
        'collection_created': False,
        'dummy_created': False,
        'container_name': None,
        'collection_id': None,
        'storage_account': None,
        'geocatalog_url': None,
        'blob_name': None,
        'asset_blob_name': None,
        'item_id': None,
        'credential': None,
        'blob_service_client': None
    }
    
    # Define variables
    print("=== Defining variables ===")
    geocatalog_url = args.geocatalog_url.rstrip('/')
    storage_account_name = args.storage_account
    
    # Store in cleanup info
    cleanup_info['geocatalog_url'] = geocatalog_url
    cleanup_info['storage_account'] = storage_account_name
    
    # Handle optional container - use default if not provided
    if args.container:
        container_name = args.container
        user_specified_container = True
        print(f"Using provided container: {container_name}")
    else:
        container_name = "troubleshooting-container"
        user_specified_container = False
        print(f"No container provided, using default: {container_name}")
    
    cleanup_info['container_name'] = container_name
    
    # Handle optional collection ID - use default if not provided
    if args.collection_id:
        collection_id = args.collection_id
        user_specified_collection = True
        print(f"Using provided collection ID: {collection_id}")
    else:
        collection_id = "troubleshooting-collection"
        user_specified_collection = False
        print(f"No collection ID provided, using default: {collection_id}")
    
    cleanup_info['collection_id'] = collection_id
    
    # If blob isn't provided, generate a default blob path and create dummy
    if not args.blob:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        blob_name = f"dummy-stac-item-{timestamp}.json"
        create_dummy = True
        print(f"No blob path provided, will create dummy STAC item at: {blob_name}")
    else:
        blob_name = args.blob
        create_dummy = False
    
    cleanup_info['blob_name'] = blob_name
    container_url = f"https://{storage_account_name}.blob.core.windows.net/{container_name}"
    
    print(f"GeoCatalog URL: {geocatalog_url}")
    print(f"Storage Account: {storage_account_name}")
    print(f"Container: {container_name}")
    print(f"Collection ID: {collection_id}")
    print(f"Blob: {blob_name}")
    print(f"Container URL: {container_url}")
    
    if not args.keep_artifacts:
        print("🧹 Cleanup mode: Artifacts will be automatically removed after completion")
    else:
        print("📌 Keep artifacts mode: Artifacts will be preserved for inspection")
        
    print("✓ Variables defined")
    
    try:
        # Step 2: Set up authentication
        credential = setup_authentication()
        cleanup_info['credential'] = credential
        
        # Step 2.4: Validate GeoCatalog access
        validate_geocatalog_access(credential, geocatalog_url)
        
        # Step 2.5: Validate storage account access
        blob_service_client = validate_storage_account_access(credential, storage_account_name)
        cleanup_info['blob_service_client'] = blob_service_client
        
        # Step 2.6: Set up storage and ensure container exists
        print("\n=== Setting up Azure Storage ===")
        
        # Check if container exists before ensuring it exists
        container_existed_before = check_container_exists(blob_service_client, container_name)
        
        # Ensure container exists
        if not ensure_container_exists(blob_service_client, container_name, user_specified_container):
            print("❌ Failed to ensure container exists. Cannot proceed.")
            sys.exit(1)
        
        # Track if we created the container
        if not user_specified_container and not container_existed_before:
            cleanup_info['container_created'] = True
        
        # Get access token for collection management
        token = credential.get_token("https://geocatalog.spatio.azure.com/.default").token
        
        # Step 2.7: Ensure STAC collection exists
        print("\n=== Ensuring STAC collection exists ===")
        
        # Check if collection exists before ensuring it exists
        collection_existed_before = check_collection_exists(token, geocatalog_url, collection_id)
        
        if not ensure_collection_exists(token, geocatalog_url, collection_id):
            print("❌ Failed to ensure collection exists. Cannot proceed with ingestion.")
            cleanup_artifacts(cleanup_info, args)
            sys.exit(1)
        
        # Track if we created the collection
        if not user_specified_collection and not collection_existed_before:
            cleanup_info['collection_created'] = True
        
        # Step 3: Generate SAS token (reusing the blob_service_client we already created)
        print("\n=== Generating SAS token ===")
        
        try:
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
        except Exception as e:
            print(f"❌ ERROR: Failed to generate SAS token: {str(e)}")
            print("\nTroubleshooting tips:")
            print("  - Verify your storage account name is correct")
            print("  - Confirm you have the right permissions on the storage account")
            print("  - Check if your account allows SAS token generation")
            cleanup_artifacts(cleanup_info, args)
            raise
        
        # Check if blob exists, create dummy if it doesn't exist
        blob_exists = False
        if not create_dummy:  # Only check if we're not already planning to create a dummy
            try:
                blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
                blob_client.get_blob_properties()
                blob_exists = True
                print(f"✓ Found existing blob: {blob_name}")
            except Exception as e:
                print(f"\n⚠️ WARNING: Blob {blob_name} not found: {str(e)}")
                print("Will create dummy STAC item...")
                create_dummy = True
        
        # Create dummy STAC item if needed
        if create_dummy:
            print("Creating dummy STAC item...")
            stac_item, asset_blob_name = create_dummy_stac_item(blob_service_client, container_name, blob_name, collection_id, geocatalog_url, storage_account_name, args.use_relative_links, args.asset_type, args.asset_role)
            cleanup_info['dummy_created'] = True
            cleanup_info['item_id'] = stac_item['id']
            cleanup_info['asset_blob_name'] = asset_blob_name
        
        # Step 4: Create an ingestion source
        ingestion_source_id = create_ingestion_source(credential, geocatalog_url, container_url, sas_token)
        
        # Step 5: Read the STAC item
        stac_item = read_stac_item(blob_service_client, container_name, blob_name, collection_id, geocatalog_url, storage_account_name, args.use_relative_links)
        
        # Update cleanup info with the item ID from the STAC item
        if not cleanup_info.get('item_id'):
            cleanup_info['item_id'] = stac_item['id']
        
        # Step 6: Ingest the STAC item
        operation_id, operation_location = ingest_stac_item(credential, geocatalog_url, collection_id, stac_item)
        
        # Step 7: Monitor the ingestion operation
        success = monitor_ingestion(credential, operation_location, geocatalog_url, collection_id, stac_item, args.timeout)
        
        # Step 8: Cleanup or preserve artifacts
        cleanup_artifacts(cleanup_info, args)
        
        # Summary
        print("\n=== Troubleshooting summary ===")
        if success:
            print("✅ Ingestion process completed successfully!")
        else:
            print("⚠️ Ingestion process completed with warnings or failures.")
            
        if args.keep_artifacts:
            print(f"\nYou can view your collection in the GeoCatalog Explorer: {geocatalog_url}/collections/{collection_id}")
        
        # Exit with error code if ingestion was not successful
        if not success:
            sys.exit(1)
        
    except Exception as e:
        print("\n=== Troubleshooting summary ===")
        print(f"❌ Ingestion process failed: {str(e)}")
        
        # Attempt cleanup even on failure
        try:
            cleanup_artifacts(cleanup_info, args)
        except Exception as cleanup_error:
            print(f"⚠️ WARNING: Cleanup failed: {cleanup_error}")
        
        sys.exit(1)

if __name__ == "__main__":
    main()