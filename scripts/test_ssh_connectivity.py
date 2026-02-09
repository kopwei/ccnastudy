#!/usr/bin/env python3
"""
Simple SSH connectivity test for lab devices.
Tests SSH access to all devices in the inventory.
"""
import getpass
import sys
import os
from netmiko import ConnectHandler

# Import shared inventory
try:
    from inventory import DEVICES
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from inventory import DEVICES

def test_device_connection(device, password=None, use_keys=True):
    """Test SSH connection to a single device."""
    print(f"\nTesting {device['name']} ({device['host']})... ", end='', flush=True)
    
    # Build connection dict with only netmiko-compatible parameters
    connection_params = {
        'device_type': device['device_type'],
        'host': device['host'],
        'username': 'admin',
    }
    
    # Try SSH key authentication first if enabled
    if use_keys:
        connection_params['use_keys'] = True
        connection_params['key_file'] = os.path.expanduser('~/.ssh/id_ed25519')
    else:
        connection_params['password'] = password
        connection_params['secret'] = password
    
    try:
        net_connect = ConnectHandler(**connection_params)
        net_connect.enable()
        
        # Get hostname to verify we're connected
        output = net_connect.send_command('show running-config | include hostname')
        
        print(f"✓ SUCCESS")
        print(f"  Response: {output.strip()}")
        
        net_connect.disconnect()
        return True
        
    except Exception as e:
        print(f"✗ FAILED")
        print(f"  Error: {str(e)}")
        return False

def main():
    print("=" * 60)
    print("SSH Connectivity Test for Lab Devices")
    print("=" * 60)
    
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
    
    results = []
    for device in DEVICES:
        success = test_device_connection(device, password, use_keys)
        results.append((device['name'], success))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for name, success in results:
        status = "✓" if success else "✗"
        print(f"{status} {name}")
    
    print(f"\nTotal: {success_count}/{total_count} devices accessible")
    
    if success_count == total_count:
        print("\n🎉 All devices are accessible via SSH!")
    else:
        print("\n⚠️  Some devices are not accessible. Check network connectivity and credentials.")

if __name__ == "__main__":
    main()
