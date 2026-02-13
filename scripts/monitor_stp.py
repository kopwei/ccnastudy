#!/usr/bin/env python3
"""
STP Convergence Monitor - Observe STP state transitions in real-time.
This script polls switches and displays the STP role and state for specific ports.
"""
import time
import os
import sys
import argparse
import subprocess
from netmiko import ConnectHandler
from prettytable import PrettyTable

try:
    from inventory import DEVICES
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from inventory import DEVICES

def get_host_alias(ip_address):
    """Map inventory IP to SSH Config Host Alias."""
    mapping = {
        '192.168.2.21': '2960s1',
        '192.168.2.22': '2960s2',
        '192.168.2.38': '3850s1',
        '192.168.2.39': '3850s2',
    }
    return mapping.get(ip_address, ip_address)

def run_ssh_command(host, command):
    """Run a command via system SSH and return output."""
    # Use the alias if available, otherwise fallback to IP
    # We include options to batch mode to avoid hanging
    ssh_cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=5",
        host,
        command
    ]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            if "Permission denied" in result.stderr:
                return f"Error: Permission denied (Check SSH keys)"
            return f"Error: SSH failed ({result.stderr.strip()})"
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Error: Timeout"
    except Exception as e:
        return f"Error: {str(e)}"

def get_stp_status(host_alias, vlan=10):
    """Get STP status for a specific VLAN."""
    cmd = f"show spanning-tree vlan {vlan}"
    output = run_ssh_command(host_alias, cmd)
    
    if output.startswith("Error"):
        # Raise error to be caught by main loop
        raise Exception(output)

    results = []
    # Simple parser for "show spanning-tree vlan X"
    lines = output.splitlines()
    start_parsing = False
    for line in lines:
        if "Interface" in line and "Role" in line and "Sts" in line:
            start_parsing = True
            continue
        if start_parsing and line.strip() and not line.startswith("-"):
            parts = line.split()
            if len(parts) >= 3:
                results.append({
                    'interface': parts[0],
                    'role': parts[1],
                    'status': parts[2]
                })
    return results

def monitor(vlan=10, interval=2):
    """Monitor STP status across all switches."""
    switches = [d for d in DEVICES if d['role'] in ['l2_switch', 'l3_switch']]
    
    # Prepare aliases once
    device_targets = []
    for sw in switches:
        alias = get_host_alias(sw['host'])
        device_targets.append({'name': sw['name'], 'alias': alias})
        print(f"  Target: {sw['name']} -> {alias}")

    if not device_targets:
        print("No L2/L3 switches found in inventory.")
        return

    try:
        while True:
            os.system('clear' if os.name == 'posix' else 'cls')
            print(f"STP Real-Time Monitor (VLAN {vlan}) - Press Ctrl+C to stop")
            print(f"Time: {time.strftime('%H:%M:%S')}\n")
            
            table = PrettyTable()
            table.field_names = ["Switch", "Interface", "Role", "Status (STP State)"]
            
            for dev in device_targets:
                try:
                    status = get_stp_status(dev['alias'], vlan)
                    if not status:
                         # Either command empty or empty VLAN
                         # We check if it returned error code first inside get_stp_status
                         table.add_row([dev['name'], "-", "-", "No active STP ports"])
                    else:
                        for entry in status:
                            table.add_row([dev['name'], entry['interface'], entry['role'], entry['status']])
                except Exception as e:
                    table.add_row([dev['name'], "Error", "-", str(e)])
            
            print(table)
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='STP Real-Time Monitor')
    parser.add_argument('--vlan', type=int, default=10, help='VLAN to monitor (default: 10)')
    parser.add_argument('--interval', type=int, default=2, help='Poll interval in seconds (default: 2)')
    args = parser.parse_args()
    
    monitor(vlan=args.vlan, interval=args.interval)
