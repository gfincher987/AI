import yaml
from netmiko import ConnectHandler
import re
import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_device_connection(device_info):
    """Establishes an SSH connection to the device."""
    return ConnectHandler(**device_info)

def parse_inventory_output(output, platform):
    """Parses the 'show inventory' output to find optics information."""
    optics_info = {}

    if platform == 'cisco_nxos':
        # Parse JSON output for NX-OS
        try:
            inventory_data = json.loads(output)
            for item in inventory_data.get("TABLE_inv", {}).get("ROW_inv", []):
                name = item.get("name")
                descr = item.get("desc")
                pid = item.get("productid", "N/A")
                vid = item.get("vid", "N/A")
                sn = item.get("serialnum", "N/A")

                if name and descr and pid:
                    optics_info[name] = {
                        "Description": descr,
                        "PID": pid,
                        "VID": vid,
                        "SN": sn
                    }
        except json.JSONDecodeError:
            print("Failed to parse JSON output for NX-OS.")
    else:
        # Updated regex pattern for IOS-XR and IOS-XE
        pattern = r'NAME: "(.*)",\s+DESCR: "(.*)"\s+PID: (\S+)\s*,\s*VID: (\S+)\s*,\s*SN: (\S+)'
        matches = re.finditer(pattern, output)
        for match in matches:
            name, descr, pid, vid, sn = match.groups()
            if 'port' in name.lower() or 'GigE' in name or 'TenGigE' in name:
                optics_info[name] = {
                    "Description": descr,
                    "PID": pid,
                    "VID": vid,
                    "SN": sn
                }

    return optics_info

def load_device_info(yaml_file):
    """Loads device information from a YAML file."""
    with open(yaml_file, 'r') as file:
        return yaml.safe_load(file)

def save_to_csv(optics_data, output_file):
    """Saves the optics information to a CSV file."""
    with open(output_file, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        # Write header
        csv_writer.writerow(["Device Name", "Port", "Description", "PID", "VID", "SN"])
        # Write data
        for device_name, optics_info in optics_data.items():
            for port, details in optics_info.items():
                if isinstance(details, dict):
                    csv_writer.writerow([device_name, port, details.get("Description"), details.get("PID"), details.get("VID"), details.get("SN")])
                else:
                    csv_writer.writerow([device_name, port, details, "N/A", "N/A", "N/A"])

def save_failed_connections_to_csv(failed_connections, output_file):
    """Saves the failed connection information to a CSV file."""
    with open(output_file, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        # Write header
        csv_writer.writerow(["Device Name", "Error Message"])
        # Write data
        for device_name, error_message in failed_connections.items():
            csv_writer.writerow([device_name, error_message])

def process_device(device_name, device_info):
    """Processes a single device and retrieves optics information."""
    try:
        print(f"\nConnecting to device: {device_name}...")
        connection = get_device_connection(device_info)

        # Determine the platform and appropriate command
        platform = device_info.get('device_type')
        if platform == 'cisco_xr':
            command = "show inventory"
        elif platform == 'cisco_xe':
            command = "show inventory"
        elif platform == 'cisco_nxos':
            command = "show inventory all | json"
        else:
            print(f"Unsupported platform for device {device_name}")
            return device_name, {}, f"Unsupported platform: {platform}"

        # Run the command
        print(f"Running '{command}'...")
        output = connection.send_command(command)

        # Parse the output to find optics information
        optics_info = parse_inventory_output(output, platform)

        # Disconnect from the device
        connection.disconnect()

        print(f"Completed processing device: {device_name}")
        return device_name, optics_info, None

    except Exception as e:
        error_message = str(e)
        print(f"An error occurred while processing {device_name}: {error_message}")
        return device_name, {}, error_message

def main():
    # Replace with your YAML file path
    yaml_file = input("Enter the path to the YAML file: ")
    output_csv = input("Enter the path for the output CSV file: ")

    try:
        # Load device information from YAML file
        devices = load_device_info(yaml_file)
        optics_data = {}
        failed_connections = {}

        # Use ThreadPoolExecutor to process devices in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_device = {executor.submit(process_device, name, info): name for name, info in devices.items()}

            for future in as_completed(future_to_device):
                device_name = future_to_device[future]
                try:
                    name, optics_info, error_message = future.result()
                    
                    if error_message:
                        # Device failed to connect
                        failed_connections[name] = error_message
                    else:
                        # Device connected successfully
                        optics_data[name] = optics_info

                        # Display the optics information
                        print(f"\nOptics Information for {name}:")
                        if optics_info:
                            for port, details in optics_info.items():
                                print(f"{port}: {details}")
                        else:
                            print("No optics information found.")
                except Exception as e:
                    print(f"An error occurred for {device_name}: {e}")
                    failed_connections[device_name] = str(e)

        # Save the optics information to a CSV file
        save_to_csv(optics_data, output_csv)
        print(f"\nOptics information saved to {output_csv}")

        # Save failed connections to a separate CSV file
        if failed_connections:
            failed_csv = output_csv.replace('.csv', '_failed_connections.csv')
            save_failed_connections_to_csv(failed_connections, failed_csv)
            print(f"Failed connections saved to {failed_csv}")
            
            # Display summary of failed connections
            print(f"\nSummary of failed connections ({len(failed_connections)} devices):")
            for device, error in failed_connections.items():
                print(f"  {device}: {error}")
        else:
            print("\nAll devices connected successfully!")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
