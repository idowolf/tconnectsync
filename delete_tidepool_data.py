#!/usr/bin/env python3
"""
Delete all diabetes data from a Tidepool account.

WARNING: This is a DESTRUCTIVE operation that cannot be undone!
Use with caution and make sure you have backups if needed.

This script will:
1. Authenticate to Tidepool
2. Fetch all data for the user
3. Delete each data point
4. Provide progress updates

Usage:
    python delete_tidepool_data.py [--yes]
    
Options:
    --yes    Skip the confirmation prompt (USE WITH CAUTION!)
"""

import os
import sys
import requests
import argparse
from dotenv import load_dotenv

def get_tidepool_url(env):
    """Get Tidepool API URL based on environment."""
    urls = {
        'int': 'https://int-api.tidepool.org',
        'prd': 'https://api.tidepool.org',
        'dev': 'https://dev-api.tidepool.org'
    }
    return urls.get(env, urls['int'])

def get_external_url(env):
    """Get Tidepool external API URL for data source deletion."""
    urls = {
        'int': 'https://int-api.tidepool.org',
        'prd': 'https://external.tidepool.org',
        'dev': 'https://external.development.tidepool.org'
    }
    return urls.get(env, urls['int'])

def authenticate(base_url, username, password):
    """Authenticate to Tidepool and return session token and user ID."""
    print(f"Authenticating to {base_url}...")
    
    url = f"{base_url}/auth/login"
    response = requests.post(url, auth=(username, password))
    
    if response.status_code != 200:
        raise Exception(f"Authentication failed: {response.status_code} - {response.text}")
    
    session_token = response.headers.get('X-Tidepool-Session-Token')
    user_id = response.json().get('userid')
    
    if not session_token or not user_id:
        raise Exception("No session token or user ID received from authentication")
    
    print(f"✓ Authenticated as user: {user_id}")
    return session_token, user_id

def get_headers(session_token):
    """Get headers for API requests."""
    return {
        'X-Tidepool-Session-Token': session_token,
        'Content-Type': 'application/json'
    }

def fetch_all_data(base_url, session_token, user_id):
    """Fetch all diabetes data for the user."""
    print("\nFetching all data from Tidepool...")
    
    url = f"{base_url}/data/{user_id}"
    response = requests.get(url, headers=get_headers(session_token))
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch data: {response.status_code} - {response.text}")
    
    data = response.json()
    print(f"✓ Found {len(data)} data points")
    
    # Count by type
    type_counts = {}
    for item in data:
        data_type = item.get('type', 'unknown')
        type_counts[data_type] = type_counts.get(data_type, 0) + 1
    
    print("\nData breakdown by type:")
    for data_type, count in sorted(type_counts.items()):
        print(f"  - {data_type}: {count}")
    
    return data

def delete_all_data_sources(external_url, session_token, user_id):
    """Delete all data sources for the user (most efficient method)."""
    print(f"\nDeleting all data sources for user {user_id}...")
    print(f"Using external API: {external_url}")
    
    url = f"{external_url}/v1/users/{user_id}/data_sources"
    headers = get_headers(session_token)
    headers['Accept'] = 'application/json'
    
    print(f"DELETE {url}")
    response = requests.delete(url, headers=headers)
    
    if response.status_code in [200, 202, 204]:
        print(f"✓ Successfully deleted all data sources!")
        print(f"  Response: {response.status_code}")
        try:
            result = response.json()
            print(f"  Details: {result}")
        except:
            pass
        return True
    else:
        print(f"✗ Failed to delete data sources: {response.status_code}")
        print(f"  Response: {response.text[:200]}")
        return False

def delete_data_individually(base_url, session_token, user_id, data_points):
    """Delete data points individually (fallback method)."""
    print(f"\nAttempting individual deletion of {len(data_points)} data points...")
    print("Note: This may not be supported by Tidepool and could take a while...")
    
    deleted = 0
    failed = 0
    
    for i, item in enumerate(data_points):
        data_id = item.get('id')
        if not data_id:
            continue
        
        url = f"{base_url}/data/{data_id}"
        response = requests.delete(url, headers=get_headers(session_token))
        
        if response.status_code in [200, 202, 204]:
            deleted += 1
            if deleted % 50 == 0:
                print(f"  Deleted {deleted}/{len(data_points)}...")
        else:
            failed += 1
            if failed <= 10:
                print(f"  ✗ Failed to delete {data_id}: {response.status_code}")
    
    print(f"\n✓ Individual deletion complete!")
    print(f"  - Successfully deleted: {deleted}")
    if failed > 0:
        print(f"  - Failed to delete: {failed}")
    
    return deleted, failed

def main():
    parser = argparse.ArgumentParser(
        description='Delete all diabetes data from a Tidepool account',
        epilog='WARNING: This operation cannot be undone!'
    )
    parser.add_argument('--yes', action='store_true',
                       help='Skip confirmation prompt (USE WITH CAUTION!)')
    parser.add_argument('--env-file', default='.env',
                       help='Path to .env file (default: .env)')
    
    args = parser.parse_args()
    
    # Load environment variables
    env_file = args.env_file
    if not os.path.exists(env_file):
        print(f"Error: Environment file '{env_file}' not found!")
        print("Please create a .env file with your Tidepool credentials:")
        print("  TIDEPOOL_USERNAME=your-email@example.com")
        print("  TIDEPOOL_PASSWORD=your-password")
        print("  TIDEPOOL_ENV=int  # or 'prd' for production")
        sys.exit(1)
    
    load_dotenv(env_file)
    
    # Get credentials from environment
    username = os.getenv('TIDEPOOL_USERNAME')
    password = os.getenv('TIDEPOOL_PASSWORD')
    env = os.getenv('TIDEPOOL_ENV', 'int')
    
    if not username or not password:
        print("Error: TIDEPOOL_USERNAME and TIDEPOOL_PASSWORD must be set in .env file")
        sys.exit(1)
    
    base_url = get_tidepool_url(env)
    external_url = get_external_url(env)
    
    print("=" * 70)
    print("TIDEPOOL DATA DELETION TOOL")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Environment: {env}")
    print(f"  API URL: {base_url}")
    print(f"  External API URL: {external_url}")
    print(f"  Username: {username}")
    print(f"  Env file: {env_file}")
    
    try:
        # Authenticate
        session_token, user_id = authenticate(base_url, username, password)
        
        # Fetch all data
        data_points = fetch_all_data(base_url, session_token, user_id)
        
        if len(data_points) == 0:
            print("\n✓ No data to delete. Account is already empty.")
            return
        
        # Confirm deletion
        if not args.yes:
            print("\n" + "=" * 70)
            print("⚠️  WARNING: This will DELETE ALL DATA from your Tidepool account!")
            print("=" * 70)
            print(f"\nYou are about to delete {len(data_points)} data points.")
            print("This operation CANNOT be undone!")
            print("\nType 'DELETE ALL DATA' to confirm: ", end='')
            
            confirmation = input().strip()
            
            if confirmation != 'DELETE ALL DATA':
                print("\n✗ Deletion cancelled.")
                sys.exit(0)
        
        # Delete all data sources (most efficient method)
        success = delete_all_data_sources(external_url, session_token, user_id)
        
        if success:
            print("\n" + "=" * 70)
            print("✓ DATA DELETION COMPLETE")
            print("=" * 70)
            print(f"\nYour Tidepool account has been cleared.")
            print(f"You can now re-upload data with the fixed basal logic.")
            
            # Verify deletion
            print("\nVerifying deletion...")
            remaining_data = fetch_all_data(base_url, session_token, user_id)
            if len(remaining_data) == 0:
                print("✓ Verification successful - account is empty!")
            else:
                print(f"⚠ Warning: {len(remaining_data)} data points still remain")
        else:
            print("\n✗ Data deletion failed. See error messages above.")
        
    except KeyboardInterrupt:
        print("\n\n✗ Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

