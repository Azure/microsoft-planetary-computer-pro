#!/usr/bin/env python3
"""
Assign Users/Groups to Provider Application

This script assigns users or groups to the registered provider application
in the customer tenant.

Usage:
    python assign_users.py --users user1@domain.com,user2@domain.com
    python assign_users.py --groups "Group Name 1","Group Name 2"
    python assign_users.py --remove --users user@domain.com
"""

import os
import sys
import json
import subprocess
import argparse
from dotenv import load_dotenv
from rich.console import Console

console = Console()


def load_registration_info():
    """Load registration info from file."""
    if not os.path.exists('registration_info.json'):
        console.print("[red]❌ Registration info not found![/red]")
        console.print("Please run register_provider_app.py first")
        sys.exit(1)
    
    with open('registration_info.json', 'r') as f:
        return json.load(f)


def assign_user(sp_id, user_email):
    """Assign a user to the application."""
    console.print(f"Assigning user: [cyan]{user_email}[/cyan]")
    
    # Get user object ID
    get_user_cmd = [
        'az', 'ad', 'user', 'show',
        '--id', user_email,
        '--query', 'id',
        '-o', 'tsv'
    ]
    
    try:
        result = subprocess.run(get_user_cmd, capture_output=True, text=True, check=True)
        user_id = result.stdout.strip()
        
        # Assign user to app
        assign_cmd = [
            'az', 'rest',
            '--method', 'POST',
            '--uri', f'https://graph.microsoft.com/v1.0/servicePrincipals/{sp_id}/appRoleAssignedTo',
            '--body', json.dumps({
                'principalId': user_id,
                'resourceId': sp_id,
                'appRoleId': '00000000-0000-0000-0000-000000000000'  # Default access
            }),
            '--headers', 'Content-Type=application/json'
        ]
        
        subprocess.run(assign_cmd, capture_output=True, text=True, check=True)
        console.print(f"✅ User assigned: {user_email}")
        
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Failed to assign user: {user_email}[/red]")
        console.print(f"Error: {e.stderr}")


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(description='Assign users/groups to provider app')
    parser.add_argument('--users', help='Comma-separated list of user emails')
    parser.add_argument('--groups', help='Comma-separated list of group names')
    parser.add_argument('--remove', action='store_true', help='Remove assignments instead of adding')
    
    args = parser.parse_args()
    
    if not args.users and not args.groups:
        parser.print_help()
        sys.exit(1)
    
    # Load registration info
    reg_info = load_registration_info()
    sp_id = reg_info['service_principal_id']
    
    console.print(f"Service Principal ID: [green]{sp_id}[/green]\n")
    
    # Process users
    if args.users:
        users = [u.strip() for u in args.users.split(',')]
        for user in users:
            assign_user(sp_id, user)
    
    console.print("\n✅ Assignment complete!")


if __name__ == "__main__":
    main()
