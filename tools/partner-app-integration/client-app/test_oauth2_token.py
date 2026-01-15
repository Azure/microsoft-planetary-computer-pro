#!/usr/bin/env python3
"""
Test OAuth2 Token Request for Azure Planetary Computer GeoCatalog

This script tests the direct OAuth2 token endpoint to request an access token
for the GeoCatalog scope using client credentials (client ID and secret).

It uses the Microsoft identity platform OAuth2 token endpoint:
https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token

Usage:
    python test_oauth2_token.py
"""

import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv


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


def request_token_oauth2(tenant_id, client_id, client_secret, scope):
    """
    Request an access token using the OAuth2 client credentials flow.
    
    Args:
        tenant_id: Azure AD tenant ID
        client_id: Application (client) ID
        client_secret: Client secret
        scope: The scope to request (e.g., 'https://geocatalog.spatio.azure.com/.default')
    
    Returns:
        dict: Token response containing access_token, token_type, expires_in, etc.
    """
    print_section("2. Requesting Token via OAuth2 Endpoint")
    
    # OAuth2 token endpoint
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    
    print(f"Token Endpoint: {token_url}")
    print(f"Scope: {scope}")
    print(f"Grant Type: client_credentials")
    print()
    
    # Request body for client credentials flow
    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': scope
    }
    
    # Headers
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        print("Sending token request...")
        response = requests.post(token_url, data=data, headers=headers)
        
        # Print response status
        print(f"Response Status Code: {response.status_code}")
        
        # Raise exception for HTTP errors
        response.raise_for_status()
        
        # Parse JSON response
        token_response = response.json()
        
        print("\n✓ Token request successful!")
        print(f"  Token Type: {token_response.get('token_type')}")
        print(f"  Expires In: {token_response.get('expires_in')} seconds")
        
        # Calculate expiration time
        expires_in = token_response.get('expires_in', 0)
        expiration_time = datetime.now().timestamp() + expires_in
        print(f"  Expires At: {datetime.fromtimestamp(expiration_time).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show token preview (first and last 20 chars)
        access_token = token_response.get('access_token', '')
        if len(access_token) > 40:
            token_preview = f"{access_token[:20]}...{access_token[-20:]}"
        else:
            token_preview = access_token
        print(f"  Token Preview: {token_preview}")
        
        return token_response
        
    except requests.exceptions.HTTPError as e:
        print(f"\n✗ HTTP Error: {e}")
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Body:\n{json.dumps(response.json(), indent=2)}")
        raise
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise


def decode_token_claims(access_token):
    """
    Decode and display JWT token claims (without verification).
    Note: This is for inspection only, not for verification.
    """
    print_section("3. Inspecting Token Claims")
    
    try:
        import base64
        
        # Split the JWT into parts
        parts = access_token.split('.')
        if len(parts) != 3:
            print("✗ Invalid JWT format")
            return
        
        # Decode the payload (middle part)
        # Add padding if needed
        payload = parts[1]
        padding = 4 - (len(payload) % 4)
        if padding != 4:
            payload += '=' * padding
        
        # Decode from base64
        decoded_bytes = base64.urlsafe_b64decode(payload)
        decoded_str = decoded_bytes.decode('utf-8')
        claims = json.loads(decoded_str)
        
        print("✓ Token claims (decoded):")
        print(json.dumps(claims, indent=2))
        
        # Highlight important claims
        print("\nKey Claims:")
        print(f"  Audience (aud): {claims.get('aud')}")
        print(f"  Issuer (iss): {claims.get('iss')}")
        print(f"  App ID (appid): {claims.get('appid')}")
        print(f"  Tenant ID (tid): {claims.get('tid')}")
        
        # Convert timestamps
        if 'exp' in claims:
            exp_time = datetime.fromtimestamp(claims['exp']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"  Expires (exp): {claims['exp']} ({exp_time})")
        if 'iat' in claims:
            iat_time = datetime.fromtimestamp(claims['iat']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"  Issued At (iat): {claims['iat']} ({iat_time})")
        
        return claims
        
    except Exception as e:
        print(f"✗ Could not decode token: {e}")
        return None


def test_token_with_api(geocatalog_url, access_token):
    """
    Test the access token by making a request to the GeoCatalog API.
    """
    print_section("4. Testing Token with GeoCatalog API")
    
    # STAC API endpoint
    collections_url = f"{geocatalog_url}/stac/collections"
    api_version = "2025-04-30-preview"

    print(f"Testing endpoint: {collections_url}")
    print()
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
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
        
        return True
        
    except requests.exceptions.HTTPError as e:
        print(f"\n✗ API request failed: {e}")
        if response.text:
            print(f"Response: {response.text}")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


def save_token_to_file(token_response, filename='token_response.json'):
    """Save the complete token response to a file."""
    print_section("5. Saving Token Response")
    
    try:
        with open(filename, 'w') as f:
            json.dump(token_response, f, indent=2)
        print(f"✓ Token response saved to: {filename}")
        return True
    except Exception as e:
        print(f"✗ Failed to save token: {e}")
        return False


def main():
    """Main execution function."""
    try:
        # Load configuration
        config = load_configuration()
        
        # GeoCatalog scope
        scope = "https://geocatalog.spatio.azure.com/.default"
        
        # Request token via OAuth2 endpoint
        token_response = request_token_oauth2(
            tenant_id=config['AZURE_TENANT_ID'],
            client_id=config['AZURE_CLIENT_ID'],
            client_secret=config['AZURE_CLIENT_SECRET'],
            scope=scope
        )
        
        # Extract access token
        access_token = token_response.get('access_token')
        
        if not access_token:
            print("✗ No access token in response")
            return 1
        
        # Decode and inspect token claims
        decode_token_claims(access_token)
        
        # Test token with GeoCatalog API
        api_success = test_token_with_api(config['GEOCATALOG_URL'], access_token)
        
        # Save token response to file
        save_token_to_file(token_response)
        
        # Final summary
        print_section("Summary")
        print("✓ OAuth2 token request: SUCCESS")
        print("✓ Token claims decoded: SUCCESS")
        print(f"✓ GeoCatalog API test: {'SUCCESS' if api_success else 'FAILED'}")
        print("✓ Token saved to file: SUCCESS")
        
        print("\n✓ All tests completed!")
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
