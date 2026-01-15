#!/usr/bin/env python3
"""
Verify Customer Setup

This script verifies that the provider app is correctly registered
and configured in the customer tenant.

Usage:
    python verify_setup.py
"""

import os
import sys
import json
import subprocess
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

console = Console()


def load_registration_info():
    """Load registration info from file."""
    if not os.path.exists('registration_info.json'):
        console.print("[red]❌ Registration info not found![/red]")
        console.print("Please run register_provider_app.py first")
        sys.exit(1)
    
    with open('registration_info.json', 'r') as f:
        return json.load(f)


def verify_service_principal(sp_id, app_id):
    """Verify service principal exists and is active."""
    console.print("\n[bold]Checking Service Principal...[/bold]")
    
    get_cmd = [
        'az', 'ad', 'sp', 'show',
        '--id', sp_id,
        '-o', 'json'
    ]
    
    try:
        result = subprocess.run(get_cmd, capture_output=True, text=True, check=True)
        sp_info = json.loads(result.stdout)
        
        console.print(f"✅ Service principal exists")
        console.print(f"   Display Name: {sp_info.get('displayName')}")
        console.print(f"   App ID: {sp_info.get('appId')}")
        console.print(f"   Object ID: {sp_info.get('id')}")
        
        return True
        
    except subprocess.CalledProcessError:
        console.print("[red]❌ Service principal not found[/red]")
        return False


def check_permissions(sp_id):
    """Check OAuth2 permissions."""
    console.print("\n[bold]Checking Permissions...[/bold]")
    
    get_cmd = [
        'az', 'rest',
        '--method', 'GET',
        '--uri', f'https://graph.microsoft.com/v1.0/servicePrincipals/{sp_id}/oauth2PermissionGrants',
        '-o', 'json'
    ]
    
    try:
        result = subprocess.run(get_cmd, capture_output=True, text=True, check=True)
        response = json.loads(result.stdout)
        grants = response.get('value', [])
        
        if grants:
            console.print(f"✅ Found {len(grants)} permission grant(s)")
            for grant in grants:
                console.print(f"   Scope: {grant.get('scope')}")
        else:
            console.print("[yellow]⚠️  No permission grants found[/yellow]")
            console.print("   Admin consent may be pending")
        
        return len(grants) > 0
        
    except subprocess.CalledProcessError as e:
        console.print(f"[yellow]⚠️  Could not check permissions: {e.stderr}[/yellow]")
        return False


def check_user_assignments(sp_id):
    """Check user/group assignments."""
    console.print("\n[bold]Checking User Assignments...[/bold]")
    
    get_cmd = [
        'az', 'rest',
        '--method', 'GET',
        '--uri', f'https://graph.microsoft.com/v1.0/servicePrincipals/{sp_id}/appRoleAssignedTo',
        '-o', 'json'
    ]
    
    try:
        result = subprocess.run(get_cmd, capture_output=True, text=True, check=True)
        response = json.loads(result.stdout)
        assignments = response.get('value', [])
        
        if assignments:
            console.print(f"✅ Found {len(assignments)} assignment(s)")
            
            table = Table(title="Assigned Users/Groups")
            table.add_column("Principal Type", style="cyan")
            table.add_column("Principal ID", style="green")
            
            for assignment in assignments[:10]:  # Show first 10
                table.add_row(
                    assignment.get('principalType', 'Unknown'),
                    assignment.get('principalId', 'N/A')[:36]
                )
            
            console.print(table)
            
            if len(assignments) > 10:
                console.print(f"   ... and {len(assignments) - 10} more")
        else:
            console.print("[yellow]⚠️  No user assignments found[/yellow]")
            console.print("   Use assign_users.py to assign users")
        
        return len(assignments) > 0
        
    except subprocess.CalledProcessError as e:
        console.print(f"[yellow]⚠️  Could not check assignments: {e.stderr}[/yellow]")
        return False


def display_summary(results):
    """Display verification summary."""
    console.print("\n" + "=" * 80)
    console.print("[bold]Verification Summary[/bold]")
    console.print("=" * 80)
    
    all_passed = all(results.values())
    
    status_icon = "✅" if all_passed else "⚠️"
    status_text = "PASSED" if all_passed else "NEEDS ATTENTION"
    status_color = "green" if all_passed else "yellow"
    
    console.print(f"\n[{status_color}]{status_icon} Overall Status: {status_text}[/{status_color}]\n")
    
    for check, passed in results.items():
        icon = "✅" if passed else "❌"
        console.print(f"{icon} {check}")
    
    if not all_passed:
        console.print("\n[yellow]Some checks failed. Review the output above for details.[/yellow]")


def main():
    """Main execution."""
    console.print("[bold cyan]Verifying Customer Setup[/bold cyan]\n")
    
    # Load registration info
    reg_info = load_registration_info()
    
    console.print(f"Customer Tenant: {reg_info['customer_tenant_id']}")
    console.print(f"Provider App ID: {reg_info['provider_client_id']}")
    console.print(f"Service Principal: {reg_info['service_principal_id']}")
    
    # Run verification checks
    results = {
        'Service Principal Exists': verify_service_principal(
            reg_info['service_principal_id'],
            reg_info['provider_client_id']
        ),
        'Permissions Granted': check_permissions(reg_info['service_principal_id']),
        'Users Assigned': check_user_assignments(reg_info['service_principal_id'])
    }
    
    # Display summary
    display_summary(results)


if __name__ == "__main__":
    main()
