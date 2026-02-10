#!/usr/bin/env python3
"""
Serial console recovery script for devices that lost management access.
Pushes minimal recovery config via serial console to restore DHCP-based
management connectivity.

Usage:
  python3 recover_serial.py
  
  Then follow the prompts to select device and connect console cable.
"""
import serial
import serial.tools.list_ports
import time
import sys
import os

# Recovery configs - minimal commands to restore management access
# These ONLY set up management connectivity, nothing else.
RECOVERY_CONFIGS = {
    'router_891': {
        'name': 'Router 891',
        'commands': [
            'interface FastEthernet0',
            ' no switchport',
            ' ip address dhcp',
            ' no shutdown',
            'ip domain-name homelab',
            'ip route 0.0.0.0 0.0.0.0 192.168.2.1',
            'line vty 0 4',
            ' transport input ssh',
            ' login local',
        ]
    },
    'switch_3560cx': {
        'name': 'Switch 3560CX',
        'commands': [
            'vlan 99',
            ' name Management',
            'interface Vlan99',
            ' ip address dhcp',
            ' no shutdown',
            'ip routing',
            'ip route 0.0.0.0 0.0.0.0 192.168.2.1',
            'line vty 0 4',
            ' transport input ssh',
            ' login local',
        ]
    },
}


def list_serial_ports():
    """List available serial ports."""
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]


def read_output(ser, wait=1):
    """Read all available output from serial."""
    time.sleep(wait)
    output = ser.read_all().decode('utf-8', errors='ignore')
    return output


def recover_device(port, device_key):
    """Push recovery config via serial console."""
    config = RECOVERY_CONFIGS[device_key]
    print(f"\n--- Recovering {config['name']} via {port} ---")

    try:
        ser = serial.Serial(
            port=port,
            baudrate=9600,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=2
        )

        if not ser.is_open:
            ser.open()

        # Wake up the device
        print("Connecting to device...")
        ser.write(b'\r\n')
        output = read_output(ser, 2)
        print(f"Device output: {output}")

        # Try to get to privileged mode
        if '>' in output:
            print("In user mode, entering enable mode...")
            ser.write(b'enable\r\n')
            output = read_output(ser, 1)
            print(f"  {output}")
            # If password prompt, try empty password
            if 'Password' in output:
                ser.write(b'\r\n')
                output = read_output(ser, 1)

        # Enter config mode
        print("Entering configuration mode...")
        ser.write(b'configure terminal\r\n')
        output = read_output(ser, 1)
        print(f"  {output}")

        # Push recovery commands
        print(f"Pushing {len(config['commands'])} recovery commands...")
        for cmd in config['commands']:
            print(f"  Sending: {cmd}")
            ser.write(cmd.encode('utf-8') + b'\r\n')
            time.sleep(0.3)
            output = read_output(ser, 0.3)
            if output.strip():
                print(f"    {output.strip()}")

        # Exit config mode and save
        print("\nExiting config mode and saving...")
        ser.write(b'end\r\n')
        output = read_output(ser, 1)
        print(f"  {output}")

        ser.write(b'write memory\r\n')
        output = read_output(ser, 3)
        print(f"  {output}")

        # Verify - check interface status
        print("\nVerifying management interface...")
        ser.write(b'show ip interface brief | include Vlan99|FastEthernet0\r\n')
        output = read_output(ser, 2)
        print(f"  {output}")

        print(f"\n✓ Recovery config pushed to {config['name']}")
        print("  Wait ~30 seconds for DHCP to assign an IP, then verify ping.")
        ser.close()

    except Exception as e:
        print(f"✗ Error: {e}")


def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║     Serial Console Recovery Tool                       ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print("\nThis tool recovers management access on devices that lost")
    print("their management configuration.\n")

    while True:
        print("\nDevices available for recovery:")
        keys = list(RECOVERY_CONFIGS.keys())
        for idx, key in enumerate(keys):
            print(f"  {idx + 1}. {RECOVERY_CONFIGS[key]['name']}")
        print("  q. Quit")

        choice = input("\nSelect device > ").strip()
        if choice.lower() == 'q':
            break

        try:
            dev_idx = int(choice) - 1
            if dev_idx < 0 or dev_idx >= len(keys):
                print("Invalid selection.")
                continue
            device_key = keys[dev_idx]
        except ValueError:
            print("Invalid input.")
            continue

        # Find serial ports
        ports = list_serial_ports()
        if not ports:
            manual = input("No serial ports found. Enter port path manually: ").strip()
            if manual:
                ports = [manual]
            else:
                continue

        if len(ports) == 1:
            selected_port = ports[0]
            print(f"\nUsing serial port: {selected_port}")
        else:
            print("\nAvailable serial ports:")
            for idx, port in enumerate(ports):
                print(f"  {idx + 1}. {port}")
            port_choice = input("Select port > ").strip()
            try:
                port_idx = int(port_choice) - 1
                selected_port = ports[port_idx]
            except (ValueError, IndexError):
                print("Invalid selection.")
                continue

        print(f"\n*** Connect console cable to {RECOVERY_CONFIGS[device_key]['name']} ***")
        input("Press Enter when ready...")

        recover_device(selected_port, device_key)

        cont = input("\nRecover another device? (y/n): ").strip().lower()
        if cont != 'y':
            break

    print("\nDone. Run 'ping 192.168.2.x' to verify connectivity.")


if __name__ == "__main__":
    main()
