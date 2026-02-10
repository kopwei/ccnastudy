import getpass
import time
import sys
import os
from netmiko import ConnectHandler

try:
    from inventory import DEVICES
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from inventory import DEVICES

# SSH key path - use the 2048-bit RSA key compatible with older Cisco IOS
SSH_KEY_PATH = os.path.expanduser('~/.ssh/id_rsa_cisco')

def load_config_file(filename):
    """Load a base config file, searching in common paths."""
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

    # Build base connection dict
    base_params = {
        'device_type': device['device_type'],
        'host': device['host'],
        'username': 'admin',
        'timeout': 30,
        'conn_timeout': 20,
        # Re-enable ssh-rsa which modern Paramiko disables by default
        'disabled_algorithms': {'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']},
    }
    
    # Try SSH key first, fall back to password if it fails
    net_connect = None
    if use_keys:
        key_params = base_params.copy()
        key_params['use_keys'] = True
        key_params['key_file'] = SSH_KEY_PATH
        key_params['allow_agent'] = True
        if password:
            key_params['password'] = password
            key_params['secret'] = password
        try:
            net_connect = ConnectHandler(**key_params)
        except Exception:
            print(f"  SSH key auth failed, falling back to password...")
    
    if net_connect is None and password:
        pwd_params = base_params.copy()
        pwd_params['password'] = password
        pwd_params['secret'] = password
        net_connect = ConnectHandler(**pwd_params)
    elif net_connect is None:
        print(f"  ✗ No authentication method available for {device['name']}")
        return

    try:
        net_connect.enable()
        
        print(f"Connected to {device['name']}. Pushing base configuration...")
        output = net_connect.send_config_set(config_lines)
        print(output)
        
        # After hostname change, the prompt changes. Re-detect it.
        net_connect.set_base_prompt()
        
        # Save configuration
        print("Saving configuration...")
        save_output = net_connect.send_command("write memory", read_timeout=15)
        print(save_output)
        
        print(f"✓ Successfully restored {device['name']}")
        net_connect.disconnect()
        
    except Exception as e:
        print(f"✗ Failed to restore {device['name']}: {e}")

def main():
    print("WARNING: This script will overwrite the running configuration of your lab devices.")
    print("Ensure the base config files are correct before proceeding.")
    
    # Check if SSH key exists
    has_ssh_key = os.path.exists(SSH_KEY_PATH)
    
    if has_ssh_key:
        print(f"\n✓ SSH key found: {SSH_KEY_PATH}")
        auth_choice = input("Use SSH key authentication? (y/n, default: y): ").strip().lower()
        use_keys = auth_choice != 'n'
    else:
        print(f"\nNo SSH key found at {SSH_KEY_PATH}. Will use password authentication.")
        use_keys = False
    
    # Always ask for password (needed for enable and as fallback)
    password = getpass.getpass("\nEnter the admin password for all devices: ")
    
    print(f"\nAuthentication method: {'SSH Key + password fallback' if use_keys else 'Password'}")
    input("\nPress Enter to continue or Ctrl+C to abort...")
    
    for device in DEVICES:
        restore_device(device, password, use_keys)

if __name__ == "__main__":
    main()
