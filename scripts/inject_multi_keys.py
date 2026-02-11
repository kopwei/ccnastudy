#!/usr/bin/env python3
"""
Multi-SSH Key Injection Script for Cisco Devices.
Allows adding multiple SSH public keys for the same user.
Idempotent: Skips keys that already exist.
Verifies access after injection.
"""
import getpass
import sys
import os
import time
import textwrap
import argparse
import hashlib
import binascii
import subprocess
from netmiko import ConnectHandler

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
            print(f"Skipping {key_file_path}: Only RSA keys are supported by Cisco IOS.")
            return None
        return content
    except Exception as e:
        print(f"Error reading {key_file_path}: {e}")
        return None

def calculate_md5_fingerprint(public_key_string):
    """Calculates the MD5 fingerprint of a public key in Cisco format (hex, no colons)."""
    try:
        parts = public_key_string.split()
        if len(parts) < 2:
            return None
        key_data_base64 = parts[1]
        key_data = binascii.a2b_base64(key_data_base64)
        fp = hashlib.md5(key_data).hexdigest().upper()
        return fp
    except Exception as e:
        print(f"Error calculating hash: {e}")
        return None

def format_key_for_cisco(public_key_string):
    """Formats the key data for Cisco CLI."""
    parts = public_key_string.split()
    if len(parts) < 2:
        return None
    key_data = parts[1]
    return textwrap.wrap(key_data, 72)

def get_existing_key_hashes(net_connect, username):
    """Retrieves existing key hashes for a user from the device."""
    print("  Checking existing keys...")
    try:
        # We need to be out of config mode to run show command, or use 'do'
        # But we are in enable mode initially.
        cmd = f"show running-config | section ip ssh pubkey-chain"
        output = net_connect.send_command(cmd)
        
        hashes = set()
        current_user = None
        
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("username"):
                parts = line.split()
                if len(parts) >= 2:
                    current_user = parts[1]
            elif line.startswith("key-hash ssh-rsa") and current_user == username:
                parts = line.split()
                # Format: key-hash ssh-rsa <HASH>
                if len(parts) >= 3:
                     hashes.add(parts[2])
        return hashes
    except Exception as e:
        print(f"  Warning: Could not retrieve existing keys: {e}")
        return set()

def verify_ssh_access(host, username, key_file):
    """Verifies SSH access using the specific key without password."""
    print(f"  Verifying access to {host}...")
    cmd = [
        "ssh",
        "-o", "PasswordAuthentication=no",
        "-o", "StrictHostKeyChecking=no",
        "-o", "KexAlgorithms=+diffie-hellman-group14-sha1,diffie-hellman-group-exchange-sha1",
        "-o", "HostKeyAlgorithms=+ssh-rsa",
        "-o", "PubkeyAcceptedAlgorithms=+ssh-rsa",
        "-i", key_file,
        f"{username}@{host}",
        "show privilege"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and "15" in result.stdout:
            print(f"  ✓ Verification SUCCESS: SSH access functional with key.")
            return True
        else:
            print(f"  ✗ Verification FAILED: {result.stderr.strip()}")
            return False
    except Exception as e:
         print(f"  ✗ Verification ERROR: {e}")
         return False

def inject_keys_to_device(device, username, password, keys_map, use_keys=False, key_file=None):
    """
    Injects multiple keys into a single device.
    keys_map: List of dicts {'raw': str, 'formatted': list, 'hash': str}
    """
    print(f"\nProcessing {device['name']} ({device['host']})...")
    
    conn_params = {
        'device_type': device['device_type'],
        'host': device['host'],
        'username': username,
        'password': password,
        'secret': password,
        'timeout': 60,
        'allow_agent': False,
        'ssh_config_file': os.path.expanduser('~/.ssh/config') if os.path.exists(os.path.expanduser('~/.ssh/config')) else None,
        'disabled_algorithms': {'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']},
    }
    
    if use_keys:
        conn_params['use_keys'] = True
        conn_params['key_file'] = key_file
        conn_params['allow_agent'] = True

    try:
        net_connect = ConnectHandler(**conn_params)
        net_connect.enable()
        
        # Check existing keys
        existing_hashes = get_existing_key_hashes(net_connect, username)
        
        keys_to_add = []
        for k in keys_map:
            if k['hash'] in existing_hashes:
                print(f"  Info: Key with hash {k['hash'][:10]}... already exists. Skipping.")
            else:
                keys_to_add.append(k)
        
        if not keys_to_add:
            print("  No new keys to add.")
            net_connect.disconnect()
            return True

        # Enter global configuration first
        net_connect.write_channel("configure terminal\n")
        time.sleep(1)
        output = net_connect.read_channel()
        if "config" not in output and "#" not in output:
             print(f"  Warning: May not be in config mode: {output}")

        # Enter ip ssh pubkey-chain mode
        net_connect.write_channel("ip ssh pubkey-chain\n")
        time.sleep(1)
        net_connect.read_channel()
        
        # Enter username mode
        net_connect.write_channel(f"username {username}\n")
        time.sleep(1)
        net_connect.read_channel()

        # Iterate through NEW keys only
        for i, k_data in enumerate(keys_to_add):
            print(f"  Adding new key (Hash: {k_data['hash'][:10]}...)...")
            
            # Enter key-string mode
            net_connect.write_channel("key-string\n")
            time.sleep(1) 
            net_connect.read_channel()
            
            # Send key data line by line
            for line in k_data['formatted']:
                net_connect.write_channel(f"{line}\n")
                time.sleep(0.1)
            
            # Exit key-string mode
            net_connect.write_channel("exit\n")
            time.sleep(1)
            output = net_connect.read_channel()
            
            if "Error" in output or "Invalid" in output:
                 print(f"  Error detected while adding key: {output}")

        # Exit modes
        net_connect.write_channel("exit\n") # username
        time.sleep(0.5)
        net_connect.write_channel("exit\n") # pubkey-chain
        time.sleep(0.5)
        net_connect.write_channel("end\n") # config
        time.sleep(1)
        net_connect.read_channel()
        
        # Save
        print("  Saving configuration...")
        net_connect.write_channel("write memory\n")
        time.sleep(5)
        save_output = net_connect.read_channel()
        
        net_connect.disconnect()
        
        if "OK" in save_output or "#" in save_output:
            print(f"  ✓ Configuration updated for {device['name']}")
            return True
        else:
            print(f"  ⚠ Warning: Check save output: {save_output}")
            return True
        
    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Inject multiple SSH keys into Cisco devices')
    parser.add_argument('--key-dir', help='Directory containing .pub files')
    parser.add_argument('--keys', nargs='+', help='Paths to specific .pub files')
    parser.add_argument('--devices', nargs='+', help='Filter devices by name (e.g., 891 3560)')
    parser.add_argument('--use-ssh-key', help='Use this private key for connection auth (e.g., ~/.ssh/id_rsa_cisco)')
    # New arguments
    parser.add_argument('--username', help='Admin username (default: admin)')
    parser.add_argument('--yes', action='store_true', help='Run without interactive prompts')
    args = parser.parse_args()

    key_files = []
    if args.keys:
        key_files.extend(args.keys)
    elif args.key_dir:
        for f in os.listdir(args.key_dir):
            if f.endswith('.pub'):
                key_files.append(os.path.join(args.key_dir, f))
    
    if not key_files:
        print("No public key files specified. Use --keys or --key-dir.")
        return

    # Filter devices if specified
    if args.devices:
        target_devices = [d for d in DEVICES if any(f.lower() in d['name'].lower() for f in args.devices)]
        if not target_devices:
            print(f"No devices found matching: {args.devices}")
            print(f"Available: {[d['name'] for d in DEVICES]}")
            return
    else:
        target_devices = DEVICES

    print(f"Found {len(key_files)} key file(s) to process.")
    
    # Pre-process keys: Read content, format for Cisco, calculate Hash
    processed_keys = []
    for kf in key_files:
        content = get_public_key_content(kf)
        if content:
            fmt = format_key_for_cisco(content)
            fp = calculate_md5_fingerprint(content)
            if fmt and fp:
                processed_keys.append({'raw': content, 'formatted': fmt, 'hash': fp, 'path': kf})
    
    if not processed_keys:
        print("No valid RSA keys found to inject.")
        return

    # Determine username
    if args.yes:
        admin_username = args.username or "admin"
    else:
        default_user = args.username or "admin"
        try:
            u_input = input(f"\nAdmin username (default: {default_user}): ").strip()
            admin_username = u_input or default_user
        except EOFError:
            admin_username = default_user
    
    admin_password = ""
    use_keys = False
    key_file = None
    
    if args.use_ssh_key:
        key_path = os.path.expanduser(args.use_ssh_key)
        if os.path.exists(key_path):
            print(f"Using SSH key for connection: {key_path}")
            use_keys = True
            key_file = key_path
        else:
             print(f"Warning: SSH key not found at {key_path}, falling back to password.")

    if not use_keys:
        if args.yes:
             print("Error: Password required but running in non-interactive mode. Use --use-ssh-key.")
             return
        admin_password = getpass.getpass("Admin password: ")
    
    if not args.yes:
        print(f"\nTarget devices: {[d['name'] for d in target_devices]}")
        try:
            confirm = input("Continue? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Aborted.")
                return
        except EOFError:
            print("Aborted (EOF).")
            return

    for device in target_devices:
        success = inject_keys_to_device(device, admin_username, admin_password, processed_keys, use_keys, key_file)
        
        # Post-injection verification
        if success and args.use_ssh_key:
             verify_ssh_access(device['host'], admin_username, args.use_ssh_key)
        elif success and not args.use_ssh_key:
             # Just try using the key we just injected if available
             # Assuming keys[0] is one of them.
             if args.keys:
                 # Check if matching private key exists?
                 # Assume key file path is provided in args.keys[0] which is public key
                 priv_key_path = args.keys[0].replace('.pub', '')
                 if os.path.exists(priv_key_path):
                     verify_ssh_access(device['host'], admin_username, priv_key_path)
                 else:
                     print("  Skipping verification (private key not found for injected public key).")

if __name__ == "__main__":
    main()
