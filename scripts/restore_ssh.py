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

def restore_device(device, password):
    print(f"\n--- Connecting to {device['name']} ({device['host']}) ---")
    
    # Add credentials to the device dict
    device['username'] = 'admin'
    device['password'] = password
    device['secret'] = password # Assuming enable password is same
    
    config_lines = load_config_file(device['base_config'])
    if not config_lines:
        print("Skipping due to missing config file.")
        return

    try:
        net_connect = ConnectHandler(**device)
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
    print("Ensure you have updated the 'DEVICES' list in the script with the correct credentials or enter it now.")
    
    # Prompt for password to avoid hardcoding it in the script for safety
    password = getpass.getpass("Enter the unified admin password for all devices: ")
    
    for device in DEVICES:
        restore_device(device, password)

if __name__ == "__main__":
    main()
