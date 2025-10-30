
#!/usr/bin/env python3
"""
Interactive script to update Azure credentials
"""

import json
import os

def update_azure_credentials():
    """Update Azure credentials interactively"""
    
    secrets_path = '/home/ubuntu/.config/abacusai_auth_secrets.json'
    
    print("=" * 60)
    print("Azure Cognitive Services - Credentials Update")
    print("=" * 60)
    print()
    print("Get your credentials from: https://portal.azure.com")
    print("Navigate to: Cognitive Services → Speech Services → Keys and Endpoint")
    print()
    
    # Get user input
    speech_key = input("Enter your Azure Speech Key: ").strip()
    speech_region = input("Enter your Azure Region (e.g., eastus): ").strip()
    
    if not speech_key or not speech_region:
        print("\n❌ Error: Both key and region are required!")
        return False
    
    # Load existing secrets
    try:
        if os.path.exists(secrets_path):
            with open(secrets_path, 'r') as f:
                secrets = json.load(f)
        else:
            secrets = {}
    except Exception as e:
        print(f"\n❌ Error reading secrets file: {e}")
        return False
    
    # Update Azure credentials
    if 'azure cognitive services' not in secrets:
        secrets['azure cognitive services'] = {'secrets': {}}
    
    secrets['azure cognitive services']['secrets']['speech_key'] = {
        'value': speech_key
    }
    secrets['azure cognitive services']['secrets']['speech_region'] = {
        'value': speech_region
    }
    
    # Save updated secrets
    try:
        # Create backup
        if os.path.exists(secrets_path):
            backup_path = secrets_path + '.backup'
            with open(secrets_path, 'r') as f:
                backup_content = f.read()
            with open(backup_path, 'w') as f:
                f.write(backup_content)
            print(f"\n✅ Backup created: {backup_path}")
        
        # Write new secrets
        os.makedirs(os.path.dirname(secrets_path), exist_ok=True)
        with open(secrets_path, 'w') as f:
            json.dump(secrets, f, indent=2)
        
        print(f"\n✅ Credentials updated successfully!")
        print(f"✅ File: {secrets_path}")
        print()
        print("=" * 60)
        print("Next Steps:")
        print("=" * 60)
        print("1. Test the service:")
        print("   curl https://phone-system-backend.onrender.com/test/azure-tts")
        print()
        print("2. If running locally, restart your Flask app:")
        print("   python app.py")
        print()
        print("3. If deployed on Render, the app will reload automatically")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error saving credentials: {e}")
        return False


if __name__ == '__main__':
    try:
        success = update_azure_credentials()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        exit(1)
