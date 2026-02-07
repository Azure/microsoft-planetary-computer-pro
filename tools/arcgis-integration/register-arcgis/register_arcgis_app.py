#!/usr/bin/env python3

import argparse
import subprocess
import sys
import json
import os

def run_command(cmd, capture_output=False, shell=False):
    """Run a shell command and return output if requested."""
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=shell, check=True, text=True, stdout=subprocess.PIPE)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, shell=shell, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        sys.exit(1)

def load_and_replace_template(template_path, app_id, web_app_id=None):
    with open(template_path, 'r') as f:
        template = f.read()
    if web_app_id:
        template = template.replace('{{WEB_APP_ID}}', web_app_id)
    config_str = template.replace('{{APP_ID}}', app_id)
    config = json.loads(config_str)
    return config_str,config

def main():
    parser = argparse.ArgumentParser(
        description=(
            "This script creates two Azure AD app registrations for ArcGIS: one for the Web API and one for the Desktop Client.\n"
            "It uses the Azure CLI and REST API to:\n"
            "  1. Create the app registrations\n"
            "  2. Patch their configuration using provided JSON templates\n\n"
            "Arguments:\n"
            "  --web-app-template: Path to the web application template JSON file\n"
            "  --desktop-app-template: Path to the desktop application template JSON file\n"
            "  --cloud: 'public' (default) or 'usgov' to select the Azure cloud\n\n"
            "Prerequisites:\n"
            "  - You must be logged into the Azure CLI (run 'az login').\n"
            "  - If running outside the Azure Cloud Shell and using US Gov, set your cloud with:\n"
            "      az cloud set --name AzureUSGovernment\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--web-app-template', required=True, help='Path to the web application template JSON file')
    parser.add_argument('--desktop-app-template', required=True, help='Path to the desktop application template JSON file')
    parser.add_argument('--cloud', choices=['public', 'usgov'], default='public', help="Azure cloud: 'public' (default) or 'usgov'")
    args = parser.parse_args()

    # Set graph_uri_base based on cloud
    graph_uri_base = "graph.microsoft.com" if args.cloud == "public" else "graph.microsoft.us"

    # 1. Create ArcGIS Web App registration
    print("Creating ArcGIS Web App registration...")
    run_command(["az", "ad", "app", "create", "--display-name", "ArcGISPro-GeoCatalog-WebAPI"])
    web_app_id = run_command(
        ["az", "ad", "app", "list", "--display-name", "ArcGISPro-GeoCatalog-WebAPI", "--query", "[0].appId", "-o", "tsv"],
        capture_output=True
    )
    print(f"  Web App appId: {web_app_id}")

    # 2. Patch Web App registration
    web_app_config_str,web_app_config = load_and_replace_template(args.web_app_template, web_app_id)
    print("Patching Web App registration...")

    # We need to patch the app registration progressively
    # Using the web_app_config, we will iteratively patch the app registration with the following properties:

    # 1. identifierUris
    if "identifierUris" in web_app_config:
        patch_body = json.dumps({"identifierUris": web_app_config["identifierUris"]})
        run_command([
            "az", "rest",
            "--method", "PATCH",
            "--uri", f"https://{graph_uri_base}/v1.0/applications(appId='{web_app_id}')",
            "--headers", "Content-type=application/json",
            "--body", patch_body
        ])

    # 2. publicClient.redirectUris
    if "publicClient" in web_app_config and "redirectUris" in web_app_config["publicClient"]:
        patch_body = json.dumps({"publicClient": {"redirectUris": web_app_config["publicClient"]["redirectUris"]}})
        run_command([
            "az", "rest",
            "--method", "PATCH",
            "--uri", f"https://{graph_uri_base}/v1.0/applications(appId='{web_app_id}')",
            "--headers", "Content-type=application/json",
            "--body", patch_body
        ])

    # 3. requiredResourceAccess
    if "requiredResourceAccess" in web_app_config:
        patch_body = json.dumps({"requiredResourceAccess": web_app_config["requiredResourceAccess"]})
        run_command([
            "az", "rest",
            "--method", "PATCH",
            "--uri", f"https://{graph_uri_base}/v1.0/applications(appId='{web_app_id}')",
            "--headers", "Content-type=application/json",
            "--body", patch_body
        ])

    # 4. api.requestedAccessTokenVersion (must be set before signInAudience for AzureADandPersonalMicrosoftAccount)
    if "api" in web_app_config and web_app_config["api"].get("requestedAccessTokenVersion") is not None:
        patch_body = json.dumps({"api": {"requestedAccessTokenVersion": web_app_config["api"]["requestedAccessTokenVersion"]}})
        run_command([
            "az", "rest",
            "--method", "PATCH",
            "--uri", f"https://{graph_uri_base}/v1.0/applications(appId='{web_app_id}')",
            "--headers", "Content-type=application/json",
            "--body", patch_body
        ])

    # 5. signInAudience
    if "signInAudience" in web_app_config:
        patch_body = json.dumps({"signInAudience": web_app_config["signInAudience"]})
        run_command([
            "az", "rest",
            "--method", "PATCH",
            "--uri", f"https://{graph_uri_base}/v1.0/applications(appId='{web_app_id}')",
            "--headers", "Content-type=application/json",
            "--body", patch_body
        ])

    # 6. web.redirectUris
    if "web" in web_app_config and "redirectUris" in web_app_config["web"]:
        patch_body = json.dumps({"web": {"redirectUris": web_app_config["web"]["redirectUris"]}})
        run_command([
            "az", "rest",
            "--method", "PATCH",
            "--uri", f"https://{graph_uri_base}/v1.0/applications(appId='{web_app_id}')",
            "--headers", "Content-type=application/json",
            "--body", patch_body
        ])

    # 7. web.redirectUriSettings
    if "web" in web_app_config and "redirectUriSettings" in web_app_config["web"]:
        patch_body = json.dumps({"web": {"redirectUriSettings": web_app_config["web"]["redirectUriSettings"]}})
        run_command([
            "az", "rest",
            "--method", "PATCH",
            "--uri", f"https://{graph_uri_base}/v1.0/applications(appId='{web_app_id}')",
            "--headers", "Content-type=application/json",
            "--body", patch_body
        ])

    # 8. web.implicitGrantSettings
    if "web" in web_app_config and "implicitGrantSettings" in web_app_config["web"]:
        patch_body = json.dumps({"web": {"implicitGrantSettings": web_app_config["web"]["implicitGrantSettings"]}})
        run_command([
            "az", "rest",
            "--method", "PATCH",
            "--uri", f"https://{graph_uri_base}/v1.0/applications(appId='{web_app_id}')",
            "--headers", "Content-type=application/json",
            "--body", patch_body
        ])

    # 9. api.oauth2PermissionScopes
    if "api" in web_app_config and "oauth2PermissionScopes" in web_app_config["api"]:
        patch_body = json.dumps({"api": {"oauth2PermissionScopes": web_app_config["api"]["oauth2PermissionScopes"]}})
        run_command([
            "az", "rest",
            "--method", "PATCH",
            "--uri", f"https://{graph_uri_base}/v1.0/applications(appId='{web_app_id}')",
            "--headers", "Content-type=application/json",
            "--body", patch_body
        ])

    # 10. api.preAuthorizedApplications
    if "api" in web_app_config and "preAuthorizedApplications" in web_app_config["api"]:
        patch_body = json.dumps({"api": {"preAuthorizedApplications": web_app_config["api"]["preAuthorizedApplications"]}})
        run_command([
            "az", "rest",
            "--method", "PATCH",
            "--uri", f"https://{graph_uri_base}/v1.0/applications(appId='{web_app_id}')",
            "--headers", "Content-type=application/json",
            "--body", patch_body
        ])

    

    # 3. Create ArcGIS Desktop App registration
    print("Creating ArcGIS Desktop App registration...")
    run_command(["az", "ad", "app", "create", "--display-name", "ArcGISPro-GeoCatalog-DesktopClient"])
    desktop_app_id = run_command(
        ["az", "ad", "app", "list", "--display-name", "ArcGISPro-GeoCatalog-DesktopClient", "--query", "[0].appId", "-o", "tsv"],
        capture_output=True
    )
    print(f"  Desktop App appId: {desktop_app_id}")

    # 4. Patch Desktop App registration
    desktop_app_config_str,desktop_app_config = load_and_replace_template(args.desktop_app_template, desktop_app_id, web_app_id)

    print("Patching Desktop App registration...")
    # We need to patch the app registration progressively
    # Using the desktop_app_config, we will iteratively patch the app registration with the following properties:
    # 1. PublicClient.redirectUris
    if "publicClient" in desktop_app_config and "redirectUris" in desktop_app_config["publicClient"]:
        patch_body = json.dumps({"publicClient": {"redirectUris": desktop_app_config["publicClient"]["redirectUris"]}})
        run_command([
            "az", "rest",
            "--method", "PATCH",
            "--uri", f"https://{graph_uri_base}/v1.0/applications(appId='{desktop_app_id}')",
            "--headers", "Content-type=application/json",
            "--body", patch_body
        ])

    # 2. requiredResourceAccess
    if "requiredResourceAccess" in desktop_app_config:
        patch_body = json.dumps({"requiredResourceAccess": desktop_app_config["requiredResourceAccess"]})
        run_command([
            "az", "rest",
            "--method", "PATCH",
            "--uri", f"https://{graph_uri_base}/v1.0/applications(appId='{desktop_app_id}')",
            "--headers", "Content-type=application/json",
            "--body", patch_body
        ])

    # 3. signInAudience
    if "signInAudience" in desktop_app_config:
        patch_body = json.dumps({"signInAudience": desktop_app_config["signInAudience"]})
        run_command([
            "az", "rest",
            "--method", "PATCH",
            "--uri", f"https://{graph_uri_base}/v1.0/applications(appId='{desktop_app_id}')",
            "--headers", "Content-type=application/json",
            "--body", patch_body
        ])

    # 4. web.redirectUris
    if "web" in desktop_app_config and "redirectUris" in desktop_app_config["web"]:
        patch_body = json.dumps({"web": {"redirectUris": desktop_app_config["web"]["redirectUris"]}})
        run_command([
            "az", "rest",
            "--method", "PATCH",
            "--uri", f"https://{graph_uri_base}/v1.0/applications(appId='{desktop_app_id}')",
            "--headers", "Content-type=application/json",
            "--body", patch_body
        ])

    # 5. web.redirectUriSettings
    if "web" in desktop_app_config and "redirectUriSettings" in desktop_app_config["web"]:
        patch_body = json.dumps({"web": {"redirectUriSettings": desktop_app_config["web"]["redirectUriSettings"]}})
        run_command([
            "az", "rest",
            "--method", "PATCH",
            "--uri", f"https://{graph_uri_base}/v1.0/applications(appId='{desktop_app_id}')",
            "--headers", "Content-type=application/json",
            "--body", patch_body
        ])
    # 6. web.implicitGrantSettings
    if "web" in desktop_app_config and "implicitGrantSettings" in desktop_app_config["web"]:
        patch_body = json.dumps({"web": {"implicitGrantSettings": desktop_app_config["web"]["implicitGrantSettings"]}})
        run_command([
            "az", "rest",
            "--method", "PATCH",
            "--uri", f"https://{graph_uri_base}/v1.0/applications(appId='{desktop_app_id}')",
            "--headers", "Content-type=application/json",
            "--body", patch_body
        ])

    # Now grant admin consent for the Web App
    # print("Granting admin consent for the Web App...")
    # run_command([
    #     "az", "rest",
    #     "--method", "POST",
    #     "--uri", f"https://{graph_uri_base}/v1.0/oauth2PermissionGrants",
    #     "--headers", "Content-type=application/json",
    #     "--body", json.dumps(
    #         {
    #             "clientId": desktop_app_id,
    #             "consentType": "AllPrincipals",
    #             "resourceId": "943603e4-e787-4fe9-93d1-e30f749aae39",
    #             "scope": "DelegatedPermissionGrant.ReadWrite.All"
    #         }
    #     )
    # ])

    print("App registrations and configuration complete.")

    # Tell the user to take note of the desktop-app-id (aka the Client ID); this will be used to setup the Authentication with ArcGIS Pro.
    print(f"\nPlease take note of the Desktop App Client ID: {desktop_app_id}")
    print("You can now use this Client ID to configure ArcGIS Pro for authentication with Azure AD.")
    print("Before using the Web App, you may need grant admin consent for the permissions it requires. This can be done in the Azure portal. See register-arcgis/README.md for more details.")

if __name__ == "__main__":
    main()