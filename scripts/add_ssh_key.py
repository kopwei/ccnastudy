#!/usr/bin/env python3
"""
Script to add an SSH public key to Cisco IOS devices.
Properly formats the key for Cisco's ip ssh pubkey-chain command.
"""
import getpass
import sys
import os
import time
import textwrap
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException

# Import shared inventory
try:
    from inventory import DEVICES
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from inventory import DEVICES

def get_public_key_content(key_file_path):
    """Reads and validates the content of the public key file."""
    try:
        with open(key_file_path, 'r') as f:
            content = f.read().strip()
        
        if not content.startswith('ssh-rsa '):
            print(f"Error: Cisco IOS only supports RSA keys.")
            print(f"Your key starts with: {content[:20]}...")
            return None
        
        return content
    except FileNotFoundError:
        print(f"Error: Public key file not found at {key_file_path}")
        return None
    except Exception as e:
        print(f"Error reading public key file: {e}")
        return None

def format_key_for_cisco(public_key_string):
    """
    Format the public key for Cisco IOS.
    Cisco expects just the base64 portion, wrapped at ~72 characters.
    """
    parts = public_key_string.split()
    if len(parts) < 2:
        return None
    
    # parts[0] = ssh-rsa
    # parts[1] = base64 key data
    key_data = parts[1]
    
    # Wrap the key at 72 characters (Cisco terminal width limitation)
    wrapped_lines = textwrap.wrap(key_data, 72)
    return wrapped_lines

def add_key_to_device(device, username, password, key_lines):
    """Adds the public key to a single device."""
    print(f"\nAdding SSH key to {device['name']} ({device['host']})...")
    
    netmiko_device = {
        'device_type': device['device_type'],
        'host': device['host'],
        'username': username,
        'password': password,
        'secret': password,
        'timeout': 30,
    }
    
    try:
        net_connect = ConnectHandler(**netmiko_device)
        
        if not net_connect.check_enable_mode():
            net_connect.enable()
        
        # Enter config mode
        net_connect.write_channel("configure terminal\n")
        time.sleep(0.5)
        net_connect.read_channel()
        
        # Enter pubkey-chain mode
        net_connect.write_channel("ip ssh pubkey-chain\n")
        time.sleep(0.5)
        net_connect.read_channel()
        
        # Specify username
        net_connect.write_channel(f"username {username}\n")
        time.sleep(0.5)
        net_connect.read_channel()
        
        # Enter key-string mode
        net_connect.write_channel("key-string\n")
        time.sleep(0.5)
        net_connect.read_channel()
        
        # Send each line of the wrapped key
        for line in key_lines:
            net_connect.write_channel(f"{line}\n")
            time.sleep(0.2)
        
        # Read any response
        time.sleep(0.5)
        output = net_connect.read_channel()
        
        # Exit key-string mode
        net_connect.write_channel("exit\n")
        time.sleep(0.5)
        net_connect.read_channel()
        
        # Exit username mode
        net_connect.write_channel("exit\n")
        time.sleep(0.5)
        net_connect.read_channel()
        
        # Exit pubkey-chain mode
        net_connect.write_channel("exit\n")
        time.sleep(0.5)
        net_connect.read_channel()
        
        # Exit config mode
        net_connect.write_channel("end\n")
        time.sleep(0.5)
        net_connect.read_channel()
        
        # Save configuration
        net_connect.write_channel("write memory\n")
        time.sleep(2.0)
        save_output = net_connect.read_channel()
        
        # Verify the key was added
        verify_output = net_connect.send_command("show running-config | section ip ssh pubkey")
        
        net_connect.disconnect()
        
        if "key-hash" in verify_output or len(verify_output.split('\n')) > 2:
            print(f"  ✓ Key successfully added to {device['name']}")
            return True
        else:
            print(f"  ⚠ Key may not have been saved properly on {device['name']}")
            print(f"  Config: {verify_output}")
            return False
            
    except NetmikoAuthenticationException:
        print(f"  ✗ FAILED: Authentication failed for {device['name']}.")
    except NetmikoTimeoutException:
        print(f"  ✗ FAILED: Connection timed out for {device['name']}.")
    except Exception as e:
        print(f"  ✗ FAILED: Error for {device['name']}: {str(e)}")
    return False

def verify_ssh_key_auth(device, username, private_key_path):
    """Verify that SSH key authentication works."""
    print(f"  Testing key auth for {device['name']}... ", end='', flush=True)
    
    netmiko_device = {
        'device_type': device['device_type'],
        'host': device['host'],
        'username': username,
        'use_keys': True,
        'key_file': private_key_path,
        'timeout': 15,
        'allow_agent': False,
    }
    
    try:
        net_connect = ConnectHandler(**netmiko_device)
        output = net_connect.send_command('show version | include uptime')
        net_connect.disconnect()
        print(f"✓ SUCCESS")
        return True
    except Exception as e:
        print(f"✗ FAILED ({str(e)[:40]})")
        return False

def main():
    print("=" * 60)
    print("Add SSH Public Key to Cisco Lab Devices")
    print("=" * 60)
    print("\nNOTE: Cisco IOS only supports RSA keys!")
    
    default_key = "~/.ssh/id_rsa_cisco.pub"
    if not os.path.exists(os.path.expanduser(default_key)):
        default_key = "~/.ssh/id_rsa.pub"
    
    key_input = input(f"\nEnter RSA public key path (default: {default_key}): ").strip()
    public_key_file = os.path.expanduser(key_input if key_input else default_key)

    public_key_string = get_public_key_content(public_key_file)
    if not public_key_string:
        return

    key_lines = format_key_for_cisco(public_key_string)
    if not key_lines:
        print("Error: Could not format the key.")
        return
        
    print(f"\n✓ Key loaded and formatted into {len(key_lines)} lines")
    
    admin_username = input("\nAdmin username (default: admin): ").strip() or "admin"
    admin_password = getpass.getpass("Admin password: ")
    
    print(f"\nAdding key for '{admin_username}' on {len(DEVICES)} devices.")
    confirm = input("Continue? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Aborted.")
        return
    
    success_count = 0
    added_devices = []
    
    for device in DEVICES:
        if add_key_to_device(device, admin_username, admin_password, key_lines):
            success_count += 1
            added_devices.append(device)
    
    print("\n" + "=" * 60)
    print(f"KEY ADDITION: {success_count}/{len(DEVICES)} devices")
    print("=" * 60)
    
    if added_devices:
        print("\nVerifying SSH key authentication...")
        private_key_path = public_key_file.replace('.pub', '')
        verified = 0
        for device in added_devices:
            if verify_ssh_key_auth(device, admin_username, private_key_path):
                verified += 1
        
        print(f"\nVERIFIED: {verified}/{len(added_devices)} devices")
        if verified == len(added_devices):
            print("\n🎉 All devices working with SSH key authentication!")
    else:
        print("\n⚠️ No devices were updated.")

if __name__ == "__main__":
    main()
