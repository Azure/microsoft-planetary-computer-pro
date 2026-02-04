#!/usr/bin/env python3
"""
Assign GeoCatalog Administrator Role

This script assigns the "GeoCatalog Administrator" role to the registered
provider app's service principal for a specific GeoCatalog resource.

Prerequisites:
- Azure CLI installed and authenticated to customer tenant
- Owner or User Access Administrator role on the GeoCatalog resource
- Service principal already registered (run register_provider_app.py first)
- .env file configured with GeoCatalog details

Usage:
    python assign_geocatalog_role.py
"""

import os
import sys
import json
import subprocess
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
        'GEOCATALOG_NAME': os.getenv('GEOCATALOG_NAME'),
        'GEOCATALOG_RESOURCE_GROUP': os.getenv('GEOCATALOG_RESOURCE_GROUP'),
        'AZURE_SUBSCRIPTION_ID': os.getenv('AZURE_SUBSCRIPTION_ID')
    }
    
    # Check all required components are provided
    if not all([config['GEOCATALOG_NAME'], config['GEOCATALOG_RESOURCE_GROUP'], config['AZURE_SUBSCRIPTION_ID']]):
        console.print("[red]❌ Missing required GeoCatalog configuration![/red]")
        console.print("\nPlease configure .env file with:")
        console.print("  - AZURE_SUBSCRIPTION_ID")
        console.print("  - GEOCATALOG_RESOURCE_GROUP")
        console.print("  - GEOCATALOG_NAME")
        sys.exit(1)
    
    # Build resource ID from components
    config['GEOCATALOG_RESOURCE_ID'] = (
        f"/subscriptions/{config['AZURE_SUBSCRIPTION_ID']}"
        f"/resourceGroups/{config['GEOCATALOG_RESOURCE_GROUP']}"
        f"/providers/Microsoft.Orbital/geoCatalogs/{config['GEOCATALOG_NAME']}"
    )
    
    console.print("✅ Configuration loaded successfully")
    console.print(f"   Subscription: [green]{config['AZURE_SUBSCRIPTION_ID'][:8]}...[/green]")
    console.print(f"   Resource Group: [green]{config['GEOCATALOG_RESOURCE_GROUP']}[/green]")
    console.print(f"   GeoCatalog Name: [green]{config['GEOCATALOG_NAME']}[/green]")
    console.print(f"   Resource ID: [green]{config['GEOCATALOG_RESOURCE_ID']}[/green]")
    
    return config


def load_registration_info():
    """Load service principal info from registration file."""
    print_section("Loading Registration Info")
    
    registration_file = 'registration_info.json'
    
    if not os.path.exists(registration_file):
        console.print(f"[red]❌ Registration file not found: {registration_file}[/red]")
        console.print("\nPlease run register_provider_app.py first to register the service principal.")
        sys.exit(1)
    
    with open(registration_file, 'r') as f:
        reg_info = json.load(f)
    
    console.print("✅ Registration info loaded")
    console.print(f"   Service Principal ID: [green]{reg_info['service_principal_id']}[/green]")
    console.print(f"   Provider Client ID: [green]{reg_info['provider_client_id']}[/green]")
    
    return reg_info


def check_azure_cli():
    """Verify Azure CLI is installed and authenticated."""
    print_section("Checking Azure CLI")
    
    try:
        result = subprocess.run(['az', '--version'], 
                              capture_output=True, text=True, check=True)
        console.print("✅ Azure CLI is installed")
        
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
        return False


def verify_geocatalog_exists(resource_id):
    """Verify the GeoCatalog resource exists and is accessible."""
    print_section("Verifying GeoCatalog Resource")
    
    console.print(f"Checking GeoCatalog resource: [cyan]{resource_id}[/cyan]")
    
    check_cmd = [
        'az', 'resource', 'show',
        '--ids', resource_id,
        '-o', 'json'
    ]
    
    try:
        result = subprocess.run(check_cmd, capture_output=True, text=True, check=True)
        resource_info = json.loads(result.stdout)
        
        console.print("✅ GeoCatalog resource found")
        console.print(f"   Name: [green]{resource_info.get('name')}[/green]")
        console.print(f"   Location: [green]{resource_info.get('location')}[/green]")
        console.print(f"   Type: [green]{resource_info.get('type')}[/green]")
        
        return True
        
    except subprocess.CalledProcessError as e:
        console.print("[red]❌ GeoCatalog resource not found or not accessible[/red]")
        console.print(f"Error: {e.stderr}")
        console.print("\nPossible issues:")
        console.print("  - Resource ID is incorrect")
        console.print("  - Resource doesn't exist")
        console.print("  - You don't have read permissions on the resource")
        return False


def get_geocatalog_admin_role_id():
    """Get the role definition ID for GeoCatalog Administrator."""
    print_section("Finding GeoCatalog Administrator Role")
    
    console.print("Searching for 'GeoCatalog Administrator' role definition...")
    
    # First, try to find the built-in role
    search_cmd = [
        'az', 'role', 'definition', 'list',
        '--name', 'GeoCatalog Administrator',
        '--query', '[0].id',
        '-o', 'tsv'
    ]
    
    result = subprocess.run(search_cmd, capture_output=True, text=True)
    role_id = result.stdout.strip()
    
    if role_id:
        console.print(f"✅ Found GeoCatalog Administrator role")
        console.print(f"   Role ID: [green]{role_id}[/green]")
        return role_id
    
    # If not found, search for similar roles
    console.print("[yellow]⚠️  'GeoCatalog Administrator' role not found[/yellow]")
    console.print("\nSearching for available GeoCatalog-related roles...")
    
    search_cmd = [
        'az', 'role', 'definition', 'list',
        '--query', "[?contains(roleName, 'GeoCatalog')].{Name:roleName, Id:id}",
        '-o', 'json'
    ]
    
    result = subprocess.run(search_cmd, capture_output=True, text=True)
    
    if result.returncode == 0 and result.stdout.strip():
        roles = json.loads(result.stdout)
        if roles:
            console.print(f"\nFound {len(roles)} GeoCatalog-related role(s):")
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Role Name", style="cyan")
            table.add_column("Role ID", style="green")
            
            for role in roles:
                table.add_row(role['Name'], role['Id'])
            
            console.print(table)
            
            # Ask user to select
            if len(roles) == 1:
                if Confirm.ask(f"\nUse '{roles[0]['Name']}' role?", default=True):
                    return roles[0]['Id']
            else:
                console.print("\n[yellow]Please update your script or select the correct role manually[/yellow]")
        else:
            console.print("[yellow]No GeoCatalog-related roles found[/yellow]")
    
    # Fallback: try common alternatives
    console.print("\nTrying alternative role names...")
    alternatives = [
        'GeoCatalog Data Owner',
        'GeoCatalog Contributor',
        'Contributor'
    ]
    
    for alt_role in alternatives:
        search_cmd = [
            'az', 'role', 'definition', 'list',
            '--name', alt_role,
            '--query', '[0].id',
            '-o', 'tsv'
        ]
        result = subprocess.run(search_cmd, capture_output=True, text=True)
        role_id = result.stdout.strip()
        
        if role_id:
            console.print(f"✅ Found alternative role: [cyan]{alt_role}[/cyan]")
            if Confirm.ask(f"Use '{alt_role}' role instead?", default=True):
                return role_id
    
    console.print("[red]❌ No suitable role found[/red]")
    console.print("\nYou can manually specify a role definition ID in the script")
    return None


def check_existing_role_assignment(sp_id, resource_id, role_id):
    """Check if the service principal already has the role assigned."""
    print_section("Checking Existing Role Assignment")
    
    console.print("Checking for existing role assignments...")
    
    check_cmd = [
        'az', 'role', 'assignment', 'list',
        '--assignee', sp_id,
        '--scope', resource_id,
        '--role', role_id,
        '-o', 'json'
    ]
    
    try:
        result = subprocess.run(check_cmd, capture_output=True, text=True, check=True)
        assignments = json.loads(result.stdout)
        
        if assignments:
            console.print("[yellow]⚠️  Role assignment already exists[/yellow]")
            console.print(f"   Assignment ID: [green]{assignments[0].get('id')}[/green]")
            console.print(f"   Created: [green]{assignments[0].get('createdOn')}[/green]")
            return True
        else:
            console.print("✅ No existing assignment found - ready to create")
            return False
            
    except subprocess.CalledProcessError as e:
        console.print(f"[yellow]⚠️  Could not check existing assignments: {e.stderr}[/yellow]")
        return False


def assign_role(sp_id, resource_id, role_id):
    """Assign the role to the service principal for the GeoCatalog resource."""
    print_section("Assigning Role")
    
    console.print(f"Assigning role to service principal...")
    console.print(f"   Service Principal: [cyan]{sp_id}[/cyan]")
    console.print(f"   Resource: [cyan]{resource_id}[/cyan]")
    console.print(f"   Role: [cyan]{role_id}[/cyan]\n")
    
    assign_cmd = [
        'az', 'role', 'assignment', 'create',
        '--assignee', sp_id,
        '--role', role_id,
        '--scope', resource_id,
        '-o', 'json'
    ]
    
    try:
        result = subprocess.run(assign_cmd, capture_output=True, text=True, check=True)
        assignment_info = json.loads(result.stdout)
        
        console.print("✅ Role assignment created successfully!")
        console.print(f"   Assignment ID: [green]{assignment_info.get('id')}[/green]")
        console.print(f"   Role Name: [green]{assignment_info.get('roleDefinitionName')}[/green]")
        console.print(f"   Scope: [green]{assignment_info.get('scope')}[/green]")
        
        return True
        
    except subprocess.CalledProcessError as e:
        console.print("[red]❌ Failed to assign role[/red]")
        console.print(f"Error: {e.stderr}")
        console.print("\nPossible issues:")
        console.print("  - You don't have permissions to assign roles (need Owner or User Access Administrator)")
        console.print("  - The service principal ID is incorrect")
        console.print("  - The role definition doesn't exist")
        console.print("  - There's a policy preventing role assignments")
        return False


def verify_assignment(sp_id, resource_id):
    """Verify the role assignment was successful."""
    print_section("Verifying Assignment")
    
    console.print("Checking all role assignments for the service principal on this resource...")
    
    check_cmd = [
        'az', 'role', 'assignment', 'list',
        '--assignee', sp_id,
        '--scope', resource_id,
        '-o', 'json'
    ]
    
    try:
        result = subprocess.run(check_cmd, capture_output=True, text=True, check=True)
        assignments = json.loads(result.stdout)
        
        if assignments:
            console.print(f"✅ Found {len(assignments)} role assignment(s):\n")
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Role Name", style="cyan")
            table.add_column("Scope Type", style="green")
            table.add_column("Created On", style="yellow")
            
            for assignment in assignments:
                scope = assignment.get('scope', '')
                scope_type = 'GeoCatalog' if 'geoCatalogs' in scope else 'Other'
                created = assignment.get('createdOn', 'N/A')[:10]  # Just date
                
                table.add_row(
                    assignment.get('roleDefinitionName', 'Unknown'),
                    scope_type,
                    created
                )
            
            console.print(table)
            return True
        else:
            console.print("[yellow]⚠️  No assignments found[/yellow]")
            return False
            
    except subprocess.CalledProcessError as e:
        console.print(f"[yellow]⚠️  Could not verify assignments: {e.stderr}[/yellow]")
        return False


def save_assignment_info(config, reg_info, role_id, assignment_created):
    """Save assignment information to file."""
    assignment_file = 'geocatalog_assignment.json'
    
    assignment_data = {
        'geocatalog_resource_id': config['GEOCATALOG_RESOURCE_ID'],
        'service_principal_id': reg_info['service_principal_id'],
        'provider_client_id': reg_info['provider_client_id'],
        'role_id': role_id,
        'assignment_created': assignment_created,
        'assigned_at': subprocess.run(
            ['date', '-Iseconds'],
            capture_output=True,
            text=True
        ).stdout.strip()
    }
    
    with open(assignment_file, 'w') as f:
        json.dump(assignment_data, f, indent=2)
    
    console.print(f"\n💾 Assignment info saved to: [cyan]{assignment_file}[/cyan]")


def main():
    """Main execution flow."""
    console.print(Panel.fit(
        "[bold green]Assign GeoCatalog Administrator Role[/bold green]\n"
        "This script assigns the GeoCatalog Administrator role to the provider app",
        border_style="green"
    ))
    
    # Check Azure CLI
    if not check_azure_cli():
        sys.exit(1)
    
    # Load configuration
    config = load_configuration()
    
    # Load registration info
    reg_info = load_registration_info()
    
    # Verify GeoCatalog exists
    if not verify_geocatalog_exists(config['GEOCATALOG_RESOURCE_ID']):
        sys.exit(1)
    
    # Get role definition ID
    role_id = get_geocatalog_admin_role_id()
    if not role_id:
        sys.exit(1)
    
    # Check for existing assignment
    already_assigned = check_existing_role_assignment(
        reg_info['service_principal_id'],
        config['GEOCATALOG_RESOURCE_ID'],
        role_id
    )
    
    assignment_created = False
    
    if not already_assigned:
        # Assign the role
        if assign_role(
            reg_info['service_principal_id'],
            config['GEOCATALOG_RESOURCE_ID'],
            role_id
        ):
            assignment_created = True
    
    # Verify assignment
    verify_assignment(
        reg_info['service_principal_id'],
        config['GEOCATALOG_RESOURCE_ID']
    )
    
    # Save assignment info
    save_assignment_info(config, reg_info, role_id, assignment_created)
    
    console.print(Panel.fit(
        "[bold green]✅ GeoCatalog Role Assignment Complete![/bold green]\n\n"
        "Next steps:\n"
        "1. Test GeoCatalog access with the provider app\n"
        "2. Verify the app can access GeoCatalog data\n"
        "3. Monitor access logs if needed",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
