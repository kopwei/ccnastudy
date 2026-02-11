#!/usr/bin/env python3
"""
STP Convergence Monitor - Observe STP state transitions in real-time.
This script polls switches and displays the STP role and state for specific ports.
"""
import time
import os
import sys
import argparse
from netmiko import ConnectHandler
from prettytable import PrettyTable

try:
    from inventory import DEVICES
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from inventory import DEVICES

def get_stp_status(net_connect, vlan=10):
    """Get STP status for a specific VLAN."""
    cmd = f"show spanning-tree vlan {vlan}"
    output = net_connect.send_command(cmd)
    
    results = []
    # Simple parser for "show spanning-tree vlan X"
    # Port      Role Sts Cost      Prio.Nbr Type
    # --------- ---- --- --------- -------- --------------------------------
    # Gi0/1     Root FWD 4         128.1    P2p 
    
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
    connections = {}
    
    print(f"Connecting to {len(switches)} switches...")
    for sw in switches:
        try:
            # Note: In a real lab, we'd use SSH keys or prompt for password
            # For this script, we assume SSH key is set up as per previous work
            conn = ConnectHandler(
                device_type=sw['device_type'],
                host=sw['host'],
                username='admin',
                use_keys=True,
                key_file=os.path.expanduser('~/.ssh/id_rsa_cisco'),
                disabled_algorithms={'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']}
            )
            connections[sw['name']] = conn
            print(f"  Connected to {sw['name']}")
        except Exception as e:
            print(f"  Failed to connect to {sw['name']}: {e}")

    if not connections:
        print("No connections established. Exiting.")
        return

    try:
        while True:
            os.system('clear' if os.name == 'posix' else 'cls')
            print(f"STP Real-Time Monitor (VLAN {vlan}) - Press Ctrl+C to stop")
            print(f"Time: {time.strftime('%H:%M:%S')}\n")
            
            table = PrettyTable()
            table.field_names = ["Switch", "Interface", "Role", "Status (STP State)"]
            
            for name, conn in connections.items():
                try:
                    status = get_stp_status(conn, vlan)
                    if not status:
                        table.add_row([name, "N/A", "N/A", "No active ports in VLAN"])
                    for entry in status:
                        # Highlight FWD in green or BLK in red if using color, 
                        # but keeping it simple for now
                        table.add_row([name, entry['interface'], entry['role'], entry['status']])
                except Exception as e:
                    table.add_row([name, "Error", "-", str(e)])
            
            print(table)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
    finally:
        for conn in connections.values():
            conn.disconnect()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='STP Real-Time Monitor')
    parser.add_argument('--vlan', type=int, default=10, help='VLAN to monitor (default: 10)')
    parser.add_argument('--interval', type=int, default=2, help='Poll interval in seconds (default: 2)')
    args = parser.parse_args()
    
    monitor(vlan=args.vlan, interval=args.interval)
