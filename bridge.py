import serial
import serial.tools.list_ports
import time
import csv
import os
import threading
from datetime import datetime

# --- Configuration ---
BAUD_RATE = 115200
DATA_FILE = 'live_data.csv'
COMMAND_FILE = 'command.txt'
MAX_ROWS = 10000  # Keep only the last N rows to prevent file bloat

class SerialBridge:
    def __init__(self, baud_rate):
        self.baud_rate = baud_rate
        self.ser = None
        self.running = False
        self.port = self.find_esp32_port()

    def find_esp32_port(self):
        """Auto-detects a likely ESP32/Arduino port."""
        ports = list(serial.tools.list_ports.comports())
        print("🔍 Scanning for devices...")
        for p in ports:
            print(f"   Found: {p.device} - {p.description}")
            # Heuristic: Look for common USB-Serial chipsets
            if "CP210" in p.description or "CH340" in p.description or "USB Serial" in p.description or "Arduino" in p.description:
                print(f"✅ Auto-selected: {p.device}")
                return p.device
        
        # Fallback if nothing obvious found
        if ports:
            print(f"⚠️ No specific driver found, defaulting to first port: {ports[0].device}")
            return ports[0].device
        
        print("❌ No serial ports found! Check connections.")
        return None

    def connect(self):
        """Attempts to connect to the serial port."""
        if not self.port:
            self.port = self.find_esp32_port()
            if not self.port: return False

        try:
            self.ser = serial.Serial(self.port, self.baud_rate, timeout=1)
            print(f"✅ Connected to {self.port} at {self.baud_rate} baud.")
            return True
        except serial.SerialException as e:
            print(f"❌ Connection Failed: {e}")
            return False

    def trim_csv(self):
        """Keeps the CSV file size manageable."""
        if not os.path.exists(DATA_FILE): return
        
        try:
            with open(DATA_FILE, 'r') as f:
                lines = f.readlines()
            
            if len(lines) > MAX_ROWS:
                header = lines[0]
                kept_lines = lines[-(MAX_ROWS-1):] # Keep header + last N-1
                
                with open(DATA_FILE, 'w') as f:
                    f.write(header)
                    f.writelines(kept_lines)
                # print("🧹 Trimmed CSV file.")
        except Exception as e:
            print(f"⚠️ Trim Error: {e}")

    def read_serial(self):
        """Reads data from Serial and writes to CSV."""
        if not self.ser or not self.ser.is_open:
            return

        row_count = 0

        while self.running:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    
                    if line.startswith("DATA,"):
                        # Expected format: DATA,sensor_value,voltage,relay_state
                        parts = line.split(',')
                        if len(parts) >= 3:
                            sensor_val = parts[1]
                            voltage = parts[2]
                            # Handle optional relay state (backward compatibility)
                            relay_state = parts[3] if len(parts) > 3 else "0"
                            
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            # Ensure file exists with header
                            if not os.path.exists(DATA_FILE):
                                with open(DATA_FILE, 'w', newline='') as f:
                                    writer = csv.writer(f)
                                    writer.writerow(['timestamp', 'sensor_value', 'voltage', 'relay_state'])

                            # Append to CSV
                            with open(DATA_FILE, 'a', newline='') as f:
                                writer = csv.writer(f)
                                writer.writerow([timestamp, sensor_val, voltage, relay_state])
                            
                            print(f"📥 Received: {sensor_val} | {voltage}V | Relay: {'ON' if relay_state=='1' else 'OFF'}")
                            
                            # Trim periodically
                            row_count += 1
                            if row_count > 100:
                                self.trim_csv()
                                row_count = 0

            except Exception as e:
                print(f"⚠️ Read Error: {e}")
                time.sleep(1)

    def write_serial(self):
        """Reads command file and sends to Serial."""
        last_command = None
        
        while self.running:
            try:
                if os.path.exists(COMMAND_FILE):
                    with open(COMMAND_FILE, 'r') as f:
                        command = f.read().strip()
                    
                    # Only send if command changed OR every 5 seconds as a heartbeat
                    if command and (command != last_command):
                        if self.ser and self.ser.is_open:
                            self.ser.write(command.encode())
                            print(f"📤 Sent Command: {command}")
                            last_command = command
            except Exception as e:
                print(f"⚠️ Write Error: {e}")
            
            time.sleep(0.5)  # Check for commands every 0.5s

    def start(self):
        """Starts the read/write threads."""
        if not self.connect():
            return

        # Initialize CSV if not exists or header mismatch
        header = ['timestamp', 'sensor_value', 'voltage', 'relay_state']
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(header)
        
        self.running = True
        
        # Start Threads
        read_thread = threading.Thread(target=self.read_serial, daemon=True)
        write_thread = threading.Thread(target=self.write_serial, daemon=True)
        
        read_thread.start()
        write_thread.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping Bridge...")
            self.running = False
            if self.ser:
                self.ser.close()

if __name__ == "__main__":
    print("🚀 Starting ESP32 <-> Streamlit Bridge...")
    bridge = SerialBridge(BAUD_RATE)
    bridge.start()
