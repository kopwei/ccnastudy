import getpass
import time
from netmiko import ConnectHandler
try:
    from inventory import DEVICES
except ImportError:
    # Handle running from root directory vs scripts directory
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from inventory import DEVICES

def load_config_file(filename):
    # Try looking in the scripts directory if running from root
    paths = [
        f"scripts/base_configs/{filename}",
        f"base_configs/{filename}",
        filename
    ]
    
    for path in paths:
        try:
            with open(path, 'r') as f:
                return f.read().splitlines()
        except FileNotFoundError:
            continue
            
    print(f"Error: Config file {filename} not found in search paths.")
    return []

def restore_device(device, password=None, use_keys=True):
    print(f"\n--- Connecting to {device['name']} ({device['host']}) ---")
    
    config_lines = load_config_file(device['base_config'])
    if not config_lines:
        print("Skipping due to missing config file.")
        return

    # Build connection dict with only netmiko-compatible parameters
    connection_params = {
        'device_type': device['device_type'],
        'host': device['host'],
        'username': 'admin',
    }
    
    # Use SSH key or password authentication
    if use_keys:
        connection_params['use_keys'] = True
        connection_params['key_file'] = os.path.expanduser('~/.ssh/id_ed25519')
    else:
        connection_params['password'] = password
        connection_params['secret'] = password

    try:
        net_connect = ConnectHandler(**connection_params)
        net_connect.enable()
        
        print(f"Connected to {device['name']}. Pushing base configuration...")
        output = net_connect.send_config_set(config_lines)
        print(output)
        
        # Save configuration
        print("Saving configuration...")
        net_connect.save_config()
        
        print(f"Successfully restored {device['name']}")
        net_connect.disconnect()
        
    except Exception as e:
        print(f"Failed to restore {device['name']}: {e}")

def main():
    print("WARNING: This script will overwrite the running configuration of your lab devices.")
    print("Ensure the base config files are correct before proceeding.")
    
    # Check if SSH key exists
    ssh_key_path = os.path.expanduser('~/.ssh/id_ed25519')
    has_ssh_key = os.path.exists(ssh_key_path)
    
    if has_ssh_key:
        print(f"\n✓ SSH key found: {ssh_key_path}")
        auth_choice = input("Use SSH key authentication? (y/n, default: y): ").strip().lower()
        use_keys = auth_choice != 'n'
    else:
        print("\nNo SSH key found. Will use password authentication.")
        use_keys = False
    
    password = None
    if not use_keys:
        password = getpass.getpass("\nEnter the admin password for all devices: ")
    
    print(f"\nAuthentication method: {'SSH Key' if use_keys else 'Password'}")
    input("\nPress Enter to continue or Ctrl+C to abort...")
    
    for device in DEVICES:
        restore_device(device, password, use_keys)

if __name__ == "__main__":
    main()
