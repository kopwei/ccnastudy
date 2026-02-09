import serial
import serial.tools.list_ports
import time
import os
import sys

# Import shared inventory
try:
    from inventory import DEVICES
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from inventory import DEVICES

def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

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

def configure_via_serial(port, device_name, config_file):
    print(f"\nInitializing serial connection to {port} for {device_name}...")
    
    try:
        # Standard Cisco Console Settings
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

        print("Connection established. Checking for prompt...")
        ser.write(b'\r\n')
        time.sleep(1)
        output = ser.read_all().decode('utf-8', errors='ignore')
        print(f"Device Output:\n{output}")
        
        # Simple interactive check - assumes we might need to enable
        # ideally we would use netmiko for serial too, but doing it raw as requested "configure them line by line"
        # and checking if ready.
        
        config_lines = load_config_file(config_file)
        if not config_lines:
            return

        print(f"Pushing {len(config_lines)} configuration lines...")
        
        # Send enable if needed (simple heuristic)
        if '>' in output:
            ser.write(b'enable\r\n')
            time.sleep(1)
            # Assuming no password for enable in recovery mode or we interactively ask, 
            # but usually this script assumes we have console access.

        # Enter config mode
        ser.write(b'configure terminal\r\n')
        time.sleep(1)
        
        for line in config_lines:
            print(f"Sending: {line}")
            ser.write(line.encode('utf-8') + b'\r\n')
            time.sleep(0.1) # Small delay for buffer
            
        # Exit and Save
        ser.write(b'end\r\n')
        time.sleep(1)
        ser.write(b'write memory\r\n')
        time.sleep(2)
        
        print("Configuration complete.")
        ser.close()

    except Exception as e:
        print(f"Error during serial config: {e}")

def main():
    print("--- Cisco Lab Restore Tool (Serial) ---")
    
    while True:
        print("\nAvailable Devices:")
        for idx, device in enumerate(DEVICES):
            print(f"{idx + 1}. {device['name']} (Base Config: {device['base_config']})")
        print("q. Quit")
        
        choice = input("\nSelect a device to restore > ")
        if choice.lower() == 'q':
            break
            
        try:
            dev_idx = int(choice) - 1
            if 0 <= dev_idx < len(DEVICES):
                selected_device = DEVICES[dev_idx]
            else:
                print("Invalid selection.")
                continue
        except ValueError:
            print("Invalid input.")
            continue

        ports = list_serial_ports()
        if not ports:
            print("No serial ports found! Check your drivers and connections.")
            # For testing without hardware, we might allow manual entry
            manual = input("Enter port path manually (or enter to retry): ")
            if manual:
                ports = [manual]
            else:
                continue

        print("\nAvailable Serial Ports:")
        for idx, port in enumerate(ports):
            print(f"{idx + 1}. {port}")
            
        port_choice = input("Select serial port > ")
        try:
            port_idx = int(port_choice) - 1
            if 0 <= port_idx < len(ports):
                selected_port = ports[port_idx]
            else:
                print("Invalid selection.")
                continue
        except ValueError:
            print("Invalid input.")
            continue
            
        print(f"\n*** ACTION REQUIRED ***")
        print(f"Please connect the console cable to: {selected_device['name']}")
        print(f"Using Port: {selected_port}")
        input("Press Enter when ready...")
        
        configure_via_serial(selected_port, selected_device['name'], selected_device['base_config'])
        
        cont = input("\nRestore another device? (y/n): ")
        if cont.lower() != 'y':
            break

if __name__ == "__main__":
    main()
