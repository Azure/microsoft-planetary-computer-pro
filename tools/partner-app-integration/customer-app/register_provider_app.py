#!/usr/bin/env python3
"""
Customer App Registration Script

This script registers the provider's multi-tenant application in the customer's
Azure AD tenant and guides through the admin consent process.

Prerequisites:
- Azure CLI installed and authenticated to customer tenant
- Global Administrator or Application Administrator role
- .env file configured with provider app details

Usage:
    python register_provider_app.py
"""

import os
import sys
import json
import subprocess
import webbrowser
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm

console = Console()


def print_section(title):
    """Print a formatted section header."""
    console.print(f"\n[bold cyan]{'=' * 80}[/bold cyan]")
    console.print(f"[bold cyan]  {title}[/bold cyan]")
    console.print(f"[bold cyan]{'=' * 80}[/bold cyan]\n")


def load_configuration():
    """Load environment variables from .env file."""
    print_section("Loading Configuration")
    
    load_dotenv()
    
    config = {
        'CUSTOMER_TENANT_ID': os.getenv('CUSTOMER_TENANT_ID'),
        'PROVIDER_CLIENT_ID': os.getenv('PROVIDER_CLIENT_ID'),
        'PROVIDER_REDIRECT_URI': os.getenv('PROVIDER_REDIRECT_URI', 'https://localhost:8080/callback')
    }
    
    # Only check required values (redirect URI has a default)
    if not config['CUSTOMER_TENANT_ID'] or not config['PROVIDER_CLIENT_ID']:
        console.print("[red]❌ Missing required environment variables![/red]")
        console.print("Please configure .env file with:")
        console.print("  - CUSTOMER_TENANT_ID")
        console.print("  - PROVIDER_CLIENT_ID")
        sys.exit(1)
    
    console.print("✅ Configuration loaded successfully")
    console.print(f"   Customer Tenant: [green]{config['CUSTOMER_TENANT_ID'][:8]}...[/green]")
    console.print(f"   Provider App ID: [green]{config['PROVIDER_CLIENT_ID'][:8]}...[/green]")
    
    return config


def check_azure_cli():
    """Verify Azure CLI is installed and authenticated to customer tenant."""
    print_section("Checking Azure CLI")
    
    try:
        result = subprocess.run(['az', '--version'], 
                              capture_output=True, text=True, check=True)
        console.print("✅ Azure CLI is installed")
        
        # Check if logged in to correct tenant
        result = subprocess.run(['az', 'account', 'show'], 
                              capture_output=True, text=True, check=True)
        account_info = json.loads(result.stdout)
        current_tenant = account_info.get('tenantId')
        
        console.print(f"✅ Logged in as: [green]{account_info.get('user', {}).get('name')}[/green]")
        console.print(f"   Current tenant: [green]{current_tenant}[/green]")
        
        return current_tenant
        
    except subprocess.CalledProcessError:
        console.print("[red]❌ Azure CLI not found or not logged in[/red]")
        console.print("Please run: [yellow]az login[/yellow]")
        return None
    except FileNotFoundError:
        console.print("[red]❌ Azure CLI not installed[/red]")
        return None


def verify_tenant(config, current_tenant):
    """Verify we're logged into the customer tenant."""
    print_section("Verifying Tenant")
    
    expected_tenant = config['CUSTOMER_TENANT_ID']
    
    if current_tenant != expected_tenant:
        console.print(f"[yellow]⚠️  Tenant mismatch![/yellow]")
        console.print(f"   Expected: {expected_tenant}")
        console.print(f"   Current:  {current_tenant}")
        console.print("\nPlease login to the correct tenant:")
        console.print(f"   [yellow]az login --tenant {expected_tenant}[/yellow]")
        return False
    
    console.print("✅ Logged into correct customer tenant")
    return True


def check_existing_service_principal(app_id):
    """Check if service principal already exists in tenant."""
    print_section("Checking Existing Service Principal")
    
    check_cmd = [
        'az', 'ad', 'sp', 'list',
        '--filter', f"appId eq '{app_id}'",
        '--query', '[0].id',
        '-o', 'tsv'
    ]
    
    result = subprocess.run(check_cmd, capture_output=True, text=True)
    sp_id = result.stdout.strip()
    
    if sp_id:
        console.print(f"ℹ️  Service principal already exists")
        console.print(f"   Object ID: [green]{sp_id}[/green]")
        return sp_id
    else:
        console.print("ℹ️  Service principal not found in this tenant")
        return None


def create_service_principal(app_id):
    """Create service principal for the provider app in customer tenant."""
    print_section("Creating Service Principal")
    
    console.print(f"Creating service principal for app: [cyan]{app_id}[/cyan]")
    console.print("This registers the provider's app in your tenant...")
    
    create_cmd = [
        'az', 'ad', 'sp', 'create',
        '--id', app_id
    ]
    
    try:
        result = subprocess.run(create_cmd, capture_output=True, text=True, check=True)
        sp_info = json.loads(result.stdout)
        sp_id = sp_info['id']
        
        console.print(f"✅ Service principal created successfully!")
        console.print(f"   Object ID: [green]{sp_id}[/green]")
        
        return sp_id
        
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Failed to create service principal[/red]")
        console.print(f"Error: {e.stderr}")
        
        if "already exists" in e.stderr:
            console.print("The application may already be registered. Check existing service principals.")
        
        return None


def generate_admin_consent_url(config):
    """Generate the admin consent URL."""
    admin_consent_url = (
        f"https://login.microsoftonline.com/{config['CUSTOMER_TENANT_ID']}/adminconsent?"
        f"client_id={config['PROVIDER_CLIENT_ID']}"
        f"&redirect_uri={config['PROVIDER_REDIRECT_URI']}"
    )
    return admin_consent_url


def request_admin_consent(config):
    """Guide user through admin consent process."""
    print_section("Admin Consent Required")
    
    admin_consent_url = generate_admin_consent_url(config)
    
    console.print("[yellow]⚠️  Admin consent is required to grant permissions[/yellow]\n")
    console.print("The consent URL has been generated:")
    console.print(f"[blue]{admin_consent_url}[/blue]\n")
    
    # Ask if user wants to open browser
    if Confirm.ask("Open consent URL in browser now?", default=True):
        console.print("Opening browser...")
        webbrowser.open(admin_consent_url)
        console.print("\n[yellow]Instructions:[/yellow]")
        console.print("1. Login with Global Administrator account")
        console.print("2. Review the requested permissions")
        console.print("3. Click 'Accept' to grant consent")
        console.print("4. After completing consent, return here\n")
        
        input("Press Enter after completing admin consent...")
        console.print("✅ Admin consent process completed")
    else:
        console.print("\n[yellow]Manual consent required:[/yellow]")
        console.print("1. Copy the URL above")
        console.print("2. Send to Global Administrator")
        console.print("3. Admin should login and grant consent")
        console.print("4. Return here after consent is granted\n")


def verify_permissions(sp_id):
    """Verify the service principal has required permissions."""
    print_section("Verifying Permissions")
    
    console.print("Checking granted permissions...")
    
    # Get OAuth2 permissions
    get_cmd = [
        'az', 'ad', 'sp', 'show',
        '--id', sp_id,
        '--query', 'oauth2PermissionGrants',
        '-o', 'json'
    ]
    
    try:
        result = subprocess.run(get_cmd, capture_output=True, text=True, check=True)
        permissions = json.loads(result.stdout)
        
        if permissions:
            console.print("✅ Permissions found:")
            for perm in permissions:
                console.print(f"   - Scope: {perm.get('scope', 'N/A')}")
        else:
            console.print("[yellow]⚠️  No permissions found yet[/yellow]")
            console.print("Admin consent may still be pending")
            
    except subprocess.CalledProcessError as e:
        console.print(f"[yellow]⚠️  Could not verify permissions: {e.stderr}[/yellow]")
    except json.JSONDecodeError:
        console.print("[yellow]⚠️  Could not parse permissions response[/yellow]")
        console.print("Admin consent may still be pending")
        # Print result for debugging
        console.print(f"Response: {result.stdout}")


def save_registration_info(config, sp_id):
    """Save registration information to file."""
    registration_file = 'registration_info.json'
    
    registration_data = {
        'customer_tenant_id': config['CUSTOMER_TENANT_ID'],
        'provider_client_id': config['PROVIDER_CLIENT_ID'],
        'service_principal_id': sp_id,
        'registered_at': subprocess.run(
            ['date', '-Iseconds'],
            capture_output=True,
            text=True
        ).stdout.strip()
    }
    
    with open(registration_file, 'w') as f:
        json.dump(registration_data, f, indent=2)
    
    console.print(f"\n💾 Registration info saved to: [cyan]{registration_file}[/cyan]")


def display_next_steps(config):
    """Display next steps for the customer."""
    print_section("Next Steps")
    
    console.print("[bold green]✅ Registration Complete![/bold green]\n")
    console.print("Next steps:")
    console.print("1. ✅ Service principal created in your tenant")
    console.print("2. ✅ Admin consent granted (or pending)")
    console.print("3. 📋 Assign users/groups to the application:")
    console.print(f"   [yellow]python assign_users.py --users user@domain.com[/yellow]")
    console.print("4. 🔍 Verify setup:")
    console.print(f"   [yellow]python verify_setup.py[/yellow]")
    console.print("\n[bold]The provider app is now available in your tenant![/bold]")


def main():
    """Main execution flow."""
    console.print(Panel.fit(
        "[bold green]Customer App Registration[/bold green]\n"
        "This script registers the provider's app in your tenant",
        border_style="green"
    ))
    
    # Load configuration
    config = load_configuration()
    
    # Check Azure CLI
    current_tenant = check_azure_cli()
    if not current_tenant:
        sys.exit(1)
    
    # Verify correct tenant
    if not verify_tenant(config, current_tenant):
        sys.exit(1)
    
    # Check for existing service principal
    sp_id = check_existing_service_principal(config['PROVIDER_CLIENT_ID'])
    
    # Create if doesn't exist
    if not sp_id:
        sp_id = create_service_principal(config['PROVIDER_CLIENT_ID'])
        if not sp_id:
            sys.exit(1)
    
    # Request admin consent
    request_admin_consent(config)
    
    # Verify permissions
    verify_permissions(sp_id)
    
    # Save registration info
    save_registration_info(config, sp_id)
    
    # Display next steps
    display_next_steps(config)


if __name__ == "__main__":
    main()
