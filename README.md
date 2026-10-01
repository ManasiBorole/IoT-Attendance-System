# IoT Attendance System

A complete, reliable, and lightweight RFID-based attendance system using **ESP32 DevKit V1**, **RC522 RFID reader**, **FastAPI (Python)**, **SQLite database**, and a **React dashboard**.

---

## 🏛️ Architecture

```
RFID Card
   ↓
 RC522
   ↓
 ESP32
   ↓
 Wi-Fi
   ↓
Backend API (FastAPI)
   ↓
Database (SQLite)
   ↓
React Dashboard
```

---

## ⚡ Features

- **Student Registration**: Register students with Serial Number, Name, and RFID Card UID.
- **Physical RFID Scanning**: ESP32 + RC522 detects physical cards instantly over SPI.
- **Automatic Identification**: Real-time identification of students from the database.
- **Automatic Attendance Marking**: Marks student attendance as "Present" with current date and time.
- **Duplicate Prevention**: Prevents duplicate attendance entries on the same day while showing visual feedback of the initial scan time.
- **Attendance Record Deletion**: Delete individual attendance records without deleting the registered student or modifying card UIDs.
- **Persistent Student Records**: Registered students remain persistent across restarts.
- **Live Real-Time Dashboard**: Auto-updates whenever an RFID card is scanned or a record is modified.
- **Safe & Responsive UI**: Clean modern design with quick feedback and no unnecessary popups.

---

## 🔌 Hardware Specifications & Wiring

### Hardware Components
- **ESP32 DevKit V1** (30-pin or 38-pin version)
- **RC522 RFID Reader Module**
- **13.56MHz RFID Cards / Keyfob Tags**
- **Breadboard and jumper wires**

### RFID Wiring Diagram (SPI Interface)

| RC522 RFID Pin | ESP32 GPIO Pin | Function / Notes |
| :--- | :--- | :--- |
| **SDA / SS** | **GPIO 5 (D5)** | SPI Chip Select |
| **SCK** | **GPIO 18 (D18)** | SPI Clock |
| **MOSI** | **GPIO 23 (D23)** | SPI Master Out |
| **MISO** | **GPIO 19 (D19)** | SPI Master In |
| **IRQ** | *Not Connected* | Leave unconnected |
| **GND** | **GND** | Ground (Common) |
| **RST** | **GPIO 22 (D22)** | Reset Pin |
| **3.3V** | **3V3** | ⚠️ Connect to **3.3V only** (5V damages RC522) |

---

## 📂 Project Structure

```
IoT-Attendance-System/
├── backend/
│   ├── main.py              # FastAPI application & REST API routes
│   ├── database.py          # SQLite engine and session configuration
│   ├── models.py            # SQLAlchemy models (Student, Attendance)
│   ├── schemas.py           # Pydantic validation schemas
│   ├── requirements.txt     # Python backend dependencies
│   ├── test_backend.py      # Automated unit and integration test suite
│   └── attendance.db        # SQLite database file (created automatically)
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # React dashboard with live polling & actions
│   │   ├── App.css          # Styling for tables, scan cards & modals
│   │   ├── index.css        # Design tokens, variables & typography
│   │   └── main.jsx         # React entry point
│   ├── .env.example         # Example frontend environment variables
│   ├── index.html           # HTML template
│   ├── package.json         # Frontend dependencies and scripts
│   └── vite.config.js       # Vite configuration
│
├── esp32/
│   └── rfid_attendance.ino  # ESP32 Arduino sketch with Wi-Fi HTTP POST
│
├── rfid_attendance/
│   └── rfid_attendance.ino  # Standard Arduino IDE sketch directory
│
├── .env.example             # Root environment configuration template
├── .gitignore               # Protected secrets, virtualenv, build artifacts
└── README.md                # System documentation & setup guide
```

---

## 🚀 Software Setup & Installation

### 1. Clone Repository
```bash
git clone https://github.com/ManasiBorole/IoT-Attendance-System.git
cd IoT-Attendance-System
```

### 2. Backend Setup (FastAPI + SQLite)

1. Open PowerShell or a terminal inside the project root:
   ```powershell
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. Install required Python packages:
   ```powershell
   pip install -r requirements.txt
   ```
4. Start the FastAPI backend server:
   ```powershell
   python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
   - API Root: `http://localhost:8000`
   - Interactive Swagger API Documentation: `http://localhost:8000/docs`

> [!NOTE]
> On first startup, the database `attendance.db` and initial registered students (**Manasi Borole** - `CD:FA:02:07` and **Ghanshyam Auti** - `6B:66:16:06`) are created automatically.

### 3. Frontend Setup (React + Vite)

1. Open a new terminal in the `frontend` directory:
   ```powershell
   cd frontend
   ```
2. Configure environment variables (optional, defaults to `http://localhost:8000`):
   ```powershell
   copy .env.example .env
   ```
3. Install frontend dependencies:
   ```powershell
   npm install
   ```
4. Start the Vite development server:
   ```powershell
   npm run dev -- --host
   ```
5. Open your browser:
   - **Local:** `http://localhost:5173`
   - **LAN (Mobile / Tablet):** `http://<YOUR_COMPUTER_IP>:5173`

---

## 📡 ESP32 Setup & Firmware Configuration

### 1. Arduino IDE Setup
1. Download and install **Arduino IDE** (v2.x recommended).
2. Install ESP32 board support in Arduino IDE:
   - Go to **File -> Preferences**.
   - In *Additional Board Manager URLs*, add:
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Go to **Tools -> Board -> Boards Manager...**, search for `esp32` by Espressif Systems, and click **Install**.
3. Install required Arduino libraries:
   - Go to **Sketch -> Include Library -> Manage Libraries...**
   - Search for and install **MFRC522** (by GithubCommunity).
   - Search for and install **ArduinoJson** (by Benoit Blanchon, v6 or v7).

### 2. Configure Wi-Fi & Server Endpoint
Open `rfid_attendance/rfid_attendance.ino` in Arduino IDE and set your Wi-Fi credentials and local backend IP:
```cpp
// Wi-Fi Credentials
const char* ssid     = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Replace with your computer's local Wi-Fi IPv4 address
const char* serverUrl = "http://192.168.1.XX:8000/api/attendance/scan";
```

### 3. Network Requirement
> [!IMPORTANT]
> **ESP32 and computer must be on the same network!**
> - The ESP32 is a separate physical device on your local network.
> - Do **NOT** use `localhost` or `127.0.0.1` in the ESP32 code.
> - Use your computer's active Wi-Fi IPv4 address (found by running `ipconfig` in PowerShell).

### 4. Upload to ESP32
1. Connect the ESP32 to your computer via USB cable.
2. In Arduino IDE:
   - **Tools -> Board -> ESP32 Arduino -> DOIT ESP32 DEVKIT V1** (or ESP32 Dev Module).
   - **Tools -> Port -> Select the COM port** (e.g. `COM3`).
3. Click **Upload** (press the `BOOT` button on ESP32 if upload stays stuck on *Connecting...*).
4. Open **Serial Monitor** at **115200 baud** to see Wi-Fi connection and scan logs.

---

## 🔄 Complete Attendance Flow

1. **Card Presentation**: User taps an RFID card against the RC522 reader.
2. **UID Reading**: The RC522 reads the card UID (e.g., `CD:FA:02:07`) over SPI.
3. **HTTP Dispatch**: ESP32 formats a JSON payload `{"card_uid": "CD:FA:02:07"}` and sends an HTTP POST request to `/api/attendance/scan` over Wi-Fi.
4. **Backend Processing**:
   - Backend normalizes the UID.
   - Searches `models.Student` for a matching registered student.
   - If not found, returns `registered: false` (dashboard displays "Card Not Registered").
   - If found, checks if attendance has already been recorded for today's date:
     - **Already Marked Today**: Returns original attendance timestamp without creating a duplicate record.
     - **New Scan**: Inserts new record into SQLite database with date, time, and status `Present`.
5. **Dashboard Refresh**: Frontend automatically reflects the new attendance event in real time and updates the Attendance Records table.
6. **Deletion**: Admin can delete any attendance record from the table by clicking **Delete**; student registration remains intact.

---

## 📡 REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/students` | List all registered students |
| `POST` | `/api/students` | Register a new student (`serial_number`, `name`, `card_uid`) |
| `PUT` | `/api/students/{id}` | Update existing student profile or assigned UID |
| `DELETE` | `/api/students/{id}` | Delete a registered student |
| `GET` | `/api/attendance` | Retrieve all attendance records (newest first) |
| `DELETE`| `/api/attendance/{id}` | Delete a specific attendance record (leaves student registered) |
| `GET` | `/api/attendance/latest`| Get the latest RFID scan event for live display |
| `POST` | `/api/attendance/scan` | ESP32 scan endpoint: receives `{"card_uid": "..."}` and processes attendance |

---

## 🌿 Future Development & Branching Strategy

The `main` branch of this repository represents the **stable, working baseline**.

To protect the working hardware integration and dashboard functionality:
1. **Never commit experimental changes directly to `main`**.
2. Create a separate feature or bugfix branch:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```
3. Test thoroughly on your branch (verify physical ESP32 scanning, database updates, and dashboard UI).
4. Merge into `main` only after full validation:
   ```bash
   git checkout main
   git merge feature/your-feature-name
   git push origin main
   ```
