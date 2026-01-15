#!/usr/bin/env python3
"""
Provider App Registration Setup

This script creates and configures a multi-tenant Azure App Registration
that can be shared with customers as an enterprise application.

Prerequisites:
- Azure CLI installed and authenticated
- Application Administrator or Global Administrator role
- .env file configured with subscription details

Usage:
    python setup_provider_app.py
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

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
        'AZURE_TENANT_ID': os.getenv('AZURE_TENANT_ID'),
        'PROVIDER_APP_NAME': os.getenv('PROVIDER_APP_NAME', 'planetary-computer-provider'),
        'PROVIDER_APP_REDIRECT_URI': os.getenv('PROVIDER_APP_REDIRECT_URI', 'https://localhost:8080/callback')
    }
    
    if not config['AZURE_TENANT_ID']:
        console.print("[red]❌ Missing required environment variables![/red]")
        console.print("Please configure .env file with:")
        console.print("  - AZURE_TENANT_ID")
        sys.exit(1)
    
    console.print("✅ Configuration loaded successfully")
    console.print(f"   App Name: [green]{config['PROVIDER_APP_NAME']}[/green]")
    console.print(f"   Tenant ID: [green]{config['AZURE_TENANT_ID'][:8]}...[/green]")
    
    return config


def check_azure_cli():
    """Verify Azure CLI is installed and authenticated."""
    print_section("Checking Azure CLI")
    
    try:
        result = subprocess.run(['az', '--version'], 
                              capture_output=True, text=True, check=True)
        console.print("✅ Azure CLI is installed")
        
        # Check if logged in
        result = subprocess.run(['az', 'account', 'show'], 
                              capture_output=True, text=True, check=True)
        account_info = json.loads(result.stdout)
        console.print(f"✅ Logged in as: [green]{account_info.get('user', {}).get('name')}[/green]")
        return True
        
    except subprocess.CalledProcessError:
        console.print("[red]❌ Azure CLI not found or not logged in[/red]")
        console.print("Please run: [yellow]az login[/yellow]")
        return False
    except FileNotFoundError:
        console.print("[red]❌ Azure CLI not installed[/red]")
        console.print("Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli")
        return False


def create_app_registration(config):
    """Create a multi-tenant app registration."""
    print_section("Creating App Registration")
    
    app_name = config['PROVIDER_APP_NAME']
    redirect_uri = config['PROVIDER_APP_REDIRECT_URI']
    
    console.print(f"Creating app: [cyan]{app_name}[/cyan]")
    
    # Check if app already exists
    check_cmd = [
        'az', 'ad', 'app', 'list',
        '--display-name', app_name,
        '--query', '[0].appId',
        '-o', 'tsv'
    ]
    
    result = subprocess.run(check_cmd, capture_output=True, text=True)
    existing_app_id = result.stdout.strip()
    
    if existing_app_id:
        console.print(f"⚠️  App already exists with ID: [yellow]{existing_app_id}[/yellow]")
        console.print("Do you want to use the existing app? (y/n): ", end="")
        choice = input().lower()
        if choice == 'y':
            return existing_app_id
        else:
            console.print("Please choose a different app name in .env")
            sys.exit(1)
    
    # Create new app registration
    create_cmd = [
        'az', 'ad', 'app', 'create',
        '--display-name', app_name,
        '--sign-in-audience', 'AzureADMultipleOrgs',  # Multi-tenant
        '--web-redirect-uris', redirect_uri,
        '--enable-id-token-issuance', 'true',
        '--enable-access-token-issuance', 'true'
    ]
    
    try:
        result = subprocess.run(create_cmd, capture_output=True, text=True, check=True)
        app_info = json.loads(result.stdout)
        app_id = app_info['appId']
        
        console.print(f"✅ App registration created!")
        console.print(f"   Application ID: [green]{app_id}[/green]")
        
        return app_id
        
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Failed to create app registration[/red]")
        console.print(f"Error: {e.stderr}")
        sys.exit(1)


def create_service_principal(app_id):
    """Create a service principal for the app."""
    print_section("Creating Service Principal")
    
    console.print(f"Creating service principal for app: [cyan]{app_id}[/cyan]")
    
    create_cmd = [
        'az', 'ad', 'sp', 'create',
        '--id', app_id
    ]
    
    try:
        result = subprocess.run(create_cmd, capture_output=True, text=True, check=True)
        sp_info = json.loads(result.stdout)
        sp_id = sp_info['id']
        
        console.print(f"✅ Service principal created!")
        console.print(f"   Object ID: [green]{sp_id}[/green]")
        
        return sp_id
        
    except subprocess.CalledProcessError as e:
        if "already exists" in e.stderr:
            console.print("⚠️  Service principal already exists")
            # Get existing SP ID
            get_cmd = ['az', 'ad', 'sp', 'list', '--filter', f"appId eq '{app_id}'", '--query', '[0].id', '-o', 'tsv']
            result = subprocess.run(get_cmd, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        else:
            console.print(f"[red]❌ Failed to create service principal[/red]")
            console.print(f"Error: {e.stderr}")
            sys.exit(1)


def create_client_secret(app_id):
    """Create a client secret for the app."""
    print_section("Creating Client Secret")
    
    console.print("Creating client secret (valid for 1 year)...")
    
    create_cmd = [
        'az', 'ad', 'app', 'credential', 'reset',
        '--id', app_id,
        '--append',
        '--years', '1'
    ]
    
    try:
        result = subprocess.run(create_cmd, capture_output=True, text=True, check=True)
        cred_info = json.loads(result.stdout)
        client_secret = cred_info['password']
        
        console.print("✅ Client secret created!")
        console.print(f"   [yellow]⚠️  Save this secret - it won't be shown again![/yellow]")
        console.print(f"   Secret: [red]{client_secret}[/red]")
        
        return client_secret
        
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Failed to create client secret[/red]")
        console.print(f"Error: {e.stderr}")
        sys.exit(1)


def configure_api_permissions(app_id):
    """Configure API permissions for the app."""
    print_section("Configuring API Permissions")
    
    console.print("Adding Microsoft Graph User.Read permission...")
    
    # Microsoft Graph API ID
    graph_api_id = "00000003-0000-0000-c000-000000000000"
    # User.Read scope ID
    user_read_id = "e1fe6dd8-ba31-4d61-89e7-88639da4683d"
    
    add_cmd = [
        'az', 'ad', 'app', 'permission', 'add',
        '--id', app_id,
        '--api', graph_api_id,
        '--api-permissions', f"{user_read_id}=Scope"
    ]
    
    try:
        subprocess.run(add_cmd, capture_output=True, text=True, check=True)
        console.print("✅ Microsoft Graph User.Read permission added")
        
    except subprocess.CalledProcessError as e:
        console.print(f"[yellow]⚠️  Permission may already exist: {e.stderr}[/yellow]")


def generate_customer_onboarding_info(config, app_id, client_secret):
    """Generate onboarding information for customers."""
    print_section("Customer Onboarding Information")
    
    tenant_id = config['AZURE_TENANT_ID']
    redirect_uri = config['PROVIDER_APP_REDIRECT_URI']
    admin_consent_url = (
        f"https://login.microsoftonline.com/{{customer-tenant-id}}/adminconsent?"
        f"client_id={app_id}&redirect_uri={redirect_uri}"
    )
    
    # Create a nice table
    table = Table(title="Provider Application Details", show_header=True, header_style="bold magenta")
    table.add_column("Property", style="cyan", width=30)
    table.add_column("Value", style="green")
    
    table.add_row("Application Name", config['PROVIDER_APP_NAME'])
    table.add_row("Application (Client) ID", app_id)
    table.add_row("Tenant ID (Provider)", tenant_id)
    table.add_row("Client Secret", client_secret)
    table.add_row("Multi-Tenant", "Yes (AzureADMultipleOrgs)")
    
    console.print(table)
    
    console.print("\n[bold yellow]📋 Share with Customers:[/bold yellow]")
    console.print(f"   Application ID: [green]{app_id}[/green]")
    console.print(f"   Provider Tenant ID: [green]{tenant_id}[/green]")
    
    console.print("\n[bold yellow]🔗 Admin Consent URL Template:[/bold yellow]")
    console.print(f"   [blue]{admin_consent_url}[/blue]")
    console.print("   (Replace {{customer-tenant-id}} with actual customer tenant ID)")
    
    # Save to file
    onboarding_file = 'customer_onboarding.json'
    onboarding_data = {
        'provider_app_name': config['PROVIDER_APP_NAME'],
        'application_id': app_id,
        'provider_tenant_id': tenant_id,
        'admin_consent_url_template': admin_consent_url,
        'created_at': datetime.now().isoformat(),
        'client_secret': client_secret,
        'instructions': {
            'step_1': 'Customer admin navigates to admin consent URL',
            'step_2': 'Admin grants consent for requested permissions',
            'step_3': 'Customer runs customer-app registration script',
            'step_4': 'Customer assigns users/groups to the application'
        }
    }
    
    with open(onboarding_file, 'w') as f:
        json.dump(onboarding_data, f, indent=2)
    
    console.print(f"\n💾 Onboarding information saved to: [cyan]{onboarding_file}[/cyan]")


def main():
    """Main execution flow."""
    console.print(Panel.fit(
        "[bold green]Provider App Registration Setup[/bold green]\n"
        "This script will create a multi-tenant Azure App Registration",
        border_style="green"
    ))
    
    # Load configuration
    config = load_configuration()
    
    # Check Azure CLI
    if not check_azure_cli():
        sys.exit(1)
    
    # Create app registration
    app_id = create_app_registration(config)
    
    # Create service principal
    sp_id = create_service_principal(app_id)
    
    # Create client secret
    client_secret = create_client_secret(app_id)
    
    # Configure permissions
    configure_api_permissions(app_id)
    
    # Generate onboarding info
    generate_customer_onboarding_info(config, app_id, client_secret)
    
    console.print(Panel.fit(
        "[bold green]✅ Provider App Setup Complete![/bold green]\n\n"
        "Next steps:\n"
        "1. Review the customer_onboarding.json file\n"
        "2. Share Application ID and Tenant ID with customers\n"
        "3. Provide customers with admin consent URL\n"
        "4. Guide customers through registration process",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
