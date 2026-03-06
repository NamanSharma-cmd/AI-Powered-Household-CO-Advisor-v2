import serial
import time
import csv
import os
import threading
from datetime import datetime

# --- Configuration ---
SERIAL_PORT = 'COM3'  # Update this to your ESP32's COM port (e.g., '/dev/ttyUSB0' on Linux/Mac)
BAUD_RATE = 115200
DATA_FILE = 'live_data.csv'
COMMAND_FILE = 'command.txt'

class SerialBridge:
    def __init__(self, port, baud_rate):
        self.port = port
        self.baud_rate = baud_rate
        self.ser = None
        self.running = False

    def connect(self):
        """Attempts to connect to the serial port."""
        try:
            self.ser = serial.Serial(self.port, self.baud_rate, timeout=1)
            print(f"✅ Connected to {self.port} at {self.baud_rate} baud.")
            return True
        except serial.SerialException as e:
            print(f"❌ Connection Failed: {e}")
            return False

    def read_serial(self):
        """Reads data from Serial and writes to CSV."""
        if not self.ser or not self.ser.is_open:
            return

        while self.running:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8').strip()
                    
                    if line.startswith("DATA,"):
                        # Expected format: DATA,sensor_value,voltage
                        parts = line.split(',')
                        if len(parts) == 3:
                            sensor_val = parts[1]
                            voltage = parts[2]
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            # Append to CSV
                            with open(DATA_FILE, 'a', newline='') as f:
                                writer = csv.writer(f)
                                writer.writerow([timestamp, sensor_val, voltage])
                            
                            print(f"📥 Received: {sensor_val} (Volts: {voltage})")
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
                    
                    if command and command != last_command:
                        if self.ser and self.ser.is_open:
                            self.ser.write(command.encode())
                            print(f"📤 Sent Command: {command}")
                            last_command = command
                            
                            # Clear file after sending (optional, or keep state)
                            # open(COMMAND_FILE, 'w').close() 
            except Exception as e:
                print(f"⚠️ Write Error: {e}")
            
            time.sleep(0.5)  # Check for commands every 0.5s

    def start(self):
        """Starts the read/write threads."""
        if not self.connect():
            return

        # Initialize CSV if not exists
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'sensor_value', 'voltage'])

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
    print(f"Make sure your ESP32 is connected to {SERIAL_PORT}")
    
    bridge = SerialBridge(SERIAL_PORT, BAUD_RATE)
    bridge.start()
