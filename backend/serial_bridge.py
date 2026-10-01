"""
Serial Bridge for IoT RFID Attendance System
Optional redundancy bridge: Reads RFID scans directly from ESP32 via USB (COM3)
and forwards them to the local FastAPI backend.
"""
import sys
import time
import serial
import httpx

PORT = "COM3"
BAUD = 115200
API_URL = "http://127.0.0.1:8000/api/attendance/scan"

def run_bridge():
    print("=" * 50)
    print(f"Starting Serial Bridge on {PORT} at {BAUD} baud...")
    print(f"Targeting: {API_URL}")
    print("=" * 50)

    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        print(f"Successfully connected to {PORT}!")
        print("Listening for RFID card scans from hardware...\n")
    except Exception as e:
        print(f"[ERROR] Could not open {PORT}: {e}")
        print("Note: Make sure Arduino IDE Serial Monitor is closed.")
        return

    client = httpx.Client(timeout=5.0)

    try:
        while True:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line:
                print(f"[ESP32] {line}")
                # Check for UID detection pattern
                if "UID:" in line:
                    parts = line.split("UID:")
                    if len(parts) > 1:
                        card_uid = parts[1].strip()
                        print(f"\n[BRIDGE] Detected UID: {card_uid} -> Sending to backend...")
                        try:
                            res = client.post(API_URL, json={"card_uid": card_uid})
                            print(f"[BRIDGE] Backend response ({res.status_code}): {res.json()}\n")
                        except Exception as req_err:
                            print(f"[BRIDGE ERROR] Request failed: {req_err}\n")
    except KeyboardInterrupt:
        print("\nExiting Serial Bridge...")
    finally:
        ser.close()
        client.close()

if __name__ == "__main__":
    run_bridge()
