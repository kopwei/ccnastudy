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

def test_device_connection(device, password):
    """Test SSH connection to a single device."""
    print(f"\nTesting {device['name']} ({device['host']})... ", end='', flush=True)
    
    # Build connection dict with only netmiko-compatible parameters
    test_device = {
        'device_type': device['device_type'],
        'host': device['host'],
        'username': 'admin',
        'password': password,
        'secret': password
    }
    
    try:
        net_connect = ConnectHandler(**test_device)
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
    
    password = getpass.getpass("\nEnter the admin password for all devices: ")
    
    results = []
    for device in DEVICES:
        success = test_device_connection(device, password)
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
